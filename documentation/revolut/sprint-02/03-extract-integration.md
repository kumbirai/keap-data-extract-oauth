# 3. Extract pipeline integration (Revolut Merchant API)

## 3.1 Position in the full extract run

The Merchant extract runs **after** the existing Revolut Business extract in `DataLoadManager.load_all_data`:

```
1. Keap V1 entity loaders
2. run_keap_v2_extract()
3. run_stripe_extract()
4. run_revolut_extract()          ← Sprint-01 (Business API)
5. run_revolut_merchant_extract() ← Sprint-02 (Merchant API)  ← NEW
```

If `REVOLUT_MERCHANT_API_KEY` is absent, `run_revolut_merchant_extract` logs a warning and returns an empty `LoadResult` — it does not abort the run.

## 3.2 Load order within the Merchant extract

Dependencies exist between entities due to fan-out:

```
1. revolut_merchant_locations   (no deps — small full sync)
2. revolut_merchant_customers   (no deps)
3. revolut_merchant_payment_methods  (fan-out from customers — run after step 2)
4. revolut_merchant_orders      (time-windowed)
5. revolut_merchant_order_payments   (fan-out from orders — run after step 4)
6. revolut_merchant_disputes    (time-windowed; references orders logically)
```

## 3.3 Sync strategies in detail

### Orders (time-windowed, paginated)

```
window_from = checkpoint["window_from"] or (now - initial_history_days)
window_to   = now

loop:
  params = {from: window_from, created_before: window_to, count: page_size}
  page = GET /api/orders?{params}
  upsert page → revolut_merchant_orders
  fetch order payments for each order in page → upsert → revolut_merchant_order_payments
  if len(page) < page_size: break
  window_to = min(order.created_at for order in page)  # advance to last created_at

save checkpoint: window_from = now - lookback_days
```

On subsequent runs, `window_from` = `last_run_at - lookback_days` to capture state transitions.

### Customers (full sync or incremental)

The Merchant API customers endpoint may not support date filtering. Default strategy:

- **First run**: fetch all pages until exhausted.
- **Subsequent runs**: re-fetch all (idempotent via upsert). If the API exposes an `updated_after` filter, use it for incremental.

Fan-out: for each customer in the full page set, call `GET /api/customers/{id}/payment-methods` and upsert to `revolut_merchant_payment_methods`.

### Disputes (time-windowed)

Similar to orders but with a **longer lookback** (default 30 days) because disputes evolve slowly:

```
window_from = last_run_at - lookback_days  (default 30)
GET /api/disputes?{from: window_from, ...}
```

### Locations (full sync)

```
GET /api/locations → upsert all rows → save last_run_at checkpoint
```

## 3.4 Fan-out pattern

Order payments and payment methods are fetched via per-resource GET calls:

```python
for order in orders_page:
    payments = client.get_order_payments(order["id"])
    rows = [map_order_payment(p, order["id"], now, store_raw) for p in payments]
    upsert_rows(session, RevolutMerchantOrderPayment, rows)
```

This is synchronous and sequential per resource. For large order volumes consider batching fan-out calls but maintain idempotency.

## 3.5 Checkpoint design

Checkpoint keys in `extraction_state.entity_type` / checkpoint JSON:

| Entity | checkpoint key | State stored |
|--------|---------------|--------------|
| Orders | `revolut_merchant_orders` | `window_from`, `window_to`, `last_run_at` |
| Customers | `revolut_merchant_customers` | `last_run_at` |
| Disputes | `revolut_merchant_disputes` | `window_from`, `last_run_at` |
| Locations | `revolut_merchant_locations` | `last_run_at` |

Order payments and payment methods piggyback on their parent entity checkpoints — no independent checkpoint.

Checkpoint JSON example for orders:

```json
{
  "window_from": "2025-01-01T00:00:00+00:00",
  "window_to": "2026-04-04T00:00:00+00:00",
  "last_run_at": "2026-04-04T06:00:00+00:00"
}
```

## 3.6 New source modules

```
src/revolut/
  merchant_settings.py          # RevolutMerchantSettings dataclass + from_env()
  merchant_api_constants.py     # paths, hosts, version header, page sizes
  merchant_client.py            # RevolutMerchantClient — Bearer token HTTP
  merchant_mappers.py           # map_order / map_customer / map_payment_method /
                                #   map_order_payment / map_dispute / map_location
  merchant_checkpoint_state.py  # entity keys, window helpers
  sync_merchant_locations.py    # full sync
  sync_merchant_customers.py    # full sync + payment method fan-out
  sync_merchant_orders.py       # time-windowed + order payment fan-out
  sync_merchant_disputes.py     # time-windowed
  merchant_orchestrator.py      # run_revolut_merchant_extract()
                                # run_revolut_merchant_entity()

src/models/
  revolut_merchant_models.py    # SQLAlchemy ORM for all 6 tables

database/migrations/versions/
  008_add_revolut_merchant_tables.py
```

## 3.7 Modified files

### `src/scripts/load_data_manager.py`

Add import and call in `load_all_data`:
```python
from src.revolut.merchant_orchestrator import run_revolut_merchant_extract

# Inside load_all_data, after run_revolut_extract():
result = run_revolut_merchant_extract(session, checkpoint_manager, update)
```

Add dispatch in `load_entity` for:
- `revolut_merchant_orders`
- `revolut_merchant_customers`
- `revolut_merchant_disputes`
- `revolut_merchant_locations`
- `revolut_merchant_all`

### `src/__main__.py`

Add entity type choices:
```python
"revolut_merchant_orders",
"revolut_merchant_customers",
"revolut_merchant_disputes",
"revolut_merchant_locations",
"revolut_merchant_all",
```

## 3.8 CLI usage

```bash
# Full extract including merchant
python -m src

# Merchant extract only
python -m src --entity-type revolut_merchant_all

# Individual entities
python -m src --entity-type revolut_merchant_orders
python -m src --entity-type revolut_merchant_customers
python -m src --entity-type revolut_merchant_disputes
python -m src --entity-type revolut_merchant_locations

# Incremental (use checkpointed window_from)
python -m src --entity-type revolut_merchant_orders --update
```

## 3.9 Error handling

- HTTP 429: backoff and retry (shared retry decorator from `src/utils/` or `merchant_client.py`).
- HTTP 404 on fan-out (order/customer deleted): log at WARNING and skip; do not abort page.
- Missing API key: log at WARNING, return `LoadResult(0, 0, 0)`.
- Fan-out failure for a single order/customer: log error, increment `failed_count`, continue with next resource.

## 3.10 References

- [`load_data_manager.py`](../../src/scripts/load_data_manager.py)
- [`checkpoint_manager.py`](../../src/scripts/checkpoint_manager.py)
- [`batch_upsert.py`](../../src/database/batch_upsert.py)
- [Sprint-01 extract integration](../sprint-01/03-extract-integration.md)
- [Stripe extract integration](../../stripe/03-extract-integration.md)

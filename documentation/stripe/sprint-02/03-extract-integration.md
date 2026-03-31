# 3. Extract pipeline integration (Stripe BI sprint-02)

This document describes how the six sprint-02 entities integrate with the existing `src/stripe/`
pipeline established in sprint-01.

## 3.1 Architecture recap

The sprint-01 pipeline:

| File | Role |
|------|------|
| `src/stripe/orchestrator.py` | `STRIPE_ENTITY_SPECS` list + `run_stripe_extract` / `run_stripe_entity` facades |
| `src/stripe/sync.py` | `sync_stripe_entity()` — top-level list → paginate → upsert |
| `src/stripe/mappers.py` | One `map_*` function per entity |
| `src/stripe/constants.py` | `STRIPE_ENTITY_TYPES` string list |
| `src/models/stripe_models.py` | SQLAlchemy model classes |
| `src/database/batch_upsert.py` | Shared `upsert_rows()` |

Sprint-02 extends all of these with new entries and adds one new function to `sync.py`.

---

## 3.2 New `entity_type` constants

Add six strings to `STRIPE_ENTITY_TYPES` in `src/stripe/constants.py`, in load order:

```python
STRIPE_ENTITY_TYPES = [
    # --- sprint-01 (unchanged order) ---
    "stripe_products",
    "stripe_prices",
    "stripe_coupons",
    "stripe_subscriptions",
    "stripe_invoices",
    "stripe_payment_intents",
    "stripe_charges",
    "stripe_refunds",
    "stripe_balance_transactions",
    "stripe_payouts",
    "stripe_transfers",
    # --- sprint-02 ---
    "stripe_customers",
    "stripe_disputes",
    "stripe_promotion_codes",
    "stripe_credit_notes",
    "stripe_invoice_line_items",
    "stripe_subscription_items",
]
```

---

## 3.3 Complete load order DAG

```
(Keap entities complete first — DataLoadManager.load_all_data load_order)

────────────────────────────────────────────────────────────────
Stripe step 1 — Catalog dimensions (no intra-Stripe dependencies)
────────────────────────────────────────────────────────────────
  stripe_products
  stripe_prices          (references stripe_products conceptually; load after)
  stripe_coupons         (independent)
  stripe_customers       ← NEW — must precede all facts carrying customer_id

────────────────────────────────────────────────────────────────
Stripe step 2 — Core facts
────────────────────────────────────────────────────────────────
  stripe_subscriptions
  stripe_invoices        (references stripe_subscriptions)
  stripe_payment_intents
  stripe_charges         (references stripe_payment_intents, stripe_invoices)

────────────────────────────────────────────────────────────────
Stripe step 3 — Supplemental facts (depend on charges/invoices/customers)
────────────────────────────────────────────────────────────────
  stripe_disputes        ← NEW — depends on stripe_charges, stripe_customers
  stripe_promotion_codes ← NEW — depends on stripe_coupons, stripe_customers
  stripe_credit_notes    ← NEW — depends on stripe_invoices, stripe_customers

────────────────────────────────────────────────────────────────
Stripe step 4 — Settlement (child-of-charge)
────────────────────────────────────────────────────────────────
  stripe_refunds
  stripe_balance_transactions
  stripe_payouts
  stripe_transfers

────────────────────────────────────────────────────────────────
Stripe step 5 — Child list entities (parents must be in DB first)
────────────────────────────────────────────────────────────────
  stripe_invoice_line_items    ← NEW — reads stripe_invoices.id from DB
  stripe_subscription_items    ← NEW — reads stripe_subscriptions.id from DB
```

**Why `stripe_customers` is first in sprint-02**: disputes, promotion codes, and credit notes all
have `customer_id`. While the database enforces no FK constraints, loading the dimension first
ensures BI views can join without missing rows even during a partial run.

**Why child entities are last**: their extraction reads parent ids from the database; the parent
tables must be present and populated before their children can be fetched.

---

## 3.4 Top-level list entities: additions to `STRIPE_ENTITY_SPECS`

`stripe_customers`, `stripe_disputes`, `stripe_promotion_codes`, and `stripe_credit_notes` all use
the existing `sync_stripe_entity()` function unchanged — their list APIs support `created[gte]` and
cursor pagination. Add four entries to `STRIPE_ENTITY_SPECS` in `orchestrator.py`:

```python
# In orchestrator.py — append after stripe_transfers entry, in load order:
("stripe_customers",       StripeCustomer,      stripe.Customer,      mappers.map_customer),
("stripe_disputes",        StripeDispute,        stripe.Dispute,        mappers.map_dispute),
("stripe_promotion_codes", StripePromotionCode,  stripe.PromotionCode,  mappers.map_promotion_code),
("stripe_credit_notes",    StripeCreditNote,     stripe.CreditNote,     mappers.map_credit_note),
```

No changes to `sync_stripe_entity()` are needed for these four entities.

---

## 3.5 Child list entities: new `sync_stripe_child_entity()` function

Invoice line items and subscription items require a different extraction pattern. Add a new
function to `src/stripe/sync.py`.

### Why a separate function

`sync_stripe_entity()` is built around `list_fn(created_gte, starting_after)`. Child list APIs
accept a parent id as the primary argument and do not accept `created` filters. Overloading the
existing function would make both code paths harder to reason about.

### Function signature

```python
def sync_stripe_child_entity(
    session,
    checkpoint_manager,
    settings: StripeExtractSettings,
    entity_type: str,           # e.g. "stripe_invoice_line_items"
    parent_entity_type: str,    # e.g. "stripe_invoices"
    parent_model_class,         # e.g. StripeInvoice
    child_model_class,          # e.g. StripeInvoiceLineItem
    child_list_fn,              # e.g. stripe.Invoice.list_line_items
    parent_id_attr: str,        # column on child row dict that holds the parent id
    mapper,                     # e.g. mappers.map_invoice_line_item
    mutable_parent_statuses: list,  # e.g. ["draft", "open"]
    stripe_account_id,
    update: bool,
) -> LoadResult:
```

### Logic pseudocode

```
1. Load checkpoint for entity_type.
   - Get per-account state: last_parent_id (resume cursor), max_created_unix (watermark).

2. Resolve parent_created_gte:
   - If update=True: max_created_unix - lookback_seconds.
   - If update=False (full load): None (process all parents).

3. Query parent ids from DB:
   SELECT id FROM <parent_table>
   WHERE (
     (:parent_created_gte IS NULL OR created >= :parent_created_gte)
     OR status IN (:mutable_parent_statuses)
   )
   AND (stripe_account_id = :account_id OR stripe_account_id IS NULL)
   ORDER BY id

4. If in_progress (last_parent_id set): skip all parent ids <= last_parent_id.

5. For each parent_id:
   a. Call _with_backoff(lambda: child_list_fn(parent_id, limit=settings.list_limit))
   b. Paginate with starting_after until has_more=False.
   c. For each child object: mapper(obj, stripe_account_id, now, settings.store_raw_payload,
      parent_id=parent_id)
   d. Batch upsert via upsert_rows(session, child_model_class, batch).
   e. After each parent completes: save last_parent_id = parent_id to checkpoint.

6. On all parents complete: clear last_parent_id, mark in_progress=False, save checkpoint.

7. Return LoadResult(total, success, failed).
```

### Checkpoint structure for child entities

The `checkpoint_json` for a child entity uses the same `accounts` envelope as sprint-01 but
stores `last_parent_id` instead of `starting_after`:

```json
{
  "accounts": {
    "__platform__": {
      "last_parent_id": "in_abc123",
      "in_progress": true,
      "parent_created_gte": 1700000000
    }
  }
}
```

---

## 3.6 Dispatcher change in `run_stripe_extract` and `run_stripe_entity`

Add a separate `STRIPE_CHILD_SPECS` list in `orchestrator.py` and extend both facade functions:

```python
STRIPE_CHILD_SPECS = [
    {
        "entity_type": "stripe_invoice_line_items",
        "child_model": StripeInvoiceLineItem,
        "parent_model": StripeInvoice,
        "parent_entity_type": "stripe_invoices",
        "child_list_fn": stripe.Invoice.list_line_items,
        "parent_id_attr": "invoice_id",
        "mapper": mappers.map_invoice_line_item,
        "mutable_parent_statuses": ["draft", "open"],
    },
    {
        "entity_type": "stripe_subscription_items",
        "child_model": StripeSubscriptionItem,
        "parent_model": StripeSubscription,
        "parent_entity_type": "stripe_subscriptions",
        "child_list_fn": stripe.SubscriptionItem.list,
        "parent_id_attr": "subscription_id",
        "mapper": mappers.map_subscription_item,
        "mutable_parent_statuses": ["active", "past_due", "trialing"],
    },
]
```

In `run_stripe_extract`: run `STRIPE_ENTITY_SPECS` first (all steps 1–4 in the DAG), then run
`STRIPE_CHILD_SPECS` (step 5).

In `run_stripe_entity`: check both lists when dispatching a targeted `--entity-type` call.

**Note**: `run_stripe_object_by_id` does not apply to child entities — there is no single-object
retrieve API for `InvoiceLineItem` or `SubscriptionItem`. Document this as a known limitation.

---

## 3.7 Mapper functions to add to `src/stripe/mappers.py`

### `map_customer`

```python
def map_customer(obj, stripe_account_id, now, store_raw):
    row = _base_row(obj, stripe_account_id, now, store_raw)
    row.update({
        "id": obj.id,
        "email": getattr(obj, "email", None) or None,
        "name": getattr(obj, "name", None) or None,
        "phone": getattr(obj, "phone", None) or None,
        "description": getattr(obj, "description", None) or None,
        "currency": _currency_code(obj),
        "balance": getattr(obj, "balance", None),
        "delinquent": getattr(obj, "delinquent", None),
        "created": _unix_ts(getattr(obj, "created", None)),
        "default_source": _stripe_id(getattr(obj, "default_source", None)),
        "invoice_prefix": getattr(obj, "invoice_prefix", None) or None,
        "tax_exempt": getattr(obj, "tax_exempt", None) or None,
    })
    return row
```

### `map_invoice_line_item`

The caller injects `invoice_id` because the Stripe SDK does not always expose it as a direct
attribute on the line item object (it may be on the parent call context only).

```python
def map_invoice_line_item(obj, stripe_account_id, now, store_raw, invoice_id=None):
    row = _base_row(obj, stripe_account_id, now, store_raw)
    # _base_row sets loaded_at / updated_at but NOT raw_payload (child table omits it)
    row.pop("raw_payload", None)
    period = getattr(obj, "period", None)
    row.update({
        "id": obj.id,
        "invoice_id": invoice_id or _stripe_id(getattr(obj, "invoice", None)),
        "subscription_id": _stripe_id(getattr(obj, "subscription", None)),
        "subscription_item_id": _stripe_id(getattr(obj, "subscription_item", None)),
        "price_id": _stripe_id(getattr(obj, "price", None)),
        "product_id": _stripe_id(
            getattr(getattr(obj, "price", None), "product", None)
        ),
        "quantity": getattr(obj, "quantity", None),
        "amount": getattr(obj, "amount", None),
        "currency": _require_currency(obj),
        "description": getattr(obj, "description", None) or None,
        "period_start": _unix_ts(getattr(period, "start", None)) if period else None,
        "period_end":   _unix_ts(getattr(period, "end",   None)) if period else None,
        "type": getattr(obj, "type", None) or None,
        "proration": getattr(obj, "proration", None),
    })
    return row
```

### `map_subscription_item`

```python
def map_subscription_item(obj, stripe_account_id, now, store_raw, subscription_id=None):
    row = _base_row(obj, stripe_account_id, now, store_raw)
    row.pop("raw_payload", None)
    row.update({
        "id": obj.id,
        "subscription_id": subscription_id or _stripe_id(getattr(obj, "subscription", None)),
        "price_id": _stripe_id(getattr(obj, "price", None)),
        "product_id": _stripe_id(
            getattr(getattr(obj, "price", None), "product", None)
        ),
        "quantity": getattr(obj, "quantity", None),
        "created": _unix_ts(getattr(obj, "created", None)),
    })
    return row
```

### `map_dispute`

```python
def map_dispute(obj, stripe_account_id, now, store_raw):
    row = _base_row(obj, stripe_account_id, now, store_raw)
    ed = getattr(obj, "evidence_details", None)
    row.update({
        "id": obj.id,
        "charge_id": _stripe_id(getattr(obj, "charge", None)),
        "payment_intent_id": _stripe_id(getattr(obj, "payment_intent", None)),
        "amount": getattr(obj, "amount", None),
        "currency": _require_currency(obj),
        "status": getattr(obj, "status", None) or None,
        "reason": getattr(obj, "reason", None) or None,
        "created": _unix_ts(getattr(obj, "created", None)),
        "evidence_due_by": _unix_ts(getattr(ed, "due_by", None) if ed else None),
        "is_charge_refundable": getattr(obj, "is_charge_refundable", None),
    })
    return row
```

### `map_promotion_code`

```python
def map_promotion_code(obj, stripe_account_id, now, store_raw):
    row = _base_row(obj, stripe_account_id, now, store_raw)
    r = getattr(obj, "restrictions", None)
    row.update({
        "id": obj.id,
        "code": getattr(obj, "code", None) or None,
        "coupon_id": _stripe_id(getattr(obj, "coupon", None)),
        "customer_id": _stripe_id(getattr(obj, "customer", None)),
        "active": getattr(obj, "active", None),
        "created": _unix_ts(getattr(obj, "created", None)),
        "expires_at": _unix_ts(getattr(obj, "expires_at", None)),
        "max_redemptions": getattr(obj, "max_redemptions", None),
        "times_redeemed": getattr(obj, "times_redeemed", None),
        "restrictions_minimum_amount": getattr(r, "minimum_amount", None) if r else None,
        "restrictions_minimum_amount_currency": getattr(r, "minimum_amount_currency", None) if r else None,
        "restrictions_first_time_transaction": getattr(r, "first_time_transaction", None) if r else None,
    })
    return row
```

### `map_credit_note`

```python
def map_credit_note(obj, stripe_account_id, now, store_raw):
    row = _base_row(obj, stripe_account_id, now, store_raw)
    row.update({
        "id": obj.id,
        "invoice_id": _stripe_id(getattr(obj, "invoice", None)),
        "customer_id": _stripe_id(getattr(obj, "customer", None)),
        "amount": getattr(obj, "amount", None),
        "currency": _require_currency(obj),
        "status": getattr(obj, "status", None) or None,
        "type": getattr(obj, "type", None) or None,
        "reason": getattr(obj, "reason", None) or None,
        "memo": getattr(obj, "memo", None) or None,
        "out_of_band_amount": getattr(obj, "out_of_band_amount", None),
        "refund_id": _stripe_id(getattr(obj, "refund", None)),
        "created": _unix_ts(getattr(obj, "created", None)),
    })
    return row
```

---

## 3.8 SQLAlchemy models to add to `src/models/stripe_models.py`

```python
class StripeCustomer(Base):
    __tablename__ = "stripe_customers"
    id = Column(Text, primary_key=True)
    email = Column(Text, nullable=True, index=True)
    name = Column(Text, nullable=True)
    phone = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    currency = Column(Text, nullable=True)
    balance = Column(Integer, nullable=True)
    delinquent = Column(Boolean, nullable=True, index=True)
    created = Column(DateTime(timezone=True), nullable=True, index=True)
    default_source = Column(Text, nullable=True)
    invoice_prefix = Column(Text, nullable=True)
    tax_exempt = Column(Text, nullable=True)
    metadata_col = Column("metadata", JSONB, nullable=True)
    raw_payload = Column(JSONB, nullable=True)
    stripe_account_id = Column(Text, nullable=True, index=True)
    loaded_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)


class StripeInvoiceLineItem(Base):
    __tablename__ = "stripe_invoice_line_items"
    id = Column(Text, primary_key=True)
    invoice_id = Column(Text, nullable=False, index=True)
    subscription_id = Column(Text, nullable=True, index=True)
    subscription_item_id = Column(Text, nullable=True)
    price_id = Column(Text, nullable=True, index=True)
    product_id = Column(Text, nullable=True, index=True)
    quantity = Column(Integer, nullable=True)
    amount = Column(Integer, nullable=True)
    currency = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    period_start = Column(DateTime(timezone=True), nullable=True)
    period_end = Column(DateTime(timezone=True), nullable=True)
    type = Column(Text, nullable=True, index=True)
    proration = Column(Boolean, nullable=True)
    metadata_col = Column("metadata", JSONB, nullable=True)
    stripe_account_id = Column(Text, nullable=True, index=True)
    loaded_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)


class StripeSubscriptionItem(Base):
    __tablename__ = "stripe_subscription_items"
    id = Column(Text, primary_key=True)
    subscription_id = Column(Text, nullable=False, index=True)
    price_id = Column(Text, nullable=True, index=True)
    product_id = Column(Text, nullable=True, index=True)
    quantity = Column(Integer, nullable=True)
    created = Column(DateTime(timezone=True), nullable=True)
    metadata_col = Column("metadata", JSONB, nullable=True)
    stripe_account_id = Column(Text, nullable=True, index=True)
    loaded_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)


class StripeDispute(Base):
    __tablename__ = "stripe_disputes"
    id = Column(Text, primary_key=True)
    charge_id = Column(Text, nullable=True, index=True)
    payment_intent_id = Column(Text, nullable=True)
    amount = Column(Integer, nullable=True)
    currency = Column(Text, nullable=False)
    status = Column(Text, nullable=True, index=True)
    reason = Column(Text, nullable=True)
    created = Column(DateTime(timezone=True), nullable=True, index=True)
    evidence_due_by = Column(DateTime(timezone=True), nullable=True, index=True)
    is_charge_refundable = Column(Boolean, nullable=True)
    metadata_col = Column("metadata", JSONB, nullable=True)
    raw_payload = Column(JSONB, nullable=True)
    stripe_account_id = Column(Text, nullable=True, index=True)
    loaded_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)


class StripePromotionCode(Base):
    __tablename__ = "stripe_promotion_codes"
    id = Column(Text, primary_key=True)
    code = Column(Text, nullable=True, index=True)
    coupon_id = Column(Text, nullable=True, index=True)
    customer_id = Column(Text, nullable=True, index=True)
    active = Column(Boolean, nullable=True, index=True)
    created = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    max_redemptions = Column(Integer, nullable=True)
    times_redeemed = Column(Integer, nullable=True)
    restrictions_minimum_amount = Column(Integer, nullable=True)
    restrictions_minimum_amount_currency = Column(Text, nullable=True)
    restrictions_first_time_transaction = Column(Boolean, nullable=True)
    metadata_col = Column("metadata", JSONB, nullable=True)
    stripe_account_id = Column(Text, nullable=True, index=True)
    loaded_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)


class StripeCreditNote(Base):
    __tablename__ = "stripe_credit_notes"
    id = Column(Text, primary_key=True)
    invoice_id = Column(Text, nullable=True, index=True)
    customer_id = Column(Text, nullable=True, index=True)
    amount = Column(Integer, nullable=True)
    currency = Column(Text, nullable=False)
    status = Column(Text, nullable=True, index=True)
    type = Column(Text, nullable=True)
    reason = Column(Text, nullable=True)
    memo = Column(Text, nullable=True)
    out_of_band_amount = Column(Integer, nullable=True)
    refund_id = Column(Text, nullable=True, index=True)
    created = Column(DateTime(timezone=True), nullable=True, index=True)
    metadata_col = Column("metadata", JSONB, nullable=True)
    raw_payload = Column(JSONB, nullable=True)
    stripe_account_id = Column(Text, nullable=True, index=True)
    loaded_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)
```

---

## 3.9 Database migration

Add a new Alembic migration `004_add_stripe_sprint02_tables.py` (following the pattern of
`003_add_stripe_bi_tables.py`). The migration should:

1. Check each table exists before creating (idempotent `upgrade`).
2. Create all six tables with their columns and NOT NULL constraints.
3. Create all indexes listed in §2.1–§2.6 of `02-schema-design.md`.
4. `downgrade`: drop indexes first, then tables in reverse dependency order:
   `stripe_subscription_items` → `stripe_invoice_line_items` → `stripe_credit_notes` →
   `stripe_promotion_codes` → `stripe_disputes` → `stripe_customers`.

---

## 3.10 Complete `entity_type` reference

| `entity_type` | Table | API type | Extraction method |
|---------------|-------|----------|-------------------|
| `stripe_products` | `stripe_products` | Top-level list | `sync_stripe_entity` |
| `stripe_prices` | `stripe_prices` | Top-level list | `sync_stripe_entity` |
| `stripe_coupons` | `stripe_coupons` | Top-level list | `sync_stripe_entity` |
| `stripe_customers` | `stripe_customers` | Top-level list | `sync_stripe_entity` |
| `stripe_subscriptions` | `stripe_subscriptions` | Top-level list | `sync_stripe_entity` |
| `stripe_invoices` | `stripe_invoices` | Top-level list | `sync_stripe_entity` |
| `stripe_payment_intents` | `stripe_payment_intents` | Top-level list | `sync_stripe_entity` |
| `stripe_charges` | `stripe_charges` | Top-level list | `sync_stripe_entity` |
| `stripe_disputes` | `stripe_disputes` | Top-level list | `sync_stripe_entity` |
| `stripe_promotion_codes` | `stripe_promotion_codes` | Top-level list | `sync_stripe_entity` |
| `stripe_credit_notes` | `stripe_credit_notes` | Top-level list | `sync_stripe_entity` |
| `stripe_refunds` | `stripe_refunds` | Top-level list | `sync_stripe_entity` |
| `stripe_balance_transactions` | `stripe_balance_transactions` | Top-level list | `sync_stripe_entity` |
| `stripe_payouts` | `stripe_payouts` | Top-level list | `sync_stripe_entity` |
| `stripe_transfers` | `stripe_transfers` | Top-level list | `sync_stripe_entity` |
| `stripe_invoice_line_items` | `stripe_invoice_line_items` | Child list per invoice | `sync_stripe_child_entity` |
| `stripe_subscription_items` | `stripe_subscription_items` | Child list per subscription | `sync_stripe_child_entity` |

---

## 3.11 CLI examples

```bash
# Full extract including all sprint-02 entities
python -m src

# Incremental update
python -m src --update

# Load only the customer dimension
python -m src --entity-type stripe_customers

# Reload invoice line items
python -m src --entity-type stripe_invoice_line_items

# Load a single dispute by Stripe id
python -m src --entity-type stripe_disputes --stripe-object-id dp_abc123

# Incremental update for disputes only
python -m src --update --entity-type stripe_disputes
```

**Limitation**: `--stripe-object-id` is not supported for `stripe_invoice_line_items` or
`stripe_subscription_items`. There is no single-object retrieve API for these child resources;
refresh by re-running the parent entity and then the child entity.

---

## 3.12 References

- [Sprint-01 extract integration](../sprint-01/03-extract-integration.md)
- [`src/stripe/orchestrator.py`](../../../../src/stripe/orchestrator.py)
- [`src/stripe/sync.py`](../../../../src/stripe/sync.py)
- [`src/stripe/mappers.py`](../../../../src/stripe/mappers.py)
- [`src/stripe/constants.py`](../../../../src/stripe/constants.py)
- [`src/models/stripe_models.py`](../../../../src/models/stripe_models.py)
- [`database/migrations/versions/003_add_stripe_bi_tables.py`](../../../../database/migrations/versions/003_add_stripe_bi_tables.py)

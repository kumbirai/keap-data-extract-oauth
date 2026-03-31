"""Tests for Stripe child-entity parent query wiring (mocked session)."""
from types import SimpleNamespace
from unittest.mock import MagicMock

from src.models.stripe_models import StripeInvoice, StripeSubscription
from src.stripe.sync import query_invoice_parents_for_line_items, query_subscription_parents_for_items


def test_query_invoice_parents_full_load_chains_query():
    session = MagicMock()
    chain = session.query.return_value
    chain.filter.return_value = chain
    chain.order_by.return_value = chain
    chain.all.return_value = [SimpleNamespace(id="in_a", created=None)]

    rows = query_invoice_parents_for_line_items(session, None, None, ("draft", "open"))

    assert rows == [("in_a", None)]
    session.query.assert_called_once_with(StripeInvoice.id, StripeInvoice.created)
    assert chain.filter.call_count == 1
    chain.order_by.assert_called_once()


def test_query_invoice_parents_incremental_adds_or_filter():
    session = MagicMock()
    chain = session.query.return_value
    chain.filter.return_value = chain
    chain.order_by.return_value = chain
    chain.all.return_value = []

    from datetime import datetime, timezone

    wm = datetime(2024, 1, 1, tzinfo=timezone.utc)
    query_invoice_parents_for_line_items(session, wm, "acct_1", ("draft", "open"))

    assert chain.filter.call_count == 2


def test_query_subscription_parents_chains_query():
    session = MagicMock()
    chain = session.query.return_value
    chain.filter.return_value = chain
    chain.order_by.return_value = chain
    chain.all.return_value = [SimpleNamespace(id="sub_x", current_period_start=None)]

    rows = query_subscription_parents_for_items(session, None, None, ("active",))

    assert rows == [("sub_x", None)]
    session.query.assert_called_once_with(StripeSubscription.id, StripeSubscription.current_period_start)

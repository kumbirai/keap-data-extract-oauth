"""Guards on Stripe single-object retrieve and aggregate entity types."""
import pytest


def test_run_stripe_object_by_id_rejects_stripe_all():
    from src.stripe.orchestrator import run_stripe_object_by_id

    with pytest.raises(ValueError, match="not valid"):
        run_stripe_object_by_id(None, "stripe_all", "cus_x")


def test_run_stripe_object_by_id_rejects_invoice_line_items():
    from src.stripe.orchestrator import run_stripe_object_by_id

    with pytest.raises(ValueError, match="not supported"):
        run_stripe_object_by_id(None, "stripe_invoice_line_items", "il_x")


def test_run_stripe_object_by_id_rejects_subscription_items():
    from src.stripe.orchestrator import run_stripe_object_by_id

    with pytest.raises(ValueError, match="not supported"):
        run_stripe_object_by_id(None, "stripe_subscription_items", "si_x")

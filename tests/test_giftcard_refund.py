import pytest
from decimal import Decimal
from django_scopes import scopes_disabled
from pretix.base.models import GiftCard, Team

from pretix_apicustomerlogin.views import GiftCardRefundSerializer


def api_url(event):
    return "/api/v1/organizers/{}/events/{}/giftcard_refunds/create/".format(
        event.organizer.slug, event.slug
    )


@pytest.mark.django_db
def test_serializer_requires_order_code():
    serializer = GiftCardRefundSerializer(data={"amount": "5.00"})
    assert not serializer.is_valid()
    assert "order_code" in serializer.errors


@pytest.mark.django_db
@scopes_disabled()
def test_refund_creates_giftcard(token_client, event, paid_order):
    response = token_client.post(
        api_url(event),
        {
            "order_code": paid_order.code,
            "amount": "5.00",
            "comment": "Refund as gift card",
            "expires": "2030-01-31",
        },
        format="json",
    )

    assert response.status_code == 201, response.data
    refund = paid_order.refunds.get()
    assert refund.provider == "giftcard"
    assert refund.state == "done"
    assert refund.amount == Decimal("5.00")
    assert refund.comment == "Refund as gift card"

    giftcard = GiftCard.objects.get(pk=refund.info_data["gift_card"])
    assert giftcard.value == Decimal("5.00")
    assert giftcard.currency == event.currency
    assert giftcard.testmode == paid_order.testmode
    assert giftcard.customer is None
    assert giftcard.expires is not None
    assert giftcard.transactions.get().refund == refund

    assert response.data["refund"]["local_id"] == refund.local_id
    assert response.data["giftcard"]["secret"] == giftcard.secret
    assert paid_order.payment_refund_sum == Decimal("18.00")


@pytest.mark.django_db
@scopes_disabled()
def test_refund_without_amount_uses_full_refundable_amount(
    token_client, event, paid_order
):
    response = token_client.post(
        api_url(event), {"order_code": paid_order.code}, format="json"
    )

    assert response.status_code == 201, response.data
    assert paid_order.refunds.get().amount == Decimal("23.00")
    assert paid_order.payment_refund_sum == Decimal("0.00")


@pytest.mark.django_db
@scopes_disabled()
def test_refund_amount_cannot_exceed_refundable_amount(
    token_client, event, paid_order, organizer
):
    response = token_client.post(
        api_url(event),
        {"order_code": paid_order.code, "amount": "24.00"},
        format="json",
    )

    assert response.status_code == 400
    assert "amount" in response.data
    assert not paid_order.refunds.exists()
    assert not organizer.issued_gift_cards.exists()


@pytest.mark.django_db
@scopes_disabled()
def test_write_permission_is_required(client, organizer, event, paid_order):
    team = Team.objects.create(
        organizer=organizer,
        name="Read-only",
        all_events=True,
        all_event_permissions=False,
        limit_event_permissions={"event.orders:read": True},
    )
    token = team.tokens.create(name="Read-only token")
    client.credentials(HTTP_AUTHORIZATION="Token " + token.token)

    response = client.post(
        api_url(event),
        {"order_code": paid_order.code, "amount": "5.00"},
        format="json",
    )

    assert response.status_code == 403
    assert not paid_order.refunds.exists()

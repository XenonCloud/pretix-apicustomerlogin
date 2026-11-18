import pytest
from datetime import datetime, timezone
from decimal import Decimal
from django.utils.timezone import now
from django_scopes import scopes_disabled
from pretix.base.models import Event, Order, OrderPayment, Organizer, Team
from rest_framework.test import APIClient


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
@scopes_disabled()
def organizer():
    return Organizer.objects.create(name="Dummy", slug="dummy")


@pytest.fixture
@scopes_disabled()
def event(organizer):
    return Event.objects.create(
        organizer=organizer,
        name="Dummy",
        slug="dummy",
        date_from=datetime(2026, 12, 27, 10, 0, 0, tzinfo=timezone.utc),
        is_public=True,
        plugins="pretix_apicustomerlogin",
    )


@pytest.fixture
@scopes_disabled()
def team(organizer):
    return Team.objects.create(
        organizer=organizer,
        name="Test-Team",
        all_events=True,
        all_event_permissions=True,
        all_organizer_permissions=True,
    )


@pytest.fixture
def token_client(client, team):
    token = team.tokens.create(name="Foo")
    client.credentials(HTTP_AUTHORIZATION="Token " + token.token)
    return client


@pytest.fixture
@scopes_disabled()
def paid_order(event):
    order = Order.objects.create(
        code="ABC123",
        event=event,
        email="customer@example.com",
        status=Order.STATUS_PAID,
        total=Decimal("23.00"),
        locale="en",
        datetime=datetime(2026, 12, 1, 10, 0, 0, tzinfo=timezone.utc),
        expires=datetime(2026, 12, 10, 10, 0, 0, tzinfo=timezone.utc),
        sales_channel=event.organizer.sales_channels.get(identifier="web"),
    )
    order.payments.create(
        provider="manual",
        state=OrderPayment.PAYMENT_STATE_CONFIRMED,
        amount=Decimal("23.00"),
        payment_date=now(),
    )
    return order

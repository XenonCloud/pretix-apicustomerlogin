from datetime import datetime, time
from decimal import Decimal
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils.timezone import make_aware, now
from pretix.api.serializers.order import OrderRefundSerializer
from pretix.api.serializers.organizer import CustomerSerializer, GiftCardSerializer
from pretix.base.models import Customer, Order, OrderPayment, OrderRefund
from pretix.base.payment import GiftCardPayment, PaymentException
from pretix.helpers import OF_SELF
from pretix.plugins.paypal2.models import ReferencedPayPalObject
from pretix.plugins.stripe.models import ReferencedStripeObject
from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet


class CustomerApiLoginViewSet(ViewSet):
    permission = "organizer.giftcards:read"

    @action(detail=False, methods=["POST"], url_path="login")
    def login(self, request, **kwargs):  # , request, **kwargs

        email = serializers.CharField(
            allow_blank=False, allow_null=False
        ).to_internal_value(request.data.get("email", ""))

        password = serializers.CharField(
            allow_blank=False, allow_null=False
        ).to_internal_value(request.data.get("password", ""))

        customer = Customer.objects.filter(
            organizer__slug=kwargs["organizer"], email=email, is_active=True
        ).first()

        # customer.set_password(password)
        # customer.save()

        if not customer or not customer.check_password(password):
            return Response(status=401)

        return Response(CustomerSerializer(customer).data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["POST"], url_path="set_password")
    def set_password(self, request, **kwargs):  # , request, **kwargs

        email = serializers.CharField(
            allow_blank=False, allow_null=False
        ).to_internal_value(request.data.get("email", ""))

        password = serializers.CharField(
            allow_blank=False, allow_null=False
        ).to_internal_value(request.data.get("password", ""))

        customer = Customer.objects.filter(
            organizer__slug=kwargs["organizer"], email=email, is_active=True
        ).first()

        customer.set_password(password)
        customer.save()

        return Response(CustomerSerializer(customer).data, status=status.HTTP_200_OK)


class OrderPaymentViewSet(ViewSet):
    permission = "event.orders:read"
    write_permission = "event.orders:write"

    def _get_payment(self, request, **kwargs):
        order_code = request.data.get("order_code")
        local_payment_id = request.data.get("local_payment_id")

        if not order_code or not local_payment_id:
            return (
                None,
                None,
                Response(
                    {"detail": "order_code and local_payment_id are required."},
                    status=status.HTTP_400_BAD_REQUEST,
                ),
            )

        try:
            order = Order.objects.get(
                event__organizer__slug=kwargs["organizer"],
                event__slug=kwargs["event"],
                code=order_code,
            )
        except Order.DoesNotExist:
            return (
                None,
                None,
                Response(
                    {"detail": "Order not found."},
                    status=status.HTTP_404_NOT_FOUND,
                ),
            )

        try:
            payment = OrderPayment.objects.get(
                order=order,
                local_id=local_payment_id,
            )
        except OrderPayment.DoesNotExist:
            return (
                None,
                None,
                Response(
                    {"detail": "Payment not found."},
                    status=status.HTTP_404_NOT_FOUND,
                ),
            )

        return order, payment, None

    @action(detail=False, methods=["POST"], url_path="add_stripe_reference")
    def add_stripe_reference(self, request, **kwargs):
        order, payment, res = self._get_payment(request, **kwargs)
        if res is not None:
            return res

        reference = request.data.get("reference")
        if not reference:
            return Response(
                {"detail": "reference is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        obj, created = ReferencedStripeObject.objects.get_or_create(
            reference=reference,
            defaults={"order": order, "payment": payment},
        )

        return Response(
            {
                "id": obj.pk,
                "reference": obj.reference,
                "order": order.code,
                "payment": payment.full_id,
                "created": created,
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @action(detail=False, methods=["POST"], url_path="add_paypal_reference")
    def add_paypal_reference(self, request, **kwargs):
        order, payment, res = self._get_payment(request, **kwargs)
        if res is not None:
            return res

        reference = request.data.get("reference")
        if not reference:
            return Response(
                {"detail": "reference is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        obj, created = ReferencedPayPalObject.objects.get_or_create(
            reference=reference,
            defaults={"order": order, "payment": payment},
        )

        return Response(
            {
                "id": obj.pk,
                "reference": obj.reference,
                "order": order.code,
                "payment": payment.full_id,
                "created": created,
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @action(detail=False, methods=["POST"], url_path="update_payment_info")
    def update_payment_info(self, request, **kwargs):
        order, payment, res = self._get_payment(request, **kwargs)
        if res is not None:
            return res

        info = request.data.get("info")
        if info is None or not isinstance(info, dict):
            return Response(
                {"detail": "info must be a JSON object."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        current = payment.info_data or {}
        current.update(info)
        payment.info_data = current
        payment.save(update_fields=["info"])

        return Response(
            {
                "order": order.code,
                "payment": payment.full_id,
                "info": payment.info_data,
            },
            status=status.HTTP_200_OK,
        )


class GiftCardRefundSerializer(serializers.Serializer):
    order_code = serializers.CharField(required=True, allow_blank=False)
    amount = serializers.DecimalField(
        max_digits=13, decimal_places=2, min_value=Decimal("0.01"), required=False
    )
    comment = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    expires = serializers.DateField(required=False, allow_null=True)
    conditions = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )


class GiftCardRefundViewSet(ViewSet):
    permission = "event.orders:read"
    write_permission = "event.orders:write"

    @action(detail=False, methods=["POST"], url_path="create")
    def refund(self, request, **kwargs):
        serializer = GiftCardRefundSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        order = get_object_or_404(Order, event=request.event, code=data["order_code"])
        user = request.user if request.user.is_authenticated else None

        with transaction.atomic():
            order = Order.objects.select_for_update(of=OF_SELF).get(pk=order.pk)
            refundable = order.payment_refund_sum
            amount = data.get("amount")
            if amount is None:
                amount = refundable
            if amount <= Decimal("0.00"):
                raise serializers.ValidationError(
                    {"amount": "No refundable amount is available for this order."}
                )
            if amount > refundable:
                raise serializers.ValidationError(
                    {
                        "amount": "Refund amount cannot exceed the refundable amount "
                        "of the order."
                    }
                )

            if "expires" in data:
                expires = data["expires"]
                if expires is not None:
                    expires = make_aware(
                        datetime.combine(expires, time(hour=23, minute=59, second=59)),
                        request.event.timezone,
                    )
            else:
                expires = request.organizer.default_gift_card_expiry

            giftcard = request.organizer.issued_gift_cards.create(
                expires=expires,
                currency=request.event.currency,
                customer=order.customer,
                testmode=order.testmode,
                conditions=data.get("conditions"),
            )
            giftcard.log_action(
                "pretix.giftcards.created", data={}, user=user, auth=request.auth
            )

            refund = OrderRefund(
                order=order,
                payment=None,
                source=OrderRefund.REFUND_SOURCE_ADMIN,
                state=OrderRefund.REFUND_STATE_CREATED,
                execution_date=now(),
                amount=amount,
                provider="giftcard",
                comment=data.get("comment"),
            )
            refund.info_data = {"gift_card": giftcard.pk}
            refund.save()
            order.log_action(
                "pretix.event.order.refund.created",
                {"local_id": refund.local_id, "provider": refund.provider},
                user=user,
                auth=request.auth,
            )

            try:
                GiftCardPayment(request.event).execute_refund(refund)
            except PaymentException as e:
                refund.state = OrderRefund.REFUND_STATE_FAILED
                refund.save(update_fields=["state"])
                order.log_action(
                    "pretix.event.order.refund.failed",
                    {
                        "local_id": refund.local_id,
                        "provider": refund.provider,
                        "error": str(e),
                    },
                    user=user,
                    auth=request.auth,
                )
                return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        context = {
            "request": request,
            "organizer": request.organizer,
            "event": request.event,
        }
        return Response(
            {
                "refund": OrderRefundSerializer(refund, context=context).data,
                "giftcard": GiftCardSerializer(giftcard, context=context).data,
            },
            status=status.HTTP_201_CREATED,
        )

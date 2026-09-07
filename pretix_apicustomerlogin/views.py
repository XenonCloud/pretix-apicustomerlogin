from django.views import View
from pretix.api.serializers.organizer import CustomerCreateSerializer, CustomerSerializer
from pretix.base.models import Customer, Order, OrderPayment
from pretix.plugins.stripe.models import ReferencedStripeObject
from rest_framework import status, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet


class CustomerApiLoginViewSet(ViewSet):
    permission = 'organizer.giftcards:read'

    @action(detail=False, methods=["POST"], url_path="login")
    def login(self, request, **kwargs):  # , request, **kwargs

        email = serializers.CharField(allow_blank=False, allow_null=False).to_internal_value(
            request.data.get('email', '')
        )

        password = serializers.CharField(allow_blank=False, allow_null=False).to_internal_value(
            request.data.get('password', '')
        )

        customer = Customer.objects.filter(
            organizer__slug=kwargs["organizer"],
            email=email,
            is_active=True
        ).first()

        # customer.set_password(password)
        # customer.save()

        if not customer or not customer.check_password(password):
            return Response(status=401)

        return Response(CustomerSerializer(customer).data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["POST"], url_path="set_password")
    def set_password(self, request, **kwargs):  # , request, **kwargs

        email = serializers.CharField(allow_blank=False, allow_null=False).to_internal_value(
            request.data.get('email', '')
        )

        password = serializers.CharField(allow_blank=False, allow_null=False).to_internal_value(
            request.data.get('password', '')
        )

        customer = Customer.objects.filter(
            organizer__slug=kwargs["organizer"],
            email=email,
            is_active=True
        ).first()

        customer.set_password(password)
        customer.save()

        return Response(CustomerSerializer(customer).data, status=status.HTTP_200_OK)


class OrderPaymentViewSet(ViewSet):
    permission = 'event.orders:read'
    write_permission = 'event.orders:write'

    def _get_payment(self, request, **kwargs):
        order_code = request.data.get('order_code')
        local_payment_id = request.data.get('local_payment_id')

        if not order_code or not local_payment_id:
            return None, None, Response(
                {'detail': 'order_code and local_payment_id are required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            order = Order.objects.get(
                event__organizer__slug=kwargs['organizer'],
                event__slug=kwargs['event'],
                code=order_code,
            )
        except Order.DoesNotExist:
            return None, None, Response(
                {'detail': 'Order not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            payment = OrderPayment.objects.get(
                order=order,
                local_id=local_payment_id,
            )
        except OrderPayment.DoesNotExist:
            return None, None, Response(
                {'detail': 'Payment not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        return order, payment, None

    @action(detail=False, methods=["POST"], url_path="add_stripe_reference")
    def add_stripe_reference(self, request, **kwargs):
        order, payment, res = self._get_payment(request, **kwargs)
        if res is not None:
            return res

        reference = request.data.get('reference')
        if not reference:
            return Response(
                {'detail': 'reference is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        obj, created = ReferencedStripeObject.objects.get_or_create(
            reference=reference,
            defaults={'order': order, 'payment': payment},
        )

        return Response(
            {
                'id': obj.pk,
                'reference': obj.reference,
                'order': order.code,
                'payment': payment.full_id,
                'created': created,
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @action(detail=False, methods=["POST"], url_path="update_payment_info")
    def update_payment_info(self, request, **kwargs):
        order, payment, res = self._get_payment(request, **kwargs)
        if res is not None:
            return res

        info = request.data.get('info')
        if info is None or not isinstance(info, dict):
            return Response(
                {'detail': 'info must be a JSON object.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        current = payment.info_data or {}
        current.update(info)
        payment.info_data = current
        payment.save(update_fields=['info'])

        return Response(
            {
                'order': order.code,
                'payment': payment.full_id,
                'info': payment.info_data,
            },
            status=status.HTTP_200_OK,
        )
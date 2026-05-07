from django.views import View
from pretix.api.serializers.organizer import CustomerCreateSerializer, CustomerSerializer
from pretix.base.models import Customer
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

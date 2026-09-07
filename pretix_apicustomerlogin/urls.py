from pretix.api.urls import event_router, router, orga_router

from pretix_apicustomerlogin.views import CustomerApiLoginViewSet, OrderPaymentViewSet

orga_router.register('customer_login', CustomerApiLoginViewSet, 'customer_login')

event_router.register('order_payment', OrderPaymentViewSet, 'order_payment')

urlpatterns = []
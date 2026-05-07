from pretix.api.urls import event_router, router, orga_router

from pretix_apicustomerlogin.views import CustomerApiLoginViewSet

orga_router.register('customer_login', CustomerApiLoginViewSet, 'customer_login')

urlpatterns = []
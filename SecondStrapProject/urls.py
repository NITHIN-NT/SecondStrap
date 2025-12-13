from django.contrib import admin
from django.urls import path, include
from .views import custom_inactive_account_view
from accounts.views import google_callback_safe
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("defaultadmin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("accounts/inactive/", custom_inactive_account_view, name="account_inactive"),
    path("accounts/google/login/callback/", google_callback_safe, name="google_callback"),
    path("accounts/", include("allauth.socialaccount.providers.google.urls")),
    path("", include("products.urls")),
    path("wishlist/", include("userFolder.wishlist.urls")),
    path("cart/", include("userFolder.cart.urls")),
    path("cart/checkout/", include("userFolder.checkout.urls")),
    path("order/",include("userFolder.order.urls")),
    path("profile/", include("userFolder.userprofile.urls"), name="userprofile"),
    path('payment/', include('userFolder.payment.urls')),
    path('wallet/',include("userFolder.wallet.urls")),
    path("superuser/", include("Admin.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

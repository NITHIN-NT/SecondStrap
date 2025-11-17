from django.contrib import admin
from django.urls import path,include
from .views import custom_inactive_account_view

urlpatterns = [
    path('defaultadmin/', admin.site.urls),
    path('',include('products.urls')),
    path('profile/',include('userFolder.userprofile.urls')),
    path('accounts/', include('accounts.urls')),
    path('accounts/inactive/', custom_inactive_account_view, name='account_inactive'),
    path('accounts/', include('allauth.urls')),

    path('wishlist/',include('userFolder.wishlist.urls')),
    path('cart/',include('userFolder.cart.urls')),


    path('superuser/',include('Admin.urls'))
]

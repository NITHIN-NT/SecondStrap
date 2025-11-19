from django.contrib import admin
from django.urls import path,include
from .views import custom_inactive_account_view   
from accounts.views import google_callback_safe 
urlpatterns = [
    path('defaultadmin/', admin.site.urls),     

    path('accounts/', include('accounts.urls')),
    path('accounts/inactive/', custom_inactive_account_view, name='account_inactive'),

    path('accounts/google/login/callback/', google_callback_safe, name='google_callback'),
    path('accounts/', include('allauth.socialaccount.providers.google.urls')),


    path('',include('products.urls')),
    path('wishlist/',include('userFolder.wishlist.urls')),
    path('cart/',include('userFolder.cart.urls')),
    path('profile/',include('userFolder.userprofile.urls'),name='userprofile'),

    path('superuser/',include('Admin.urls'))
]

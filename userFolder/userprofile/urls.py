from django.urls import path
from .views import * 
urlpatterns = [
    path('info/',ProfileView.as_view(),name = 'profile_view_user'),
    path('address/',ProfileAddressView.as_view(),name = 'profile_adress'),
    path('payment/',ProfilePaymentView.as_view(),name = 'profile_payment'),
    path('order/',ProfileOrderView.as_view(),name = 'profile_order'),
    path('Wallet/',ProfileWalletView.as_view(),name = 'profile_wallet'),

    # api endpoints

    path('api/update-info',edit_action,name='update_info_axios'),

    path('info/email/send',verify_action,name='send_otp'),
    path('info/email/verify',otp_verification,name='verify_otp_axios')
]

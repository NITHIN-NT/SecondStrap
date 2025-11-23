from django.urls import path
from .views import * 
urlpatterns = [
    path('info/',ProfileView.as_view(),name = 'profile_view_user'),
    path('address/',ProfileAddressView.as_view(),name = 'profile_address'),
    path('payment/',ProfilePaymentView.as_view(),name = 'profile_payment'),
    path('order/',ProfileOrderView.as_view(),name = 'profile_order'),
    path('Wallet/',ProfileWalletView.as_view(),name = 'profile_wallet'),
    path('password/change/',change_password,name='change_password'),

    # api endpoints

    path('api/update-info',edit_action,name='update_info_axios'),

    path('info/email/send',verify_action,name='send_otp'),
    path('info/email/verify',otp_verification,name='verify_otp_axios'),
    path('profile/edit',update_profile_picture,name='update_profile_picture'),

    path('addresses/manage/',manage_address, name='add_address'),
    path('addresses/fetch/<int:address_id>/',manage_address, name='fetch_address'),
    path('addresses/delete/<int:address_id>/',delete_address, name='delete_address'),
]

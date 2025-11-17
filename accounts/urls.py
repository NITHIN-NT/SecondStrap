from django.urls import path
from . import views
from .views import SendOTPView,VerifyOTPView,NewPasswordView

urlpatterns = [
    path('signup/', views.signup_view, name='signup'),
    path('activate/', views.activate_account, name='activate_account'),
    path('verify/resend',views.resent_otp,name='resent_otp'),

    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    path('forgot/password/',SendOTPView.as_view(),name='forgot-password'),
    path('verify/otp/',VerifyOTPView.as_view(),name='forgot-verify-otp'),
    path('new/password/',NewPasswordView.as_view(),name='set-new-password')
]

from django.urls import path
from .views import *

urlpatterns = [
    path("", CheckOutView.as_view(), name="checkout"),
]

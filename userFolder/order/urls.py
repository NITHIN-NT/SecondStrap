from django.urls import path
from .views import *

urlpatterns = [
    path("", order, name="order"),
    path("order-id/",order_details_view,name="order_details")
]

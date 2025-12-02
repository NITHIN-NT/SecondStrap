from django.urls import path
from .views import *

urlpatterns = [
    path("", order, name="order"),
    path("<str:order_id>/",order_details_view,name="order_details")
]

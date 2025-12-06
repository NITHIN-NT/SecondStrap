from django.urls import path
from .views import *

urlpatterns = [
    path("", order, name="order"),
    path("return/<str:order_id>",return_order_view,name='return_order_view'),
    path("return/cancel/<str:order_id>",cancel_return_order_view,name='cancel_return_order_view'),
]

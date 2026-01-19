from django.urls import path
from .views import *

urlpatterns = [
    path("", order, name="order"),
    path("processing/<str:order_id>/", order_processing_animation_view, name="order_processing_animation"),
    path("send-order-email/<str:order_id>/", send_order_email_ajax, name="send_order_email_ajax"),
    path("return/<str:order_id>",return_order_view,name='return_order_view'),
    path("return/cancel/<str:order_id>",cancel_return_order_view,name='cancel_return_order_view'),
    path("cancel/<str:order_id>",cancel_order_view,name='cancel_order_view'),
]

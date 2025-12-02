from django.urls import path
from .views import *

urlpatterns = [
    path("", order, name="order"),
    path("<str:order_id>/",order_details_view,name="order_details"),
    path("<str:order_id>/download-invoice",download_invoice_view,name='download_invoice')
]

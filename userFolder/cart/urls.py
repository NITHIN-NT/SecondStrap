from django.urls import path
from .views import *

urlpatterns = [
    path("", CartView.as_view(), name="cart"),
    path("add/", cart_item_add, name="add_cart"),
    path("remove/", cart_item_remove, name="remove_cart_item"),
    path("quantity/add",update_cart_item_quantity,name='update_cart_item_quantity'),
]

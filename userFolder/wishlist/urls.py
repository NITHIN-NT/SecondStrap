from django.urls import path
from .views import *
urlpatterns = [
    path('',wishlistView,name='wishlist'),
    path('add/',add_to_wishlist ,name='add_to_wishlist'),
    path('add/cart/',add_to_cart,name='add_to_cart'),
    path('remove/',remove_from_wishlist,name='remove_from_wishlist')
]

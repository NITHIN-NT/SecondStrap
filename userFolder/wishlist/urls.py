from django.urls import path
from .views import *
urlpatterns = [
    path('',wishlistView,name='wishlist'),
    path('add/',add_to_wishlist ,name='add_to_wishlist')
]

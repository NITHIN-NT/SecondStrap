from django.urls import path
from . import views
urlpatterns = [
    path('',views.wishlistView,name='wishlist')
]

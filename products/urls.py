from django.urls import path
from . import views
from .views import HomePageView,ProductDetailedView,AboutView
from django.conf import settings
from django.conf.urls.static import static
from userFolder.review.views import submit_review

urlpatterns = [
    path('',HomePageView.as_view(),name='Home_page_user'),
    path('offer/list',views.samble,name='sambe'),
    path('about/',AboutView.as_view(),name='About_page_user'),
    path('review/',submit_review,name='submit_review'),
    path('products/',views.product_list_view,name='products_page_user'),
    path('products/<slug:slug>',ProductDetailedView.as_view(),name='Product_card_view'),
    path('api/get-offers/', views.get_offers, name='get_offers'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL,document_root=settings.MEDIA_ROOT)
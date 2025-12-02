from django.urls import path
from . import views
from .views import AdminProductsView,AdminCategoryView,AdminUserView,AdminHome,StockManagementView,AdminOrderView
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [

    path('',views.admin_login,name='admin_login'),
    path('forget/',views.admin_forgot,name='admin_forgot_password'),
    path('verify/',views.admin_otp_verification,name='admin_otp_verification'),
    path('reset/',views.admin_reset,name='admin_reset'),
    path('logout/',views.admin_logout,name='admin_logout'),

    path('strap/',AdminHome.as_view(),name='admin_home'),

    path('users/',AdminUserView.as_view(),name='admin_user'),
    path('user/block/<int:id>',views.toggle_user_block,name='admin_user_block'),

    path('products/',AdminProductsView.as_view(),name='admin_products'),
    path('products/add',views.manage_product,name='admin_product_add'),
    path('products/edit/<int:id>',views.manage_product,name='admin_product_edit'),
    path('products/block/<int:id>',views.toggle_product_block,name='admin_product_block'),

    path('category/',AdminCategoryView.as_view(),name='admin_category'),
    path('category/block/<int:id>',views.toggle_category_block,name='admin_category_block'),
    path('category/add',views.admin_category_management,name='admin_category_add'),
    path('category/edit/<int:id>',views.admin_category_management,name='admin_category_edit'),

    path('stock/',StockManagementView.as_view(),name='stock_mangement'),
    
    path('order/',AdminOrderView.as_view(),name='Admin_order'),
    path('order/<str:order_id>',views.admin_order_detailed_view,name='Admin_order_detailed_view'),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL,document_root=settings.MEDIA_ROOT)
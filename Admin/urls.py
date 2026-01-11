from django.urls import path

from .views.views import *
from .views.sales_views import *
from .views.users_views import *
from .views.product_views import *
from .views.order_views import *
from .views.coupon_views import *

from offer.views import *
from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls import handler404

handler404 = 'Admin.views.custom_404_handler'

urlpatterns = [

    path('',admin_login,name='admin_login'),
    path('forget/',admin_forgot,name='admin_forgot_password'),
    path('verify/',admin_otp_verification,name='admin_otp_verification'),
    path('reset/',admin_reset,name='admin_reset'),
    path('logout/',admin_logout,name='admin_logout'),

    path('strap/',admin_home,name='admin_home'),

    path('users/',AdminUserView.as_view(),name='admin_user'),
    path('user/block/<int:id>',toggle_user_block,name='admin_user_block'),

    path('products/',AdminProductsView.as_view(),name='admin_products'),
    path('products/add',manage_product,name='admin_product_add'),
    path('products/edit/<int:id>',manage_product,name='admin_product_edit'),
    path('products/block/<int:id>',toggle_product_block,name='admin_product_block'),

    path('category/',AdminCategoryView.as_view(),name='admin_category'),
    path('category/block/<int:id>',toggle_category_block,name='admin_category_block'),
    path('category/add',admin_category_management,name='admin_category_add'),
    path('category/edit/<int:id>',admin_category_management,name='admin_category_edit'),

    path('stock/',StockManagementView.as_view(),name='stock_mangement'),
    
    path('order/',AdminOrderView.as_view(),name='Admin_order'),
    path('order/<str:order_id>/',admin_order_detailed_view,name='Admin_order_detailed_view'),
    path('order/update/<str:order_id>/',admin_order_status_update,name='order_status_update'),
    path('order/manage-return/<int:item_id>/<str:order_id>/',manage_return_request,name='manage_return_item'),
    
    path('offer/',offers_view,name='offers_view'),
    path('offer/manage-offer/',manage_offer_view,name='manage_offer_view'),
    path('offer/manage-offer/edit/<int:pk>',manage_offer_view,name='edit_offer_view'),
    path('offer/<int:pk>',OfferDetailedView.as_view(),name='Offer_detailed_view'),
    path('offer/delete/',delete_offer_view,name='Offer_delete_view'),
    path('offer/manage-offer/products/search/',search_products,name='search_products'),
    path('offer/manage-offer/categories/search/',search_category,name='search_categories'),
    
    path('coupon/',CouponAdminView.as_view(),name='admin_coupons'),
    path('coupon/manage',manage_coupon_view,name='admin_manage_coupon'),
    path('coupon/manage/<int:id>/',manage_coupon_view,name='admin_manage_coupon'),
    path('coupon/delete/<int:pk>/',CouponDeleteView.as_view(),name='admin_coupon_delete_view'),
    path('coupon/history',CouponHistoryView.as_view(),name='admin_coupon_history'),
    
    path('sales/report/',sale_report_view,name='admin_sale_report'),
    path('sales/order/<str:order_id>/',admin_order_detailed_view,name='report_order_status_update'),
    path('sales-report/export/pdf/', sales_report_pdf, name='sales_report_pdf'),
    path('sales-report/export/excel/', sales_report_excel, name='sales_report_excel'),

    path('customer-messages/',CustomerMessageView.as_view(),name='admin_customer_message_view'),
    path('customer-messages/mark-read/', mark_message_read, name='mark_message_read'),
    
    path('thumbanail/',thumbanail_view,name='thumbail_view'),
    path('thumbanail/add',upload_thumbnail,name='upload_thumbnail'),
    path('thumbnail/delete/<int:image_id>/', delete_thumbnail, name='delete_thumbnail'),
    path('thumbnail/toggle/<int:image_id>/',toggle_visibility_view, name='toggle_thumbnail'),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL,document_root=settings.MEDIA_ROOT)
from django.urls import path
from . import views

urlpatterns = [
    path('', views.product_list),

    path('products/', views.product_list),
    path('products/info/', views.product_info),
    path('products/<int:pk>/', views.product_infobyid),
    path('products/<int:pk>/update/', views.update_item),


    path('orders/', views.order_list),
    path('orders/<uuid:order_id>/', views.order_info),

    path('users/<int:user_id>/orders/', views.user_orders),
    path(
        'users/<int:user_id>/orders/<uuid:order_id>/',
        views.user_order
    ),
    path('users/<int:user_id>', views.user_info),

]
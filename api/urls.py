from django.urls import path
from . import views

urlpatterns = [
    path('', views.product_list),
    path('add/', views.addItem),
    path('products/', views.product_list),
    path('orders/', views.order_list),
        path('products/info/', views.product_info),


]
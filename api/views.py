from django.db.models import Max,Q
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAdminUser , AllowAny
from rest_framework import status

from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from base .models import Item , OrderItem, Order , User
from .serializers import ItemSerializer,OrderSerializer , ItemInfoSerializer , UserInfoSerializer , UserCreateSerializer


# get and search products
@api_view(['GET','POST'])
def product_list(request):

    if request.method == 'GET':
        search = request.query_params.get('search')

        if search:
            products = Item.objects.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search)
            )
        else:
            products = Item.objects.all()

        serializer = ItemSerializer(products, many=True)
        return Response(serializer.data)

    elif request.method == 'POST':
        serializer = ItemSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )

@api_view(['PUT', 'PATCH', 'DELETE'])
def update_item(request, pk):
    item = get_object_or_404(Item, id=pk)

    if request.method == 'DELETE':
        item.delete()
        return Response(
            {"message": "Product deleted successfully"},
            status=status.HTTP_204_NO_CONTENT
        )

    serializer = ItemSerializer(
        item,
        data=request.data,
        partial=request.method == 'PATCH'
    )

    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)

    return Response(
        serializer.errors,
        status=status.HTTP_400_BAD_REQUEST
    )


@api_view(['GET'])
def order_list(request):
    orders = Order.objects.all()
    serializer = OrderSerializer(orders, many = True)
    return Response(serializer.data)

@api_view(['GET'])
def order_info(request,order_id):
    orders = Order.objects.get(order_id = order_id)
    serializer = OrderSerializer(orders)
    return Response(serializer.data)

@api_view(['GET'])
def product_info(request):
    products = Item.objects.all()
    serializer = ItemInfoSerializer(
        {
            'product': products,
            'count' : len(products),
            'max_price' : products.aggregate(max_price = Max('price'))['max_price']
        }
    )
    return Response(serializer.data)


# get user info using userid
@api_view(['GET', 'PUT', 'PATCH'])
def user_info(request, user_id):
    user = get_object_or_404(User, id=user_id)

    if request.method == 'GET':
        serializer = UserInfoSerializer(user)
        return Response(serializer.data)

    serializer = UserInfoSerializer(
        user,
        data=request.data,
        partial=request.method == 'PATCH'
    )

    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)

    return Response(
        serializer.errors,
        status=status.HTTP_400_BAD_REQUEST
    )

@api_view(['POST'])
def create_user(request):
    serializer = UserCreateSerializer(data=request.data)

    if serializer.is_valid():
        serializer.save()
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED
        )

    return Response(
        serializer.errors,
        status=status.HTTP_400_BAD_REQUEST
    )

@api_view(['GET'])
def product_infobyid(request , pk):
    product = Item.objects.get(id = pk)
    serializer = ItemSerializer(
        product
    )
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def user_orders(request, user_id):
    orders = Order.objects.filter(user_id=user_id)
    serializer = OrderSerializer(orders, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def user_order(request, user_id, order_id):
    order = get_object_or_404(
        Order,
        user_id=user_id,
        order_id=order_id
    )

    serializer = OrderSerializer(order)

    return Response(serializer.data)
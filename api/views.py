from django.db.models import Max,Q
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAdminUser , AllowAny
from rest_framework import status

from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from base .models import Item , OrderItem, Order , User
from .serializers import ItemSerializer,OrderSerializer , ItemInfoSerializer , UserInfoSerializer , UserCreateSerializer , OrderItemSerializer


# get and search products
@api_view(['GET','POST'])
def product_list(request):

    if request.method == 'GET':

        products = Item.objects.all()

        search = request.query_params.get('search')
        min_price = request.query_params.get('min_price')
        max_price = request.query_params.get('max_price')
        in_stock = request.query_params.get('in_stock')
        sort_by = request.query_params.get('sort_by')

        if search:
            products = products.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search)
            )

        if min_price:
            products = products.filter(price__gte=min_price)

        if max_price:
            products = products.filter(price__lte=max_price)

        if in_stock == 'true':
            products = products.filter(stock__gt=0)

        if sort_by == 'price':
            products = products.order_by('price')
        elif sort_by == '-price':
            products = products.order_by('-price')

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


@api_view(['GET','POST'])
@permission_classes([AllowAny])
def user_orders(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if request.method == 'GET':
        orders = Order.objects.filter(user=user)
        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)

    if request.method == 'POST':
        order = Order.objects.create(user=user)

        serializer = OrderSerializer(order)
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED
        )


@api_view(['GET','PUT','PATCH'])
def user_order(request, user_id, order_id):
    order = get_object_or_404(
        Order,
        user_id=user_id,
        order_id=order_id
    )

    if request.method == 'GET':
        serializer = OrderSerializer(order)
        return Response(serializer.data)

    serializer = OrderSerializer(
        order,
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

# add item to the order id
@api_view(['POST'])
def add_order_item(request, user_id, order_id):

    order = get_object_or_404(
        Order,
        user_id=user_id,
        order_id=order_id
    )

    serializer = OrderItemSerializer(data=request.data)

    if serializer.is_valid():
        serializer.save(order=order)

        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED
        )

    return Response(
        serializer.errors,
        status=status.HTTP_400_BAD_REQUEST
    )

# modify and delete order items
@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
def order_item(request, user_id, order_id, item_id):

    order = get_object_or_404(
        Order,
        user_id=user_id,
        order_id=order_id
    )

    order_item = get_object_or_404(
        OrderItem,
        id=item_id,
        order=order
    )

    if request.method == 'GET':
        serializer = OrderItemSerializer(order_item)
        return Response(serializer.data)

    if request.method == 'DELETE':
        order_item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    serializer = OrderItemSerializer(
        order_item,
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
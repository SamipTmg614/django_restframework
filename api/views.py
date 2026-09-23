from django.db.models import Max,Q
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAdminUser


from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from base .models import Item , OrderItem, Order , User
from .serializers import ItemSerializer,OrderSerializer , ItemInfoSerializer , UserInfoSerializer

@api_view(['POST'])
def addItem(request):

    serializer = ItemSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()

    return Response(serializer.data)

# get and search products
@api_view(['GET'])
def product_list(request):

    search = request.query_params.get('search')
    if search:
        products = Item.objects.filter(
            Q(name__icontains = search)|
            Q(description__icontains = search)
        )
    else:
        products = Item.objects.all()

    serializer = ItemSerializer(products, many = True)
    return Response(serializer.data)

@api_view(['PUT'])
def update_item(request):
    serializer = ItemSerializer(Item)


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
@api_view(['GET'])
def user_info(request,user_id):
    user = get_object_or_404(User,id = user_id)
    serializer = UserInfoSerializer(
        user
    )
    return Response(serializer.data)


@api_view(['GET'])
def product_infobyid(request , pk):
    product = Item.objects.get(id = pk)
    serializer = ItemSerializer(
        product
    )
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAdminUser])
def user_orders(request , pk):
    orders = Order.objects.filter(user_id = pk)
    serializer = OrderSerializer(
        orders, many=True
    )
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
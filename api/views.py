from django.db.models import Max
from rest_framework.response import Response
from rest_framework.decorators import api_view
from base .models import Item , OrderItem, Order
from .serializers import ItemSerializer,OrderSerializer , ItemInfoSerializer

@api_view(['POST'])
def addItem(request):

    serializer = ItemSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()

    return Response(serializer.data)

@api_view(['GET'])
def product_list(request):
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


@api_view(['GET'])
def product_infobyid(request , pk):
    product = Item.objects.get(id = pk)
    serializer = ItemSerializer(
        product
    )
    return Response(serializer.data)

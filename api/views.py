from rest_framework.response import Response
from rest_framework.decorators import api_view
from base .models import Item
from .serializers import ItemSerializer

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
    serializer = ItemSerializer(item)
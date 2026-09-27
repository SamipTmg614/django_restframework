from  rest_framework import serializers
from base.models import Item , User , Order , OrderItem

class ItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = Item
        fields = (
            'name',
            'created',
            'description' ,
            'price',
            'stock'
        )

    def validate_price(self,value):
        if value<=0:
            raise serializers.ValidationError(
                "Price must be greater than 0"
            )
        return value

class OrderItemSerializer(serializers.ModelSerializer):
    product_name =  serializers.CharField(source = 'product.name')
    product_price =  serializers.DecimalField(max_digits=10,decimal_places=2,source = 'product.price')

    class Meta:
        model = OrderItem
        fields = (
            'product_name',
            'product_price',
            'quantity',
            'item_subtotal'

        )

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only = True)
    total_price = serializers.SerializerMethodField()

    def get_total_price(self, obj):
        order_items = obj.items.all()
        return sum(order_item.item_subtotal for order_item in order_items)

    class Meta:
        model = Order
        fields = (
            'order_id',
            'user',
            'created_at',
            'status',
            'items',
            'total_price',
        )

class ItemInfoSerializer(serializers.Serializer):
    # get all products, counts of products , max price
    product = ItemSerializer(many=True)
    count = serializers.IntegerField()
    max_price = serializers.FloatField()

class UserInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            'id',
            'username',
            'first_name',
            'last_name',
            'email'
        )

class UserCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            'username',
            'first_name',
            'last_name',
            'email',
            'password',
        )
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            email=validated_data.get('email', ''),
            password=validated_data['password']
        )

        return user
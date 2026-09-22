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
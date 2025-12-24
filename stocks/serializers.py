from rest_framework import serializers
from .models import StockTrade, Portfolio
from decimal import Decimal


class PortfolioSerializer(serializers.ModelSerializer):
    """Serializer for Portfolio model"""

    class Meta:
        model = Portfolio
        fields = ['id', 'name', 'description', 'created_at']
        read_only_fields = ['id', 'created_at']


class StockTradeSerializer(serializers.ModelSerializer):
    """Serializer for StockTrade model"""
    portfolio = serializers.PrimaryKeyRelatedField(
        queryset=Portfolio.objects.all(), allow_null=True, required=False
    )
    portfolio_name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = StockTrade
        fields = [
            'id',
            'symbol',
            'total_buy_qty',
            'buy_price',
            'total_buy_value',
            'total_sell_qty',
            'sell_price',
            'total_sell_value',
            'balance_qty',
            'ltp',
            'acquisition_cost',
            'percent_holding',
            'current_value',
            'realised_profit_loss',
            'wk_52_high',
            'wk_52_low',
            'portfolio',
            'portfolio_name',
            'date_time_field',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'total_buy_value',
            'total_sell_value',
            'balance_qty',
            'acquisition_cost',
            'percent_holding',
            'current_value',
            'realised_profit_loss',
            'date_time_field',
            'created_at',
            'updated_at',
            'portfolio_name',
        ]

    def get_portfolio_name(self, obj):
        return obj.portfolio.name if obj.portfolio else None

    def validate_symbol(self, value):
        """Validate symbol is not empty"""
        if not value or not value.strip():
            raise serializers.ValidationError("Symbol cannot be empty.")
        return value.strip().upper()

    def validate(self, attrs):
        """Validate the data and quantize decimals"""
        # Ensure buy_price and sell_price are properly formatted
        if 'buy_price' in attrs:
            attrs['buy_price'] = Decimal(str(attrs['buy_price'])).quantize(Decimal('0.01'))
        if 'sell_price' in attrs:
            attrs['sell_price'] = Decimal(str(attrs['sell_price'])).quantize(Decimal('0.01'))
        if 'ltp' in attrs:
            attrs['ltp'] = Decimal(str(attrs['ltp'])).quantize(Decimal('0.01'))
        if 'wk_52_high' in attrs:
            attrs['wk_52_high'] = Decimal(str(attrs['wk_52_high'])).quantize(Decimal('0.01'))
        if 'wk_52_low' in attrs:
            attrs['wk_52_low'] = Decimal(str(attrs['wk_52_low'])).quantize(Decimal('0.01'))
        
        return attrs


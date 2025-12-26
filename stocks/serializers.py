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
        queryset=Portfolio.objects.all(),
        required=True,  # Changed from required=False to True
        write_only=True  # Make it write-only for creation/update
    )
    portfolio_name = serializers.SerializerMethodField(read_only=True)
    portfolio_id = serializers.IntegerField(source='portfolio.id', read_only=True)  # Add this

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
            'portfolio',  # This is write-only
            'portfolio_id',  # This is read-only
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
            'portfolio_id',  # Add this to read_only_fields
        ]

    def get_portfolio_name(self, obj):
        return obj.portfolio.name if obj.portfolio else None

    def validate(self, attrs):
        """Validate the data and quantize decimals"""
        # Check if portfolio is provided during creation
        if self.instance is None and 'portfolio' not in attrs:
            raise serializers.ValidationError({
                'portfolio': 'Portfolio is required when creating a stock.'
            })
        
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

    def create(self, validated_data):
        """Create a new stock trade"""
        portfolio = validated_data.pop('portfolio')
        stock_trade = StockTrade.objects.create(portfolio=portfolio, **validated_data)
        return stock_trade

    def update(self, instance, validated_data):
        """Update an existing stock trade"""
        # Update portfolio if provided
        portfolio = validated_data.pop('portfolio', None)
        if portfolio:
            instance.portfolio = portfolio
        
        # Update other fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.save()
        return instance
from django.contrib import admin
from .models import StockTrade, Portfolio


@admin.register(StockTrade)
class StockTradeAdmin(admin.ModelAdmin):
    """Admin configuration for StockTrade model"""
    list_display = (
        'symbol', 
        'total_buy_qty', 
        'buy_price', 
        'total_buy_value',
        'total_sell_qty',
        'sell_price',
        'total_sell_value',
        'realised_profit_loss',
        'created_at'
    )
    list_filter = ('created_at', 'updated_at')
    search_fields = ('symbol',)
    readonly_fields = (
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
    )
    fieldsets = (
        ('Basic Information', {
            'fields': ('symbol', 'portfolio', 'date_time_field')
        }),
        ('Buy Information', {
            'fields': ('total_buy_qty', 'buy_price', 'total_buy_value')
        }),
        ('Sell Information', {
            'fields': ('total_sell_qty', 'sell_price', 'total_sell_value')
        }),
        ('Calculated Fields', {
            'fields': (
                'balance_qty',
                'acquisition_cost',
                'percent_holding',
                'current_value',
                'realised_profit_loss',
            )
        }),
        ('52 Week Data', {
            'fields': ('wk_52_high', 'wk_52_low')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(Portfolio)
class PortfolioAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')
    search_fields = ('name',)

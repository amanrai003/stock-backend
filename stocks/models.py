from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from datetime import datetime
import pytz

class Portfolio(models.Model):
    name = models.CharField(
        max_length=255,
        unique=True,
        help_text="Portfolio name"
    )
    description = models.TextField(
        blank=True,
        null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Portfolio"
        verbose_name_plural = "Portfolios"

    def __str__(self):
        return self.name
    
class StockTrade(models.Model):
    """Model to store stock trading information"""
    symbol = models.CharField(max_length=50, unique=True, help_text="Stock symbol")
    total_buy_qty = models.IntegerField(validators=[MinValueValidator(0)], help_text="Total buy quantity")
    buy_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=[MinValueValidator(0)],
        help_text="Buy price per share"
    )
    total_buy_value = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0.00'),
        help_text="Total buy value (calculated: total_buy_qty * buy_price)"
    )
    total_sell_qty = models.IntegerField(
        default=0, 
        validators=[MinValueValidator(0)],
        help_text="Total sell quantity"
    )
    sell_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0.00'),
        validators=[MinValueValidator(0)],
        help_text="Sell price per share"
    )
    total_sell_value = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0.00'),
        help_text="Total sell value (calculated: total_sell_qty * sell_price)"
    )
    balance_qty = models.IntegerField(
        default=0,
        help_text="Balance quantity (always saved as 0)"
    )
    ltp = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0.00'),
        validators=[MinValueValidator(0)],
        help_text="ltp price"
    )
    acquisition_cost = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0.00'),
        help_text="Acquisition cost (always 0.00)"
    )
    percent_holding = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=Decimal('0.00'),
        help_text="Percentage holding (always 0.00)"
    )
    current_value = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0.00'),
        help_text="Current value (always 0.00)"
    )
    realised_profit_loss = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0.00'),
        help_text="Realised profit/loss (calculated: sell_price - buy_price)"
    )
    wk_52_high = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0.00'),
        validators=[MinValueValidator(0)],
        help_text="52 week high price"
    )
    wk_52_low = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0.00'),
        validators=[MinValueValidator(0)],
        help_text="52 week low price"
    )
    portfolio = models.ForeignKey(
        Portfolio,
        on_delete=models.CASCADE,
        related_name='stocks',
        null=True,
        blank=True,
        help_text="Parent portfolio"
    )
    date_time_field = models.CharField(
        max_length=100,
        blank=True,
        help_text="Formatted date time string: 'As on Nov 28, 5025 16:00:27 Hours IST'"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Stock Trade'
        verbose_name_plural = 'Stock Trades'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.symbol} - Buy: {self.total_buy_qty} @ {self.buy_price}"

    def format_date_time(self):
        """Format datetime as 'As on Nov 28, 5025 16:00:27 Hours IST'"""
        # Get current datetime in IST timezone
        ist = pytz.timezone('Asia/Kolkata')
        now = datetime.now(ist)
        
        # Format: "As on Nov 28, 5025 16:00:27 Hours IST"
        # Month abbreviation, day, year, time
        month_abbr = now.strftime('%b')
        day = now.strftime('%d').lstrip('0') or '0'  # Remove leading zero from day
        year = now.strftime('%Y')
        time_str = now.strftime('%H:%M:%S')
        
        return f"As on {month_abbr} {day}, {year} {time_str} Hours IST"

    def save(self, *args, **kwargs):
        """Override save to calculate computed fields"""
        # Calculate total_buy_value
        self.total_buy_value = Decimal(str(self.total_buy_qty)) * Decimal(str(self.buy_price))
        
        # Calculate total_sell_value
        self.total_sell_value = Decimal(str(self.total_sell_qty)) * Decimal(str(self.sell_price))
        
        # Always set balance_qty to 0
        self.balance_qty = 0
        
        # Always set acquisition_cost to 0.00
        self.acquisition_cost = Decimal('0.00')
        
        # Always set percent_holding to 0.00
        self.percent_holding = Decimal('0.00')
        
        # Always set current_value to 0.00
        self.current_value = Decimal('0.00')
        
        # Calculate realised_profit_loss (sell_price - buy_price)
        if self.sell_price > 0 and self.buy_price > 0:
            self.realised_profit_loss = Decimal(str(self.sell_price)) - Decimal(str(self.buy_price))
        else:
            self.realised_profit_loss = Decimal('0.00')
        
        # Format and set date_time_field (always update to current time)
        self.date_time_field = self.format_date_time()
        
        # Round all decimal fields to 2 decimal places
        self.total_buy_value = self.total_buy_value.quantize(Decimal('0.01'))
        self.total_sell_value = self.total_sell_value.quantize(Decimal('0.01'))
        self.realised_profit_loss = self.realised_profit_loss.quantize(Decimal('0.01'))
        self.wk_52_high = Decimal(str(self.wk_52_high)).quantize(Decimal('0.01'))
        self.wk_52_low = Decimal(str(self.wk_52_low)).quantize(Decimal('0.01'))
        
        super().save(*args, **kwargs)

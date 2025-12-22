from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.http import HttpResponse
from decimal import Decimal

import stocks
from .models import StockTrade, Portfolio
from .serializers import StockTradeSerializer, PortfolioSerializer


class StockTradeViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing stock trades
    
    list: Get all stock trades
    create: Create a new stock trade
    retrieve: Get a specific stock trade by ID
    update: Update a stock trade (full update)
    partial_update: Update a stock trade (partial update)
    destroy: Delete a stock trade
    """
    queryset = StockTrade.objects.all()
    serializer_class = StockTradeSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'

    def get_queryset(self):
        """Return all stock trades"""
        return StockTrade.objects.all().order_by('-created_at')

    def list(self, request, *args, **kwargs):
        """Get all stock trades"""
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(
            {
                'message': 'Stock trades retrieved successfully',
                'count': len(serializer.data),
                'data': serializer.data
            },
            status=status.HTTP_200_OK
        )

    def create(self, request, *args, **kwargs):
        """Create a new stock trade"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            {
                'message': 'Stock trade created successfully',
                'data': serializer.data
            },
            status=status.HTTP_201_CREATED,
            headers=headers
        )

    def update(self, request, *args, **kwargs):
        """Update a stock trade"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(
            {
                'message': 'Stock trade updated successfully',
                'data': serializer.data
            },
            status=status.HTTP_200_OK
        )

    def destroy(self, request, *args, **kwargs):
        """Delete a stock trade"""
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(
            {'message': 'Stock trade deleted successfully'},
            status=status.HTTP_200_OK
        )

    @action(detail=False, methods=['get'])
    def by_symbol(self, request):
        """Get stock trade by symbol"""
        symbol = request.query_params.get('symbol', None)
        if not symbol:
            return Response(
                {'error': 'Symbol parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            stock_trade = StockTrade.objects.get(symbol=symbol.upper())
            serializer = self.get_serializer(stock_trade)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except StockTrade.DoesNotExist:
            return Response(
                {'error': f'Stock trade with symbol {symbol} not found'},
                status=status.HTTP_404_NOT_FOUND
            )

   # ... inside StockTradeViewSet ...

    @action(detail=False, methods=['get'])
    def download_report(self, request):
        """Download HTML report of all stock trades"""
        stocks = StockTrade.objects.all().order_by('symbol')

        # ---- SAFE TOTAL CALCULATIONS ----
        total_buy_qty = sum(to_int(s.total_buy_qty) for s in stocks)
        total_buy_value = sum(to_decimal(s.total_buy_value) for s in stocks)
        total_sell_qty = sum(to_int(s.total_sell_qty) for s in stocks)
        total_sell_value = sum(to_decimal(s.total_sell_value) for s in stocks)

        # ---- REALISED PROFIT / LOSS ----
        total_realised_profit_loss = Decimal('0.00')

        for stock in stocks:
            buy_qty = int(clean_number(stock.total_buy_qty))
            sell_qty = int(clean_number(stock.total_sell_qty))

            buy_value = clean_number(stock.total_buy_value)
            sell_value = clean_number(stock.total_sell_value)


            if buy_qty > 0 and sell_qty > 0:
                avg_buy_price = buy_value / buy_qty
                buy_value_for_sold = avg_buy_price * sell_qty
                total_realised_profit_loss += sell_value - buy_value_for_sold

        # ---- PORTFOLIO META ----
        if stocks.exists():
            first_stock = stocks.first()
            portfolio_name = (
                first_stock.portfolio.name
                if first_stock.portfolio
                else "CURRENT PORTFOLIO"
            )
            date_time = first_stock.date_time_field or first_stock.format_date_time()
        else:
            portfolio_name = "CURRENT PORTFOLIO"
            date_time = ""

        html_content = self._generate_html_report(
            stocks,
            total_buy_qty,
            total_buy_value,
            total_sell_qty,
            total_sell_value,
            total_realised_profit_loss,
            portfolio_name,
            date_time,
        )

        return HttpResponse(html_content, content_type="text/html")

        return response

# ... rest of StockTradeViewSet ...
    
    def _generate_html_report(self, stocks, total_buy_qty, total_buy_value, 
                             total_sell_qty, total_sell_value, total_realised_profit_loss,
                             portfolio_name, date_time):
        """Generate HTML report content"""
        
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Stock Portfolio Report</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: Arial, sans-serif;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background-color: white;
            padding: 30px;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
        }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
            border-bottom: 2px solid #333;
            padding-bottom: 20px;
        }}
        .header h1 {{
            font-size: 24px;
            color: #333;
            margin-bottom: 10px;
        }}
        .header .date {{
            font-size: 14px;
            color: #666;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
            font-size: 12px;
        }}
        th {{
            background-color: #4a90e2;
            color: white;
            padding: 12px 8px;
            text-align: center;
            font-weight: bold;
            border: 1px solid #333;
        }}
        td {{
            padding: 10px 8px;
            text-align: right;
            border: 1px solid #ddd;
        }}
        tr:nth-child(even) {{
            background-color: #f9f9f9;
        }}
        tr:hover {{
            background-color: #f0f0f0;
        }}
        .symbol {{
            text-align: left;
            font-weight: bold;
        }}
        .total-row {{
            background-color: #e8f4f8 !important;
            font-weight: bold;
            border-top: 2px solid #333;
        }}
        .total-row td {{
            font-weight: bold;
        }}
        .positive {{
            color: #28a745;
        }}
        .negative {{
            color: #dc3545;
        }}
        @media print {{
            body {{
                background-color: white;
                padding: 0;
            }}
            .container {{
                box-shadow: none;
                padding: 20px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{portfolio_name}</h1>
            <div class="date">{date_time}</div>
        </div>
        <table>
            <thead>
                <tr>
                    <th>SYMBOL</th>
                    <th>TOTAL BUY QTY</th>
                    <th>TOTAL BUY VALUE</th>
                    <th>TOTAL SELL QTY</th>
                    <th>TOTAL SELL VALUE</th>
                    <th>BALANCE QTY</th>
                    <th>ACQUISITION COST</th>
                    <th>% HOLDING</th>
                    <th>LTP</th>
                    <th>CURRENT VALUE</th>
                    <th>REALISED PROFIT / LOSS</th>
                    <th>UN-REALISED PROFIT / LOSS</th>
                    <th>TOTAL PROFIT / LOSS</th>
                    <th>52WK HIGH</th>
                    <th>52WK LOW</th>
                </tr>
            </thead>
            <tbody>"""
        
        # Add rows for each stock
        for stock in stocks:
            # LTP (Last Traded Price) - use sell_price if available, otherwise buy_price
            sell_price = to_decimal(stock.sell_price)
            buy_price = to_decimal(stock.buy_price)
            ltp = sell_price if sell_price > 0 else buy_price

            
            # Calculate realised profit/loss: total_sell_value - (proportion of buy_value for sold shares)
            buy_qty = to_int(stock.total_buy_qty)
            sell_qty = to_int(stock.total_sell_qty)
            buy_value = to_decimal(stock.total_buy_value)
            sell_value = to_decimal(stock.total_sell_value)

            if buy_qty > 0 and sell_qty > 0:
                avg_buy_price = buy_value / buy_qty
                buy_value_for_sold = avg_buy_price * sell_qty
                realised_pl = sell_value - buy_value_for_sold
            else:
                realised_pl = Decimal('0.00')

            
            unrealised_pl = Decimal('0.00')
            total_pl = realised_pl + unrealised_pl
            
            profit_class = "positive" if total_pl >= 0 else "negative"
            profit_sign = "+" if total_pl >= 0 else ""
            
            html += f"""
                <tr>
                    <td class="symbol">{stock.symbol}</td>
                    <td>{to_int(stock.total_buy_qty):,}</td>
                    <td>{format_number(stock.total_buy_value)}</td>
                    <td>{to_int(stock.total_sell_qty):,}</td>
                    <td>{format_number(stock.total_sell_value)}</td>
                    <td>{to_int(stock.balance_qty):,}</td>
                    <td>{format_number(stock.acquisition_cost)}</td>
                    <td>{format_number(stock.percent_holding)}</td>
                    <td>{format_number(ltp)}</td>
                    <td>{format_number(stock.current_value)}</td>
                    <td class="{profit_class}">{profit_sign}{format_number(realised_pl)}</td>
                    <td>{format_number(unrealised_pl)}</td>
                    <td class="{profit_class}">{profit_sign}{format_number(total_pl)}</td>
                    <td>{format_number(stock.wk_52_high)}</td>
                    <td>{format_number(stock.wk_52_low)}</td>
                </tr>"""
        
        # Add total row
        total_unrealised_pl = Decimal('0.00')
        total_profit_loss = total_realised_profit_loss + total_unrealised_pl
        profit_class = "positive" if total_profit_loss >= 0 else "negative"
        profit_sign = "+" if total_profit_loss >= 0 else ""
        
        html += f"""
                <tr class="total-row">
                    <td class="symbol">TOTAL</td>
                    <td>{int(clean_number(stock.total_buy_qty)):,}</td>

                    <td>{format_number(total_buy_value)}</td>
                    <td>{total_sell_qty:,}</td>
                    <td>{format_number(total_sell_value)}</td>
                    <td>0</td>
                    <td>0.00</td>
                    <td>0.00</td>
                    <td>-</td>
                    <td>0.00</td>
                    <td class="{profit_class}">{profit_sign}{format_number(total_realised_profit_loss)}</td>
                    <td>{format_number(total_unrealised_pl)}</td>
                    <td class="{profit_class}">{profit_sign}{format_number(total_profit_loss)}</td>
                    <td>-</td>
                    <td>-</td>
                </tr>
            </tbody>
        </table>
    </div>
</body>
</html>"""
        
        return html


class PortfolioViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing portfolios
    list: Get all portfolios
    create: Create a new portfolio
    retrieve: Get a specific portfolio by ID
    update/partial_update: Update a portfolio
    destroy: Delete a portfolio
    """
    queryset = Portfolio.objects.all().order_by('-created_at')
    serializer_class = PortfolioSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response({'message': 'Portfolios retrieved', 'count': len(serializer.data), 'data': serializer.data}, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response({'message': 'Portfolio created', 'data': serializer.data}, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response({'message': 'Portfolio updated', 'data': serializer.data}, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response({'message': 'Portfolio deleted'}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def by_name(self, request):
        name = request.query_params.get('name', None)
        if not name:
            return Response({'error': 'name parameter is required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            portfolio = Portfolio.objects.get(name__iexact=name)
            serializer = self.get_serializer(portfolio)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Portfolio.DoesNotExist:
            return Response({'error': f'Portfolio with name {name} not found'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['delete'])
    def delete_by_name(self, request):
        name = request.query_params.get('name', None)
        if not name:
            return Response({'error': 'name parameter is required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            portfolio = Portfolio.objects.get(name__iexact=name)
            portfolio.delete()
            return Response({'message': f'Portfolio {name} deleted'}, status=status.HTTP_200_OK)
        except Portfolio.DoesNotExist:
            return Response({'error': f'Portfolio with name {name} not found'}, status=status.HTTP_404_NOT_FOUND)


def to_int(value):
    if value is None:
        return 0
    if isinstance(value, str):
        return int(value.replace(',', ''))
    return int(value)

def to_decimal(value):
    if value is None:
        return Decimal('0.00')
    if isinstance(value, str):
        return Decimal(value.replace(',', ''))
    return Decimal(value)


from decimal import Decimal, InvalidOperation

def clean_number(value):
    if value in (None, "", "-"):
        return Decimal("0")
    if isinstance(value, (int, float, Decimal)):
        return Decimal(value)
    return Decimal(str(value).replace(",", "").strip())


def format_number(value):
    try:
        return f"{clean_number(value):,.2f}"
    except (InvalidOperation, ValueError):
        return "0.00"

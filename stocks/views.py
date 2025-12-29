from rest_framework import status, viewsets
# from playwright.sync_api import sync_playwright
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.http import HttpResponse
from decimal import Decimal

import stocks
from .models import StockTrade, Portfolio
from .serializers import StockTradeSerializer, PortfolioSerializer
from django.http import HttpResponse
from rest_framework.decorators import action
from decimal import Decimal
import tempfile
import os

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


    # @action(detail=False, methods=["get"])
    # def download_report_image(self, request):
    #     # 1️⃣ Generate SAME HTML
    #     html_content = self.download_report(request).content.decode("utf-8")

    #     # 2️⃣ Render HTML → Image using Playwright
    #     with sync_playwright() as p:
    #         browser = p.chromium.launch()
    #         page = browser.new_page(viewport={"width": 1800, "height": 2000})

    #         page.set_content(html_content, wait_until="networkidle")

    #         image_bytes = page.screenshot(
    #             full_page=True,
    #             type="png"
    #         )

    #         browser.close()

    #     # 3️⃣ Return Image
    #     response = HttpResponse(image_bytes, content_type="image/png")
    #     response["Content-Disposition"] = 'attachment; filename="portfolio_report.png"'
    #     return response

   # ... inside StockTradeViewSet ...

    @action(detail=False, methods=['get'], permission_classes=[])
    def download_report(self, request):
        """Download HTML report of all stock trades"""
        # Get portfolio_id from query parameters
        portfolio_id = request.query_params.get('portfolio_id')
        
        if portfolio_id:
            # Filter stocks by specific portfolio
            try:
                portfolio = Portfolio.objects.get(id=portfolio_id)
                stocks = StockTrade.objects.filter(portfolio=portfolio).order_by('symbol')
                portfolio_name = portfolio.name
                description = portfolio.description or ""
            except Portfolio.DoesNotExist:
                return Response(
                    {'error': f'Portfolio with ID {portfolio_id} not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            # Get all stocks
            stocks = StockTrade.objects.all().order_by('symbol')
            portfolio_name = "ALL PORTFOLIOS"
            description = "Combined report of all portfolios"

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

        # ---- DATE TIME ----
        if stocks.exists():
            first_stock = stocks.first()
            date_time = first_stock.date_time_field or first_stock.format_date_time()
        else:
            date_time = ""

        html_content = self._generate_html_report(
            stocks,
            total_buy_qty,
            total_buy_value,
            total_sell_qty,
            total_sell_value,
            total_realised_profit_loss,
            portfolio_name,
            description,
            date_time,
        )

        return HttpResponse(html_content, content_type="text/html")

        return response

# ... rest of StockTradeViewSet ...
    
    def _generate_html_report(self, stocks, total_buy_qty, total_buy_value, 
                            total_sell_qty, total_sell_value, total_realised_profit_loss,
                            portfolio_name, description, date_time):
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
                background-color: #f5f5f5;
                width: 100%;
                overflow-x: hidden;
            }}
            .container {{
                width: 100%;
                background-color: white;
                padding: 15px;
            }}
            .header {{
                margin-bottom: 20px;
                padding-bottom: 15px;
                
            }}
            .portfolio-title {{
                font-size: 18px;
                color: #331866;
                margin-bottom: 8px;
                font-weight: bold;
                word-break: break-word;
            }}
            .portfolio-description {{
                font-size: 14px;
                color: #666;
                margin-bottom: 5px;
                line-height: 1.4;
                word-break: break-word;
            }}
            .date {{
                font-size: 12px;
                color: #999;
                text-align: right;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                table-layout: fixed;
            }}
            th {{
                background-color: #331866;
                color: white;
                padding: 10px 4px;
                text-align: center;
                font-weight: bold;
                border: 1px solid #444;
                font-size: 10px;
                word-wrap: break-word;
                overflow-wrap: break-word;
                line-height: 1.2;
            }}
            td {{
                padding: 8px 4px;
                text-align: right;
                border: 1px solid #ddd;
                font-size: 10px;
                word-wrap: break-word;
                overflow-wrap: break-word;
                line-height: 1.2;
            }}
            .symbol {{
                text-align: left;
                font-weight: bold;
                color: #0d6efd;
            }}
            tr:nth-child(even) {{
                background-color: #f9f9f9;
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
            .cell-color {{
                text-align: center;
                color: #3B3B3D;
            }}
            .ltp {{
                color: #0d6efd;
            }}
            .unrealised {{
                color: #28a745;
            }}
            
            /* Set specific column widths for better fit */
            th:nth-child(1), td:nth-child(1) {{ /* SYMBOL */
                width: 8%;
                min-width: 60px;
                max-width: 80px;
            }}
            th:nth-child(2), td:nth-child(2) {{ /* TOTAL BUY QTY */
                width: 6%;
                min-width: 50px;
            }}
            th:nth-child(3), td:nth-child(3) {{ /* TOTAL BUY VALUE */
                width: 9%;
                min-width: 60px;
            }}
            th:nth-child(4), td:nth-child(4) {{ /* TOTAL SELL QTY */
                width: 6%;
                min-width: 50px;
            }}
            th:nth-child(5), td:nth-child(5) {{ /* TOTAL SELL VALUE */
                width: 9%;
                min-width: 60px;
            }}
            th:nth-child(6), td:nth-child(6) {{ /* BALANCE QTY */
                width: 6%;
                min-width: 50px;
            }}
            th:nth-child(7), td:nth-child(7) {{ /* ACQUISITION COST */
                width: 6%;
                min-width: 60px;
            }}
            th:nth-child(8), td:nth-child(8) {{ /* % HOLDING */
                width: 5%;
                min-width: 40px;
            }}
            th:nth-child(9), td:nth-child(9) {{ /* LTP */
                width: 5%;
                min-width: 40px;
            }}
            th:nth-child(10), td:nth-child(10) {{ /* CURRENT VALUE */
                width: 7%;
                min-width: 60px;
            }}
            th:nth-child(11), td:nth-child(11) {{ /* REALISED PROFIT/LOSS */
                width: 8%;
                min-width: 70px;
            }}
            th:nth-child(12), td:nth-child(12) {{ /* UN-REALISED PROFIT/LOSS */
                width: 8%;
                min-width: 70px;
            }}
            th:nth-child(13), td:nth-child(13) {{ /* TOTAL PROFIT/LOSS */
                width: 7%;
                min-width: 60px;
            }}
            th:nth-child(14), td:nth-child(14) {{ /* 52WK HIGH */
                width: 6%;
                min-width: 50px;
            }}
            th:nth-child(15), td:nth-child(15) {{ /* 52WK LOW */
                width: 6%;
                min-width: 50px;
            }}
            
            /* Mobile-specific optimizations */
            @media screen and (max-width: 768px) {{
                body {{
                    padding: 5px;
                }}
                .container {{
                    padding: 8px;
                }}
                .portfolio-title {{
                    font-size: 16px;
                }}
                table {{
                    font-size: 9px;
                }}
                th, td {{
                    padding: 6px 2px;
                    font-size: 9px;
                }}
                th {{
                    font-size: 9px;
                    padding: 8px 2px;
                }}
                
                /* Shorter column headers for mobile */
                th:nth-child(11):before {{ content: "R P/L"; }}
                th:nth-child(12):before {{ content: "UR P/L"; }}
                th:nth-child(13):before {{ content: "T P/L"; }}
                th:nth-child(14):before {{ content: "52H"; }}
                th:nth-child(15):before {{ content: "52L"; }}
                
                th:nth-child(11) span,
                th:nth-child(12) span,
                th:nth-child(13) span,
                th:nth-child(14) span,
                th:nth-child(15) span {{
                    display: none;
                }}
            }}
            
            /* Tablet optimizations */
            @media screen and (min-width: 769px) and (max-width: 1024px) {{
                body {{
                    padding: 10px;
                }}
                .container {{
                    padding: 15px;
                }}
                table {{
                    font-size: 10px;
                }}
                th, td {{
                    padding: 8px 3px;
                    font-size: 10px;
                }}
            }}
            
            /* Desktop */
            @media screen and (min-width: 1025px) {{
                body {{
                    padding: 20px;
                }}
                .container {{
                    max-width: 1800px;
                    margin: 0 auto;
                    padding: 25px;
                    box-shadow: 0 0 10px rgba(0,0,0,0.1);
                }}
                table {{
                    font-size: 11px;
                }}
                th, td {{
                    padding: 10px 5px;
                    font-size: 11px;
                }}
                
                /* Show full column headers on desktop */
                th:nth-child(11):before,
                th:nth-child(12):before,
                th:nth-child(13):before,
                th:nth-child(14):before,
                th:nth-child(15):before {{
                    display: none;
                }}
                th:nth-child(11) span,
                th:nth-child(12) span,
                th:nth-child(13) span,
                th:nth-child(14) span,
                th:nth-child(15) span {{
                    display: inline;
                }}
            }}
            
            /* Very small phones */
            @media screen and (max-width: 480px) {{
                body {{
                    padding: 2px;
                }}
                .container {{
                    padding: 5px;
                }}
                table {{
                    font-size: 8px;
                }}
                th, td {{
                    padding: 4px 1px;
                    font-size: 8px;
                }}
                th {{
                    padding: 6px 1px;
                }}
                
                /* Even shorter headers for very small screens */
                th:nth-child(3):before {{ content: "B VAL"; }}
                th:nth-child(5):before {{ content: "S VAL"; }}
                th:nth-child(7):before {{ content: "ACQ"; }}
                th:nth-child(10):before {{ content: "C VAL"; }}
                
                th:nth-child(3) span,
                th:nth-child(5) span,
                th:nth-child(7) span,
                th:nth-child(10) span {{
                    display: none;
                }}
            }}
            
            /* Print styles */
            @media print {{
                body {{
                    background-color: white;
                    padding: 0;
                    margin: 0;
                }}
                .container {{
                    box-shadow: none;
                    padding: 10px;
                    width: 100%;
                }}
                table {{
                    width: 100%;
                    font-size: 8pt;
                }}
                th, td {{
                    padding: 4px 2px;
                    border: 1px solid #000;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div>CURRENT PORTFOLIO: {portfolio_name.upper()}</div>
                <div style="text-align:right">{description}</div>
            </div>
            
            <table>
                <thead>
                    <tr>
                        <th>SYMBOL</th>
                        <th>TOTAL BUY QTY</th>
                        <th><span>TOTAL BUY VALUE</span></th>
                        <th>TOTAL SELL QTY</th>
                        <th><span>TOTAL SELL VALUE</span></th>
                        <th>BALANCE QTY</th>
                        <th><span>ACQUISITION COST</span></th>
                        <th>% HOLDING</th>
                        <th>LTP</th>
                        <th><span>CURRENT VALUE</span></th>
                        <th><span>REALISED PROFIT/ LOSS</span></th>
                        <th><span>UN-REALISED PROFIT/ LOSS</span></th>
                        <th><span>TOTAL PROFIT/ LOSS</span></th>
                        <th><span>52WK HIGH</span></th>
                        <th><span>52WK LOW</span></th>
                    </tr>
                </thead>
                <tbody>"""
        
        # Add rows for each stock
        for stock in stocks:
            # Calculate realised profit/loss
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
                        <td class="cell-color">{to_int(stock.total_buy_qty):,}</td>
                        <td class="cell-color">{format_number(stock.total_buy_value)}</td>
                        <td class="cell-color">{to_int(stock.total_sell_qty):,}</td>
                        <td class="cell-color">{format_number(stock.total_sell_value)}</td>
                        <td class="cell-color">{to_int(stock.balance_qty):,}</td>
                        <td class="cell-color">{format_number(stock.acquisition_cost)}</td>
                        <td class="cell-color">{format_number(stock.percent_holding)}</td>
                        <td style="text-align:center" class="ltp">{format_number(stock.ltp)}</td>
                        <td class="cell-color">{format_number(stock.current_value)}</td>
                        <td class="cell-color">{profit_sign}{format_number(realised_pl)}</td>
                        <td class="cell-color unrealised">{format_number(unrealised_pl)}</td>
                        <td style="text-align:center" class="{profit_class}">{profit_sign}{format_number(total_pl)}</td>
                        <td class="cell-color">{format_number(stock.wk_52_high)}</td>
                        <td class="cell-color">{format_number(stock.wk_52_low)}</td>
                    </tr>"""
        
        # Add total row
        total_unrealised_pl = Decimal('0.00')
        total_profit_loss = total_realised_profit_loss + total_unrealised_pl
        profit_class = "positive" if total_profit_loss >= 0 else "negative"
        profit_sign = "+" if total_profit_loss >= 0 else ""
        
        # Calculate total balance qty
        total_balance_qty = total_buy_qty - total_sell_qty
        
        html += f"""
                    <tr class="total-row">
                        <td class="symbol">TOTAL</td>
                        <td style="text-align: center">{total_buy_qty:,}</td>
                        <td style="text-align: center">{format_number(total_buy_value)}</td>
                        <td style="text-align: center">{total_sell_qty:,}</td>
                        <td style="text-align: center">{format_number(total_sell_value)}</td>
                        <td style="text-align: center">0</td>
                        <td style="text-align: center">0.00</td>
                        <td style="text-align: center">0.00</td>
                        <td></td>
                        <td style="text-align: center">0.00</td>
                        <td style="text-align: center" class="{profit_class}">{profit_sign}{format_number(total_realised_profit_loss)}</td>
                        <td style="text-align: center">0.00</td>
                        <td style="text-align: center" class="{profit_class}">{profit_sign}{format_number(total_profit_loss)}</td>
                        <td></td>
                        <td></td>
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


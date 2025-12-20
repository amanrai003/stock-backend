from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import StockTradeViewSet, PortfolioViewSet

router = DefaultRouter()
router.register(r'trades', StockTradeViewSet, basename='stocktrade')
router.register(r'portfolios', PortfolioViewSet, basename='portfolio')

urlpatterns = [
    path('', include(router.urls)),
]


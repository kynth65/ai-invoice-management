from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'expense-summaries', views.ExpenseSummaryViewSet)
router.register(r'budget-alerts', views.BudgetAlertViewSet)
router.register(r'spending-trends', views.SpendingTrendViewSet)
router.register(r'dashboard-metrics', views.UserDashboardMetricsViewSet)
router.register(r'analytics', views.AnalyticsViewSet, basename='analytics')

urlpatterns = [
    path('', include(router.urls)),
]
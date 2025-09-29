from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'tasks', views.AIProcessingTaskViewSet, basename='aiprocessingtask')
router.register(r'processing', views.AIProcessingTaskListViewSet, basename='ai-processing')

urlpatterns = [
    path('', include(router.urls)),
]
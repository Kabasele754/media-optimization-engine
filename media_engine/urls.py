from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import MediaViewSet
from . import system_views

router = DefaultRouter()
router.register('images', MediaViewSet, basename='media-image')

urlpatterns = [
    path('system/capabilities/', system_views.capabilities, name='media-engine-capabilities'),
    path('system/health/', system_views.health, name='media-engine-health'),
    path('system/version/', system_views.version, name='media-engine-version'),
    path('system/openapi.yaml', system_views.openapi_yaml, name='media-engine-openapi'),
] + router.urls

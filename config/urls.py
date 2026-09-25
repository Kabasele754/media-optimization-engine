from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static
from media_engine.metrics import metrics_view
from media_engine.system_views import well_known

urlpatterns = [
    path('.well-known/media-optimization-engine.json', well_known, name='media-engine-well-known'),
    path('admin/', admin.site.urls),
    path('api/v1/', include('media_engine.urls')),
    path('internal/metrics', metrics_view, name='metrics'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

from django.http import HttpResponse

try:
    from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
except ImportError:
    class _Metric:
        def labels(self, *args, **kwargs):
            return self
        def inc(self, *args, **kwargs):
            return None
        def set(self, *args, **kwargs):
            return None
        def time(self):
            class _Timer:
                def __enter__(self): return self
                def __exit__(self, *args): return False
            return _Timer()
    def Counter(*args, **kwargs): return _Metric()
    def Histogram(*args, **kwargs): return _Metric()
    def Gauge(*args, **kwargs): return _Metric()
    def generate_latest(): return b''
    CONTENT_TYPE_LATEST = 'text/plain; charset=utf-8'

IMAGES_INGESTED = Counter('media_engine_images_ingested_total', 'Number of media assets ingested')
VARIANTS_GENERATED = Counter('media_engine_variants_generated_total', 'Generated variants', ['format', 'profile'])
VARIANT_FAILURES = Counter('media_engine_variant_failures_total', 'Failed variant generations', ['format', 'profile'])
GENERATION_SECONDS = Histogram('media_engine_generation_seconds', 'Variant generation duration', ['format', 'profile'])
ORIGINAL_BYTES = Counter('media_engine_original_bytes_total', 'Bytes ingested as originals')
DERIVATIVE_BYTES = Counter('media_engine_derivative_bytes_total', 'Bytes written as derivatives', ['format'])
READY_ASSETS = Gauge('media_engine_ready_assets', 'Number of ready media assets')


def metrics_view(request):
    return HttpResponse(generate_latest(), content_type=CONTENT_TYPE_LATEST)

from .base import *
import os

DEBUG = False

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': os.getenv('REDIS_URL', 'redis://redis:6379/0'),
        'TIMEOUT': 300,
        'OPTIONS': {
            'socket_connect_timeout': 1,
            'socket_timeout': 1,
        },
    }
}

CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/1')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://redis:6379/2')

if os.getenv('USE_S3', '0') == '1':
    STORAGES = {
        'default': {
            'BACKEND': 'storages.backends.s3.S3Storage',
            'OPTIONS': {
                'access_key': os.getenv('AWS_ACCESS_KEY_ID'),
                'secret_key': os.getenv('AWS_SECRET_ACCESS_KEY'),
                'bucket_name': os.getenv('AWS_STORAGE_BUCKET_NAME'),
                'endpoint_url': os.getenv('AWS_S3_ENDPOINT_URL') or None,
                'region_name': os.getenv('AWS_S3_REGION_NAME') or None,
                'custom_domain': os.getenv('AWS_S3_CUSTOM_DOMAIN') or None,
                'default_acl': None,
                'querystring_auth': False,
                'file_overwrite': False,
            },
        },
        'staticfiles': {
            'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
        },
    }

MEDIA_ENGINE_REQUIRE_API_KEY = os.getenv('MEDIA_ENGINE_REQUIRE_API_KEY', '1') == '1'

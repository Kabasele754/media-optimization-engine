from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parents[2]

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'dev-only-secret')
DEBUG = False
ALLOWED_HOSTS = [x.strip() for x in os.getenv('DJANGO_ALLOWED_HOSTS', '*').split(',') if x.strip()]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'media_engine',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ]
        },
    }
]
WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('POSTGRES_DB', 'media_engine'),
        'USER': os.getenv('POSTGRES_USER', 'media_engine'),
        'PASSWORD': os.getenv('POSTGRES_PASSWORD', 'media_engine'),
        'HOST': os.getenv('POSTGRES_HOST', '127.0.0.1'),
        'PORT': os.getenv('POSTGRES_PORT', '5432'),
        'CONN_MAX_AGE': 60,
    }
}

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_SAVE_EVERY_REQUEST = False

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.AllowAny'],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.FormParser',
        'rest_framework.parsers.MultiPartParser',
    ],
}


MEDIA_ENGINE_VERSION = os.getenv('MEDIA_ENGINE_VERSION', '1.4.0')
MEDIA_ENGINE_NODE_ID = os.getenv('MEDIA_ENGINE_NODE_ID', 'local-node')
MEDIA_ENGINE_PROJECT_SLUG = os.getenv('MEDIA_ENGINE_PROJECT_SLUG', 'local-project')
MEDIA_ENGINE_TENANT_SLUG = os.getenv('MEDIA_ENGINE_TENANT_SLUG', 'default')
MEDIA_ENGINE_DEPLOYMENT_ID = os.getenv('MEDIA_ENGINE_DEPLOYMENT_ID', 'standalone')
MEDIA_ENGINE_API_KEYS = os.getenv('MEDIA_ENGINE_API_KEYS', '')
MEDIA_ENGINE_REQUIRE_API_KEY = os.getenv('MEDIA_ENGINE_REQUIRE_API_KEY', '0') == '1'
MEDIA_ENGINE_CONFIG_DIR = os.getenv('MEDIA_ENGINE_CONFIG_DIR', str(BASE_DIR / 'runtime-config'))
MEDIA_ENGINE_CONTROL_PLANE_ENABLED = os.getenv('MEDIA_ENGINE_CONTROL_PLANE_ENABLED', '0') == '1'
MEDIA_ENGINE_CONTROL_PLANE_URL = os.getenv('MEDIA_ENGINE_CONTROL_PLANE_URL', '').rstrip('/')
MEDIA_ENGINE_CONTROL_PLANE_TOKEN = os.getenv('MEDIA_ENGINE_CONTROL_PLANE_TOKEN', '')
MEDIA_ENGINE_CONTROL_PLANE_TIMEOUT_SECONDS = float(os.getenv('MEDIA_ENGINE_CONTROL_PLANE_TIMEOUT_SECONDS', '3'))
MEDIA_ENGINE_CONTROL_PLANE_CIRCUIT_SECONDS = int(os.getenv('MEDIA_ENGINE_CONTROL_PLANE_CIRCUIT_SECONDS', '300'))
MEDIA_ENGINE_CONTROL_PLANE_SYNC_SECONDS = int(os.getenv('MEDIA_ENGINE_CONTROL_PLANE_SYNC_SECONDS', '300'))
MEDIA_ENGINE_WORKER_HEARTBEAT_MAX_AGE = int(os.getenv('MEDIA_ENGINE_WORKER_HEARTBEAT_MAX_AGE', '120'))

MEDIA_ENGINE_PIPELINE_VERSION = int(os.getenv('MEDIA_ENGINE_PIPELINE_VERSION', '1'))
MEDIA_ENGINE_MAX_UPLOAD_BYTES = int(os.getenv('MEDIA_ENGINE_MAX_UPLOAD_BYTES', str(25 * 1024 * 1024)))
MEDIA_ENGINE_MAX_PIXELS = int(os.getenv('MEDIA_ENGINE_MAX_PIXELS', '50000000'))
MEDIA_ENGINE_DEDUPLICATE = os.getenv('MEDIA_ENGINE_DEDUPLICATE', '1') == '1'
MEDIA_ENGINE_PUBLIC_ORIGINAL_FALLBACK = os.getenv('MEDIA_ENGINE_PUBLIC_ORIGINAL_FALLBACK', '0') == '1'
MEDIA_ENGINE_CDN_BASE_URL = os.getenv('MEDIA_ENGINE_CDN_BASE_URL', '').rstrip('/')
MEDIA_ENGINE_AUTO_FOCAL = os.getenv('MEDIA_ENGINE_AUTO_FOCAL', '0') == '1'

MEDIA_ENGINE_PROFILES = {
    'default': {
        'widths': [320, 480, 640, 960, 1280, 1600],
        'formats': ['avif', 'webp'],
        'fallback_format': 'jpeg',
        'quality': {'avif': 52, 'webp': 72, 'jpeg': 78},
        'target_bytes': {320: 50000, 480: 70000, 640: 100000, 960: 150000, 1280: 220000, 1600: 300000},
        'fit': 'contain',
    },
    'avatar': {
        'widths': [96, 192, 384],
        'formats': ['avif', 'webp'],
        'fallback_format': 'jpeg',
        'quality': {'avif': 48, 'webp': 68, 'jpeg': 74},
        'target_bytes': {96: 20000, 192: 35000, 384: 60000},
        'fit': 'cover',
        'aspect_ratio': [1, 1],
    },
    'hero': {
        'widths': [640, 960, 1280, 1600, 1920],
        'formats': ['avif', 'webp'],
        'fallback_format': 'jpeg',
        'quality': {'avif': 58, 'webp': 78, 'jpeg': 82},
        'target_bytes': {640: 120000, 960: 170000, 1280: 220000, 1600: 300000, 1920: 360000},
        'fit': 'cover',
        'aspect_ratio': [16, 9],
    },
    'card': {
        'widths': [320, 480, 640, 768],
        'formats': ['avif', 'webp'],
        'fallback_format': 'jpeg',
        'quality': {'avif': 50, 'webp': 70, 'jpeg': 76},
        'target_bytes': {320: 40000, 480: 60000, 640: 90000, 768: 110000},
        'fit': 'cover',
        'aspect_ratio': [4, 3],
    },
}

CELERY_TASK_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULE = {
    'media-engine-cleanup-orphans': {
        'task': 'media_engine.tasks.cleanup_orphan_derivatives_task',
        'schedule': 86400.0,
    },
    'media-engine-worker-heartbeat': {
        'task': 'media_engine.tasks.worker_heartbeat_task',
        'schedule': 30.0,
    },
    'media-engine-control-plane-sync': {
        'task': 'media_engine.tasks.sync_control_plane_config_task',
        'schedule': float(MEDIA_ENGINE_CONTROL_PLANE_SYNC_SECONDS),
    },
}

# Panorama 360 multiresolution defaults (MOE 1.3)
MEDIA_ENGINE_PANORAMA_TILE_SIZE = int(os.getenv('MEDIA_ENGINE_PANORAMA_TILE_SIZE', '512'))
MEDIA_ENGINE_PANORAMA_MIN_LEVEL_WIDTH = int(os.getenv('MEDIA_ENGINE_PANORAMA_MIN_LEVEL_WIDTH', '1024'))
MEDIA_ENGINE_PANORAMA_FORMATS = tuple(x.strip() for x in os.getenv('MEDIA_ENGINE_PANORAMA_FORMATS', 'avif,webp').split(',') if x.strip())
MEDIA_ENGINE_PANORAMA_QUALITY = {'avif': 52, 'webp': 72}
MEDIA_ENGINE_PANORAMA_GENERATE_CUBEMAP = os.getenv('MEDIA_ENGINE_PANORAMA_GENERATE_CUBEMAP', '0').lower() in {'1', 'true', 'yes'}
MEDIA_ENGINE_PANORAMA_CUBEMAP_FACE_SIZE = int(os.getenv('MEDIA_ENGINE_PANORAMA_CUBEMAP_FACE_SIZE', '2048'))
MEDIA_ENGINE_TASK_MODE = os.getenv('MEDIA_ENGINE_TASK_MODE', 'auto')

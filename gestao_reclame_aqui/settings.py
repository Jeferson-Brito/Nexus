"""
Django settings for gestao_reclame_aqui project.
"""

import os
import sys
from pathlib import Path
import dj_database_url

# ==============================
# BASE DIR
# ==============================
BASE_DIR = Path(__file__).resolve().parent.parent

# ==============================
# ENV
# ==============================
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

def get_env(key, default=None):
    return os.environ.get(key, default)

# ==============================
# SECURITY
# ==============================
SECRET_KEY = get_env("SECRET_KEY", "django-insecure-change-me")

DEBUG = get_env("DEBUG", "False").lower() == "true"

ALLOWED_HOSTS = get_env("ALLOWED_HOSTS", "cshub-deploy.onrender.com,localhost,127.0.0.1,.onrender.com").split(",")

CSRF_TRUSTED_ORIGINS = [
    "https://cshub-deploy.onrender.com",
    "https://cshub-l8jg.onrender.com",
    "https://*.onrender.com",
]


# ==============================
# APPLICATIONS
# ==============================
INSTALLED_APPS = [
    # "daphne",  # Removed
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "storages",

    # "channels",  # Removed
    "crispy_forms",
    "crispy_bootstrap5",
    "django_filters",
    "import_export",
    "django.contrib.humanize",

    # apps locais
    "core",
]

# ==============================
# MIDDLEWARE
# ==============================
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.middleware.gzip.GZipMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "core.middleware_ponto.TabletRedirectMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "gestao_reclame_aqui.urls"

# ==============================
# TEMPLATES
# ==============================
# Em produção, usar cached loader para não reler templates do disco a cada request
_template_loaders = [
    "django.template.loaders.filesystem.Loader",
    "django.template.loaders.app_directories.Loader",
]

if not DEBUG:
    _template_loaders = [
        ("django.template.loaders.cached.Loader", _template_loaders),
    ]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": False,  # Must be False when using loaders
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.context_processors.departments",
            ],
            "loaders": _template_loaders,
        },
    },
]

WSGI_APPLICATION = "gestao_reclame_aqui.wsgi.application"

# ==============================
# DATABASE (POSTGRESQL - Render & Supabase Config)
# ==============================
DATABASES = {
    "default": {
        "ENGINE": "django_cockroachdb",
        "NAME": get_env("DB_NAME", "defaultdb"),
        "USER": get_env("DB_USER", "jeferson"),
        "PASSWORD": get_env("DB_PASSWORD", ""),
        "HOST": get_env("DB_HOST", "ageing-phantom-12866.jxf.gcp-southamerica-east1.cockroachlabs.cloud"),
        "PORT": get_env("DB_PORT", "26257"),
        "CONN_MAX_AGE": 300,  # 5 minutos — reduz overhead de conexão com CockroachDB
        "OPTIONS": {
            "sslmode": "require",
        },
    }
}


print("✓ Banco PostgreSQL configurado", file=sys.stderr)

# ==============================
# AUTH / PASSWORDS
# ==============================
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 6},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

AUTH_USER_MODEL = "core.User"

LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/login/"

# ==============================
# INTERNATIONALIZATION
# ==============================
LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True
USE_THOUSAND_SEPARATOR = True

# ==============================
# STATIC FILES
# ==============================
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

# ==============================
# MEDIA FILES
# ==============================
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Supabase Storage (S3 Compatible)
AWS_ACCESS_KEY_ID = get_env("AWS_ACCESS_KEY_ID")

if AWS_ACCESS_KEY_ID:
    AWS_SECRET_ACCESS_KEY = get_env("AWS_SECRET_ACCESS_KEY")
    AWS_STORAGE_BUCKET_NAME = get_env("AWS_STORAGE_BUCKET_NAME")
    AWS_S3_ENDPOINT_URL = get_env("AWS_S3_ENDPOINT_URL")
    AWS_S3_REGION_NAME = get_env("AWS_S3_REGION_NAME", "sa-east-1")

    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
            "OPTIONS": {
                "access_key": AWS_ACCESS_KEY_ID,
                "secret_key": AWS_SECRET_ACCESS_KEY,
                "bucket_name": AWS_STORAGE_BUCKET_NAME,
                "endpoint_url": AWS_S3_ENDPOINT_URL,
                "region_name": AWS_S3_REGION_NAME,
                "querystring_auth": False,
                "file_overwrite": False,
                "addressing_style": "path",
                "custom_domain": f"{AWS_S3_ENDPOINT_URL.replace('https://', '').split('.')[0]}.supabase.co/storage/v1/object/public/{AWS_STORAGE_BUCKET_NAME}",
                "object_parameters": {
                    "CacheControl": "max-age=86400",
                },
            },
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        },
    }
else:
    # Local Storage
    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        },
    }

# ==============================
# DEFAULT PK
# ==============================
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ==============================
# CRISPY FORMS
# ==============================
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# ==============================
# SECURITY HEADERS
# ==============================
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False  # MUST be False to allow JavaScript to read CSRF token

# ==============================
# SESSION
# ==============================
SESSION_COOKIE_AGE = 86400  # 24h
SESSION_SAVE_EVERY_REQUEST = False
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# ==============================
# UPLOAD LIMITS
# ==============================
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
DATA_UPLOAD_MAX_NUMBER_FIELDS = 1000

# ==============================
# EMAIL (DEV)
# ==============================
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# ==============================
# LOGGING
# ==============================
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
}
# ==============================
# CHANNELS (WEBSOCKETS) - REMOVED
# ==============================
# ASGI_APPLICATION = "gestao_reclame_aqui.asgi.application"

# CHANNEL_LAYERS = {
#     "default": {
#         "BACKEND": "channels.layers.InMemoryChannelLayer"
#     }
# }

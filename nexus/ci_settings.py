"""
Settings para CI (GitHub Actions) e testes locais.

Usa SQLite em memória — sem precisar de CockroachDB/Supabase.
Rodar com:
    python manage.py test core.tests --settings=nexus.ci_settings -v 2
"""
from .settings import *  # Herda tudo do settings principal

# Banco de dados em memória (SQLite) — sem credenciais externas
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Cache em memória simples
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

# Storage local (sem S3)
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

# Templates sem cache (para facilitar debug)
TEMPLATES[0]["OPTIONS"]["loaders"] = [
    "django.template.loaders.filesystem.Loader",
    "django.template.loaders.app_directories.Loader",
]

# Desabilita validações de senha para testes
AUTH_PASSWORD_VALIDATORS = []

# Acelera hash de senha em testes
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Silencia logs durante testes
LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "handlers": {"null": {"class": "logging.NullHandler"}},
    "root": {"handlers": ["null"]},
}

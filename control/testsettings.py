from control.settings import *  # flake8: noqa

JEMBI_BASE_URL = "http://test/v2"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

TEMPLATE_DEBUG = True
CELERY_ALWAYS_EAGER = True
BROKER_BACKEND = 'memory'
CELERY_RESULT_BACKEND = 'djcelery.backends.database:DatabaseBackend'
RAVEN_CONFIG = {'dsn': None}

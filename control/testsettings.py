from control.settings import *  # flake8: noqa

JEMBI_BASE_URL = "http://test/v2"

TESTING_TIMESTAMP = "20130819144811"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

TEMPLATE_DEBUG = True
CELERY_ALWAYS_EAGER = True
# CELERY_EAGER_PROPAGATES_EXCEPTIONS = True
BROKER_BACKEND = 'memory'
CELERY_RESULT_BACKEND = 'djcelery.backends.database:DatabaseBackend'
RAVEN_CONFIG = {'dsn': None}

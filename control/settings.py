# Django settings for control project.

import os
import djcelery


djcelery.setup_loader()

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))


def abspath(*args):
    """convert relative paths to absolute paths relative to PROJECT_ROOT"""
    return os.path.join(PROJECT_ROOT, *args)

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'control',
        'USER': 'postgres',
        'PASSWORD': 'postgres',
        'HOST': '127.0.0.1',
        'PORT': '5432',
    }
}

# Hosts/domain names that are valid for this site; required if DEBUG is False
# See https://docs.djangoproject.com/en/1.5/ref/settings/#allowed-hosts
ALLOWED_HOSTS = ['*']

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
TIME_ZONE = 'UTC'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/var/www/example.com/media/"
MEDIA_ROOT = abspath('media')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://example.com/media/", "http://media.example.com/"
MEDIA_URL = '/media/'

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/var/www/example.com/static/"
STATIC_ROOT = abspath('static')

# URL prefix for static files.
# Example: "http://example.com/static/", "http://static.example.com/"
STATIC_URL = '/static/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    # 'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Make this unique, and don't share it with anybody.
# Leaving this intentionally blank because you have to generate one yourself.
SECRET_KEY = 'please-change-me'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
    # 'django.template.loaders.eggs.Loader',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    "django.contrib.auth.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    "django.core.context_processors.static",
    "django.core.context_processors.tz",
    "django.contrib.messages.context_processors.messages",
    "django.core.context_processors.request"

)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    # Uncomment the next line for simple clickjacking protection:
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'control.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'control.wsgi.application'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or
    # "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    abspath('templates'),
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Uncomment the next line to enable the admin:
    'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
    'south',
    'gunicorn',
    'django_nose',
    'raven.contrib.django.raven_compat',
    'djcelery',
    'djcelery_email',
    'tastypie',
    'bootstrapform',
    'rest_framework',
    'rest_framework.authtoken',
    # Custom apps
    'django_filters',
    'control',
    'subscription',
    'registration',
    'subsend',
    'servicerating',
    'snappybouncer',
    'controlinterface',
    'nursereg',
)

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}

# Celery configuration options
CELERY_RESULT_BACKEND = "database"
CELERYBEAT_SCHEDULER = 'djcelery.schedulers.DatabaseScheduler'

# Uncomment if you're running in DEBUG mode and you want to skip the broker
# and execute tasks immediate instead of deferring them to the queue / workers.
CELERY_ALWAYS_EAGER = DEBUG

# Tell Celery where to find the tasks
CELERY_IMPORTS = (
    'subsend.tasks',
    'subscription.tasks',
    'snappybouncer.tasks',
    'registration.tasks',
    'nursereg.tasks',
)

# Enabling priority routing for snappy bouncer tasks to allow those to
# go through as normal regardless of the size of the default queue
# http://docs.celeryproject.org
#    /en/latest/userguide/routing.html#routing-automatic
# This alleviates the problem of these being backlogged if a large outbound
# send is happening.
CELERY_CREATE_MISSING_QUEUES = True
CELERY_ROUTES = {
    'celery.backend_cleanup': {
        'queue': 'mediumpriority',
    },
    'snappybouncer.tasks.send_helpdesk_response': {
        'queue': 'priority',
    },
    'snappybouncer.tasks.send_helpdesk_response_jembi': {
        'queue': 'priority',
    },
    'snappybouncer.tasks.create_snappy_ticket': {
        'queue': 'priority',
    },
    'snappybouncer.tasks.update_snappy_ticket_with_extras': {
        'queue': 'priority',
    },
    'snappybouncer.tasks.backfill_ticket': {
        'queue': 'lowpriority',
    },
    'snappybouncer.tasks.backfill_ticket_faccode': {
        'queue': 'lowpriority',
    },
    'subscription.tasks.fire_metrics_active_subscriptions': {
        'queue': 'priority',
    },
    'subscription.tasks.fire_metrics_all_time_subscriptions': {
        'queue': 'priority',
    },
    'subscription.tasks.fire_metrics_active_langs': {
        'queue': 'priority',
    },
    'subscription.tasks.fire_metrics_all_time_langs': {
        'queue': 'priority',
    },
    'subscription.tasks.vumi_fire_metric': {
        'queue': 'priority',
    },
    'subscription.tasks.ingest_csv': {
        'queue': 'priority',
    },
    'subscription.tasks.ingest_opt_opts_csv': {
        'queue': 'priority',
    },
    'subscription.tasks.ensure_one_subscription': {
        'queue': 'highmemory',
    },
    'servicerating.tasks.send_reminders': {
        'queue': 'mediumpriority',
    },
    'servicerating.tasks.vumi_update_smart_group_query': {
        'queue': 'mediumpriority',
    },
    'servicerating.tasks.vumi_get_smart_group_contacts': {
        'queue': 'mediumpriority',
    },
    'servicerating.tasks.vumi_update_contact_extras': {
        'queue': 'mediumpriority',
    },
    'servicerating.tasks.vumi_send_message': {
        'queue': 'mediumpriority',
    },
    'servicerating.tasks.vumi_fire_metric': {
        'queue': 'mediumpriority',
    },
    'servicerating.tasks.ensure_one_servicerating': {
        'queue': 'highmemory',
    },
    'subsend.tasks.vumi_fire_metric': {
        'queue': 'lowpriority',
    },
    'subsend.tasks.process_message_queue': {
        'queue': 'highmemory',
    },
    'subsend.tasks.send_message': {
        'queue': 'lowpriority',
    },
    'subsend.tasks.processes_message': {
        'queue': 'lowpriority',
    },
    'registration.tasks.jembi_post_json': {
        'queue': 'priority',
    },
    'registration.tasks.jembi_post_xml': {
        'queue': 'priority',
    },
    'registration.tasks.update_create_vumi_contact': {
        'queue': 'priority',
    },
    'registration.tasks.vumi_fire_metric': {
        'queue': 'priority',
    },
    'nursereg.tasks.jembi_post_json': {
        'queue': 'priority',
    },
    'nursereg.tasks.update_create_vumi_contact': {
        'queue': 'priority',
    },
    'nursereg.tasks.vumi_fire_metric': {
        'queue': 'priority',
    },
}


# Defer email sending to Celery, except if we're in debug mode,
# then just print the emails to stdout for debugging.
EMAIL_BACKEND = 'djcelery_email.backends.CeleryEmailBackend'
if DEBUG:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Django debug toolbar
DEBUG_TOOLBAR_CONFIG = {
    'ENABLE_STACKTRACES': True,
}

# South configuration variables
TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'
# Do not run the south tests as part of our test suite.
SKIP_SOUTH_TESTS = True
# Do not run the migrations for our tests. We are assuming that our models.py
# are correct for the tests and as such nothing needs to be migrated.
SOUTH_TESTS_MIGRATE = False

# Sentry configuration
RAVEN_CONFIG = {
    # DevOps will supply you with this.
    # 'dsn': 'http://public:secret@example.com/1',
}

# REST Framework conf defaults
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': ('rest_framework.permissions.IsAdminUser',),
    'PAGINATE_BY': 1000,
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.BasicAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_FILTER_BACKENDS': ('rest_framework.filters.DjangoFilterBackend',)
}

VUMI_GO_BASE_URL = "http://go.vumi.org/api/v1/go/http_api_nostream"
VUMI_GO_ACCOUNT_KEY = "replaceme"
VUMI_GO_CONVERSATION_KEY = "replaceme"
VUMI_GO_ACCOUNT_TOKEN = "replaceme"
VUMI_GO_METRICS_PREFIX = "prd"
VUMI_GO_API_TOKEN = "replaceme"

SITE_DOMAIN_URL = "https://momconnect.co.za"

SNAPPY_BASE_URL = "https://app.besnappy.com/api/v1"
SNAPPY_API_KEY = "replaceme"
SNAPPY_MAILBOX_ID = 1
SNAPPY_EMAIL = "replaceme@example.org"
SNAPPY_EXTRAS = []
SNAPPY_ACCOUNT_ID = None

BROKER_URL = 'redis://localhost:6379/0'

DASHBOARD_API_KEY = "replaceme"

JEMBI_BASE_URL = "http://npr-staging.jembi.org:5001/ws/rest/v1"
JEMBI_USERNAME = "test"
JEMBI_PASSWORD = "test"

SUBSCRIPTION_RATES = {
    "daily": 1,
    "one_per_week": 2,
    "two_per_week": 3,
    "three_per_week": 4,
    "four_per_week": 5,
    "five_per_week": 6
}

LANG_GROUP_KEYS = {
    "en": "ee47385f0c954fc6b614ec3961dbf30b",
    "af": "672442947cdf4a2aae0f96ccb688df05",
    "zu": "4baf3a89aa0243feb328ca664d1a5e8c",
    "xh": "13140076f49f4e84a752a5d5ab961091",
    "ve": "82370a4df3134352a6d7e6c9ccfed323",
    "ts": "c8b90679389143e78c656c16d0f999c7",
    "tn": "0106c492e4b04b03ae7849300eea0cc4",
    "nso": "969fcdd2358e4c8cb063f4c5035fc8c6",
    "st": "f4738d01b4f74e41b9a6e804fc7eda56",
    "ss": "b1e6bbd5d28b477aabb9cce43de7e9d1",
    "nr": "778479e9ad7c4b00a898b61be6dbcac3"
}

METRIC_ENV = "prd"

try:
    from local_settings import *  # flake8: noqa
except ImportError:
    pass

import os
import random
import json

from django.core.exceptions import ImproperlyConfigured

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# JSON loader for application secrets.
SECRETS_JSON = os.path.join(BASE_DIR, 'secrets.json')
try:
    with open(SECRETS_JSON) as f:
        secrets = json.loads(f.read())

except IOError:
    error_msg = 'Missing secrets.json file in project root'
    raise ImproperlyConfigured(error_msg)


def get_secret(setting, secret_vals=secrets):
    try:
        return secret_vals[setting]
    except KeyError:
        error_msg = 'Set the {} key in {}'.format(setting, SECRETS_JSON)
        raise ImproperlyConfigured(error_msg)


# The Django docs state that the secret key must not be part of version control.
# Whatever base.py contains, override it with something local. There's no need
# to store this permanently in case of a reinstall; it's used for transient data
# only, at most some logged in sessions or password reset tokens may become
# invalidated.
SECRET_FILE = os.path.join(BASE_DIR, 'secret.txt')
try:
    SECRET_KEY = open(SECRET_FILE).read().strip()
except IOError:
    try:
        SECRET_KEY = ''.join([random.SystemRandom().choice('abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)') for i in range(50)])
        secret = open(SECRET_FILE, 'w')
        secret.write(SECRET_KEY)
        secret.close()
    except IOError:
        Exception('Please create a %s file with random characters \
        to generate your secret key!' % SECRET_FILE)

DEBUG = get_secret('DEBUG')
ALLOWED_HOSTS = get_secret('ALLOWED_HOSTS')

ADMINS = (
    ('Software Dev', 'razvan.vasiliu@powervault.co.uk'),
)
# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_admin_listfilter_dropdown',

    # third party
    'django_extensions',
    # installed apps
    'backend.apps.base',
    'silk',
    'django_celery_beat',
]

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
)

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'silk.middleware.SilkyMiddleware',
]

ROOT_URLCONF = 'backend.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'backend', 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'backend', 'static'),
]

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    #    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

WSGI_APPLICATION = 'backend.wsgi.application'

MAX_BYTES = 5 * 1024 ** 2
BACKUP_COUNT = 10

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(levelname)-8s %(asctime)s %(filename)s |%(lineno)4d| %(message)s',
            'datefmt': '%a, %Y-%m-%d %H:%M:%S',
        },
        'simple': {
            'format': '%(message)s'
        },
    },
    'filters': {
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'filters': ['require_debug_true'],
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        },
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler',
            'filters': ['require_debug_false'],
        },
        'base': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'verbose',
            'filename': os.path.join(BASE_DIR, 'logs', 'base.log'),
            'maxBytes': MAX_BYTES,
            'backupCount': BACKUP_COUNT,
        },
        'celery_log': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'verbose',
            'filename': os.path.join(BASE_DIR, 'logs', 'celery.log'),
            'maxBytes': MAX_BYTES,
            'backupCount': BACKUP_COUNT,
        },
        'battery': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'verbose',
            'filename': os.path.join(BASE_DIR, 'logs', 'battery.log'),
            'maxBytes': MAX_BYTES,
            'backupCount': BACKUP_COUNT,
        },
        'inverter': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'verbose',
            'filename': os.path.join(BASE_DIR, 'logs', 'inverter.log'),
            'maxBytes': MAX_BYTES,
            'backupCount': BACKUP_COUNT,
        },
        'inverter_pool': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'verbose',
            'filename': os.path.join(BASE_DIR, 'logs', 'inverter_pool.log'),
            'maxBytes': MAX_BYTES,
            'backupCount': BACKUP_COUNT,
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'propagate': True,
        },
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': False,
        },
        'base': {
            'handlers': ['base'],
            'level': 'INFO',
        },
        'celery_log': {
            'handlers': ['celery_log'],
            'level': 'INFO',
        },
        'battery': {
            'handlers': ['battery'],
            'level': 'INFO',
        },
        'inverter': {
            'handlers': ['inverter'],
            'level': 'INFO',
        },
        'inverter_pool': {
            'handlers': ['inverter_pool'],
            'level': 'INFO',
        },
    }
}

DATABASES = {

    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': get_secret('DB_NAME'),
        'USER': get_secret('DB_USER'),
        'PASSWORD': get_secret('DB_PASS'),
        'HOST': get_secret('DB_HOST')
    },
}

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Europe/Brussels'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.10/howto/static-files/

STATIC_URL = '/static/'
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/login/'
STATIC_ROOT = os.path.join(BASE_DIR, 'backend', 'assets')

# EMAIL_HOST = 'smtp.cegeka.be'
# EMAIL_HOST_USER = 'noreply@cegeka.be'
# SERVER_EMAIL = EMAIL_HOST_USER
#
# enable authentication on silk page
SILKY_AUTHENTICATION = True  # User must login
SILKY_AUTHORISATION = True  # User must have permissions

# celery/rabbitmq settings
CELERY_USER = get_secret('CELERY_USER')
CELERY_PASSWORD = get_secret('CELERY_PASSWORD')
CELERY_HOST = 'localhost'
CELERY_VHOST = 'battery_tester'
SMSBOX_STATUS_CHECK_QUEUE = 'check_sms_box'

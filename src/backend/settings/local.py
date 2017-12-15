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

DATABASES = {

    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': get_secret('DB_NAME'),
        'USER': get_secret('DB_USER'),
        'PASSWORD': get_secret('DB_PASS'),
        'HOST': get_secret('DB_HOST')
    },
}
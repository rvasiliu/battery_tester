from django import template

from django.conf import settings
from django.contrib.staticfiles.templatetags.staticfiles import static

register = template.Library()


@register.simple_tag(name='webpack_static')
def webpack_static(file_path):
    if hasattr(settings, 'WEBPACK_DEV_SERVER'):
        file_name = file_path.split('/')[-1].replace('dist', 'bundle')
        url = settings.WEBPACK_DEV_SERVER['URL']
        return '{url}/{file}'.format(url=url, file=file_name)
    else:
        return static(file_path)

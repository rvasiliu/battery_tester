from __future__ import absolute_import
import os

from celery import Celery

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

from django.conf import settings  # noqa

config = {
    'host': settings.CELERY_HOST,
    'user': settings.CELERY_USER,
    'password': settings.CELERY_PASSWORD,
    'vhost': settings.CELERY_VHOST
}


app = Celery('backend.apps.base',
            broker='pyamqp://{user}:{password}@{host}/{vhost}'.format(**config))

app.config_from_object('django.conf:settings')
# get services from the database. Create a queue for each service.


app.conf.update(task_queues=settings.QUEUES)

# app.conf.update(task_queues={'{}_t'.format(s.priority):{} for s in services})
# app.conf.update(task_queues={'{}_b'.format(s.priority):{} for s in services})
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)


@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))

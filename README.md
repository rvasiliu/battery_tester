# Installation:

### Virtual environment

#### Create virtualenv

```mkvirtualenv battery_tester```

#### Activate virtualenv

```workon battery_tester```

### Installation

#### Install requirements

``` pip install -r requirements/pip```

#### Install rabbitmq

##### Ubuntu

```sudo apt-get install rabbitmq```

##### Mac OS X

```brew install rabbitmq```

##### Windows

# RabbitMQ

https://stackoverflow.com/questions/14699873/how-to-reset-user-for-rabbitmq-management

```rabbitmq command (https://cmatskas.com/getting-started-with-rabbitmq-on-windows/)```

### Configuration

#### Configure rabbitmq

*  enable management plugin ```rabbitmq-plugins.bat enable rabbitmq_management```

* create a new rabbitmq user ```rabbitmqctl add_user <username> <password>``` (get the user from the secrets.json)

* create a new rabbitmq virtual host ```rabbitmqctl add_vhost <vhost>``` (get the CELERY_VHOST from settings.base.py)

* allow the user admin rights ```rabbitmqctl set_permissions -p <vhost> <username> ".*" ".*" ".*"```

### Run

#### Django app

* start the server ```python manage.py runserver 0.0.0.0:8000```

#### Celery commands:

* start workers

```celery -A backend worker --app=backend.celery:app -l info -c 5 --pool=eventlet -Q main_com_0, main_com_1, periodic_com_0, periodic_com_1```

* start the celery beat(scheduler) using the django-celery-beat with django database scheduler

```celery -A backend --app=backend.celery:app beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler```

* Remove tasks from queue

```celery -A backend --app=backend.celery:app purge```

#### Other Django commands:
* db migration commands

  1.```manage.py makemigrations```
 
  2.```manage.py migrate```

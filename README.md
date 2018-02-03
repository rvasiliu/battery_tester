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

```celery -A backend worker --app=backend.celery:app -l info -c 5 --pool=eventlet -Q main_COM8,main_COM9,main_COM13,main_COM14,periodic_COM8,periodic_COM9,periodic_COM13,periodic_COM14```

OR

```celery -A backend worker --app=backend.celery:app -l info -c 5 --pool=eventlet -Ofair -Q main_ttyUSB0,main_ttyACM0,main_ttyUSB1,main_ttyACM1,main_ttyUSB2,main_ttyACM2,main_ttyUSB3,main_ttyACM3,main_ttyUSB4,main_ttyACM4,main_ttyUSB5,main_ttyACM5,main_ttyUSB6,main_ttyACM6,main_ttyUSB7,main_ttyACM7,main_ttyUSB8,main_ttyACM8,main_ttyUSB9,main_ttyACM9,main_ttyUSB10,main_ttyACM10,periodic```

* start the celery beat(scheduler) using the django-celery-beat with django database scheduler

```celery -A backend --app=backend.celery:app beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler```

* Remove tasks from queue

```celery -A backend --app=backend.celery:app purge```

#### Other Django commands:
* db migration commands

  1.```manage.py makemigrations```
 
  2.```manage.py migrate```

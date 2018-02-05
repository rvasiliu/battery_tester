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

* start rabbitmq(mac OS) ```/usr/local/Cellar/rabbitmq/3.7.0/sbin/rabbitmq-server start```

### Run

#### Django app

* start the server ```python manage.py runserver 0.0.0.0:8000```

#### Celery commands:

* start workers
Long running tasks must be distributed each on a thread(main tasks). The other tasks can be executed by another worker. For the rest of the tasks(periodic ones) must avoid greedy workers/threads. Therefore:
  
  * there must be one worker that deals with the main tasks(concurency=no of main tasks, use -Ofair to avoid prefetch). All main tasks can be submitted to one Q)
  
  ```celery -A backend worker --app=backend.celery:app -l info -c 10 -Ofair --pool=eventlet -Q main -n worker_main@%h```
  
  * there must be one worker for the periodic tasks. Once again, -Ofair has to be used to avoid prefetching. Periodic tasks must be processed the moment they are scheduled.
  
  ```celery -A backend worker --app=backend.celery:app -l info -c 10 -Ofair --pool=eventlet -Q periodic -n worker_periodic@%h```

* start the celery beat(scheduler) using the django-celery-beat with django database scheduler

  ```celery -A backend --app=backend.celery:app beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler```

* Remove tasks from queue

  ```celery -A backend --app=backend.celery:app purge```

#### Other Django commands:
* db migration commands

  1.```manage.py makemigrations```
 
  2.```manage.py migrate```

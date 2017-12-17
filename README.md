# Celery start command:

#### Start workers

```celery -A backend worker --app=backend.celery:app -l info -c 5 --pool=eventlet```

#### Start the beat

```celery -A backend --app=backend.celery:app beat -l info```

#### Remove tasks from queue

```celery -A backend --app=backend.celery:app purge```

# Setup RabbitMQ

```rabbitmq command (https://cmatskas.com/getting-started-with-rabbitmq-on-windows/)```
```rabbitmq-plugins.bat enable rabbitmq_management```

```rabbitmqctl add_user <username> <password>```
```rabbitmqctl add_vhost <vhost>```
```rabbitmqctl set_permissions -p <vhost> <username> ".*" ".*" ".*"```

# Django:

```Manage.py runserver ip:port```
```Manage.py makemigrations```
```Manage.py migrate```

# Python:

```Workon```
```Deactivate```
```mkvirtualenv```

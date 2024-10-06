release: python manage.py makemigrations && python manage.py migrate
web: gunicorn doji_lite_api_v2.wsgi --log-file -
worker: celery -A doji_lite_api_v2 worker --loglevel=info

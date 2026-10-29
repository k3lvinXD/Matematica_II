# Loaded automatically by `gunicorn app:app` from the project directory.
workers = 1
worker_class = 'gthread'
threads = 2
timeout = 75
accesslog = '-'
errorlog = '-'

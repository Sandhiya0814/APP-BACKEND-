import os
import django

os.environ['DJANGO_SETTINGS_MODULE'] = 'copd.settings'
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("DELETE FROM django_migrations WHERE app='patients'")
    print("MIGRATIONS CLEARED FOR PATIENTS APP")

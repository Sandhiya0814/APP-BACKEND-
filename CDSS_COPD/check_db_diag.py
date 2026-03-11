import os
import django
import sys

# Add the project directory to sys.path
sys.path.append(r'C:\Users\sandh\Desktop\CDSS COPD\CDSS_COPD')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from api.models import Doctor, Staff, CustomUser
from django.db import connection

def check_db():
    print(f"Database Name: {connection.settings_dict['NAME']}")
    try:
        with connection.cursor() as cursor:
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            print("Tables in database:", [t[0] for t in tables])
            
            doctor_count = Doctor.objects.count()
            staff_count = Staff.objects.count()
            pending_count = CustomUser.objects.filter(is_approved=False).exclude(role='admin').count()
            
            print(f"Doctor count: {doctor_count}")
            print(f"Staff count: {staff_count}")
            print(f"Pending count: {pending_count}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_db()

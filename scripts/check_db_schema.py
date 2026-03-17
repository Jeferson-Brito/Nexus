import os
import django
from django.db import connection

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestao_reclame_aqui.settings')
django.setup()

def check_db():
    with connection.cursor() as cursor:
        # Check if tables exist
        cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"Tables: {tables}")
        
        # Check columns of core_message
        if 'core_analistaescala' in tables:
            cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'core_analistaescala'")
            cols = [row[0] for row in cursor.fetchall()]
            print(f"core_analistaescala columns: {cols}")
        
        # Check migrations
        cursor.execute("SELECT name FROM django_migrations WHERE app='core' ORDER BY id DESC LIMIT 10")
        migrations = [row[0] for row in cursor.fetchall()]
        print(f"Migrations for core: {migrations}")

if __name__ == "__main__":
    check_db()

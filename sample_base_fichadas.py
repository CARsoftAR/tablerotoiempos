
import os
import django
import sys
import datetime

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.db import connections

def sample_base_fichadas():
    table = 'T7_FICHADAS_BASE'
    with connections['sql_server'].cursor() as cursor:
        print(f"\nSampling {table}...")
        try:
            cursor.execute(f"SELECT TOP 10 * FROM {table}")
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
            for r in rows:
                print(dict(zip(columns, r)))
        except Exception as e:
            print(f"  Error: {e}")

if __name__ == "__main__":
    sample_base_fichadas()

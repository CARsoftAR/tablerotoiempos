
import os
import django
import sys

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.db import connections

def sample_data(table):
    with connections['sql_server'].cursor() as cursor:
        print(f"\nSample data for: {table}")
        cursor.execute(f"SELECT TOP 10 * FROM {table} ORDER BY Fecha DESC, Hora DESC")
        columns = [col[0] for col in cursor.description]
        results = cursor.fetchall()
        for row in results:
            print(dict(zip(columns, row)))

if __name__ == "__main__":
    sample_data('T71_Reloj')
    sample_data('T7_SYJ_Reloj')

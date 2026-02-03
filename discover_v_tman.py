import os
import django
import sys

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.db import connections

def check_views():
    views_to_check = [
        'V_TMAN',
        'V_Equalrp_ORDENES_DE_PRODUCCION',
        'V_t5_op',
        'V_T5_OP_TIEMPO'
    ]
    
    with connections['sql_server'].cursor() as cursor:
        for view_name in views_to_check:
            print(f"\n--- Checking {view_name} ---")
            try:
                cursor.execute(f"SELECT TOP 1 * FROM {view_name}")
                columns = [column[0] for column in cursor.description]
                print(f"Columns: {', '.join(columns)}")
                
                # Check for "nivel" or "proyecto"
                matches = [c for c in columns if 'NIVEL' in c.upper() or 'PROYECTO' in c.upper() or 'LEVEL' in c.upper()]
                if matches:
                    print(f"MATCHES FOUND: {matches}")
                
                row = cursor.fetchone()
                if row:
                    print(f"Sample data: {row}")
            except Exception as e:
                print(f"Error checking {view_name}: {e}")

if __name__ == "__main__":
    check_views()

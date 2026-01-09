
import os
import django
from django.conf import settings
import pyodbc

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from dashboard.models import VTMan
from dotenv import load_dotenv

def check_machines_table():
    load_dotenv()
    conn_str = (
        f"DRIVER={{{os.getenv('SQLSERVER_DRIVER')}}};"
        f"SERVER={os.getenv('SQLSERVER_HOST')};"
        f"DATABASE={os.getenv('SQLSERVER_DB_NAME')};"
        f"UID={os.getenv('SQLSERVER_USER')};"
        f"PWD={os.getenv('SQLSERVER_PASSWORD')};"
        "TrustServerCertificate=yes;"
    )
    
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        print("--- COLUMNAS DE TMAN010 ---")
        cursor.execute("SELECT TOP 1 * FROM TMAN010")
        columns = [column[0] for column in cursor.description]
        print(columns)
        
        print("\n--- EJEMPLO DE DATOS ---")
        row = cursor.fetchone()
        if row:
            print(row)
            
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_machines_table()

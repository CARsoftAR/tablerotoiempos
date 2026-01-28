import os
import pyodbc
from dotenv import load_dotenv

def get_sqlserver_connection():
    load_dotenv()
    conn_str = (
        f"DRIVER={{{os.getenv('SQLSERVER_DRIVER')}}};"
        f"SERVER={os.getenv('SQLSERVER_HOST')};"
        f"DATABASE={os.getenv('SQLSERVER_DB_NAME')};"
        f"UID={os.getenv('SQLSERVER_USER')};"
        f"PWD={os.getenv('SQLSERVER_PASSWORD')};"
        "TrustServerCertificate=yes;"
    )
    return pyodbc.connect(conn_str)

def explore():
    try:
        conn = get_sqlserver_connection()
        cursor = conn.cursor()
        
        print("--- LISTADO DE TABLAS ---")
        cursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE'")
        tables = cursor.fetchall()
        for i, table in enumerate(tables):
            print(f"{i+1}. {table[0]}")
            
        # Buscar palabras clave como 'maquina', 'produccion', 'tiempo', 'eficiencia'
        keywords = ['maquina', 'prod', 'tiempo', 'stnd', 'standard', 'calidad', 'oee']
        print("\n--- POSIBLES TABLAS CLAVE ---")
        for table in tables:
            name = table[0].lower()
            if any(key in name for key in keywords):
                print(f"[*] {table[0]}")
        
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    explore()

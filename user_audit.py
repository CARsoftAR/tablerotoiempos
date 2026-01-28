
import os
import django
import datetime
from django.db import connections

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

def check_users():
    today = datetime.date.today().strftime('%Y-%m-%d')
    with connections['sql_server'].cursor() as cursor:
        cursor.execute("""
            SELECT TOP 20 Op_usuario, ORGANISMOD, IDORGANISMO, IDORDEN, Cantidad_producida
            FROM V_TMAN
            WHERE CONVERT(date, FECHA) = %s
        """, [today])
        print("User Data Samples:")
        for row in cursor.fetchall():
            print(f"  User: {row[0]} | OrganismoD: {row[1]} | IDOrg: {row[2]} | Order: {row[3]} | Qty: {row[4]}")

if __name__ == "__main__":
    check_users()

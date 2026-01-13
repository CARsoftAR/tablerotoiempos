
import os
import django
from django.utils import timezone
import datetime as dt

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from dashboard.models import VTMan

def check_all_114_recs():
    # Ignore date and just list ALL records for 114 to see what's going on
    recs = VTMan.objects.using('sql_server').filter(id_concepto="114").order_by('-hora_inicio')[:20]
    
    print("--- Latest 20 records for ID 114 ---")
    for r in recs:
        # Check fecha field too
        print(f"ID:{r.id_concepto} | FechaField:{r.fecha} | Start:{r.hora_inicio} | Art:{r.articulod} | Qty:{r.cantidad_producida}")

if __name__ == "__main__":
    check_all_114_recs()

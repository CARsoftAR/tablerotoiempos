import os
import django
import datetime

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from dashboard.models import VTMan

def inspect_mac23():
    target_date = datetime.date(2026, 1, 8)
    start_utc = datetime.datetime.combine(target_date, datetime.time.min).replace(tzinfo=datetime.timezone.utc)
    end_utc = datetime.datetime.combine(target_date, datetime.time.max).replace(tzinfo=datetime.timezone.utc)
    
    print(f"--- Records for MAC23 on {target_date} ---")
    
    registros = VTMan.objects.filter(
        fecha__range=(start_utc, end_utc), 
        id_maquina='MAC23'
    ).values('id_orden', 'tiempo_cotizado', 'cantidad_producida', 'tiempo_minutos', 'es_proceso')
    
    for r in registros:
        print(r)

if __name__ == '__main__':
    inspect_mac23()

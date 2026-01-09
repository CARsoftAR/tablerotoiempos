import os
import django
from django.utils import timezone
import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from dashboard.models import VTMan

fecha_target = timezone.now().date()
start_utc = datetime.datetime.combine(fecha_target, datetime.time.min).replace(tzinfo=datetime.timezone.utc)
end_utc = datetime.datetime.combine(fecha_target, datetime.time.max).replace(tzinfo=datetime.timezone.utc)

print(f"Checking records for MAC42 (HYUNDAI) between {start_utc} and {end_utc}")

records = VTMan.objects.filter(
    fecha__range=(start_utc, end_utc),
    id_maquina='MAC42'
).order_by('fecha').values(
    'id_maquina', 'fecha', 'id_orden', 'tiempo_minutos', 
    'tiempo_cotizado', 'cantidad_producida', 'es_proceso', 'tiempo_cotizado_individual',
    'hora_inicio', 'hora_fin'
)

total_qty = 0
total_std = 0
total_min = 0

for r in records:
    print(f"REC: {r['fecha']} | Start: {r['hora_inicio']} | End: {r['hora_fin']} | Ord: {r['id_orden']} | Min: {r['tiempo_minutos']} | Qty: {r['cantidad_producida']} | Std: {r['tiempo_cotizado']}")

    total_qty += r['cantidad_producida'] or 0
    total_std += r['tiempo_cotizado'] or 0
    total_min += r['tiempo_minutos'] or 0

print("-" * 30)
print(f"TOTALS: Qty={total_qty} | Std={total_std} | Min={total_min}")

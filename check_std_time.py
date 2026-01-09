import os
import django
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from dashboard.models import VTMan

today = timezone.now().date()
print(f"Checking records for today {today}...")

# Filter for records with some observation or production
# records = VTMan.objects.filter(fecha__date=today).exclude(id_maquina__isnull=True)[:20]
# Better: search for the machines in the image: HYUNDAI ME020, BANCO TRABAJO 1 (MAC06), HAAS
target_machines = ['MAC20', 'MAC06', 'MAC05', 'MAC43', 'MAC04'] # HYUNDAI, BANCO, HAAS

records = VTMan.objects.filter(fecha__date=today, id_maquina__in=target_machines).values(
    'id_maquina', 'observaciones', 'es_proceso', 
    'tiempo_cotizado', 'tiempo_cotizado_individual', 'cantidad_producida', 'tiempo_minutos'
)

print(f"Found {len(records)} records.")

for r in records:
    print(f"MAC: {r['id_maquina']} | OBS: {r['observaciones']} | Proc: {r['es_proceso']}")
    print(f"   Cotizado (DB): {r['tiempo_cotizado']}")
    print(f"   Cotiz. Indiv: {r['tiempo_cotizado_individual']}")
    print(f"   Cant Prod: {r['cantidad_producida']}")
    print(f"   Tiempo Min: {r['tiempo_minutos']}")
    print("-" * 20)

print("Checking ONLINE records specifically (any date)")
online_recs = VTMan.objects.filter(observaciones='ONLINE').values(
    'id_maquina', 'tiempo_cotizado', 'tiempo_cotizado_individual', 'cantidad_producida'
)
for r in online_recs:
    print(f"ONLINE - MAC: {r['id_maquina']}")
    print(f"   Cotizado (DB-Hrs?): {r['tiempo_cotizado']}")
    print(f"   Indiv: {r['tiempo_cotizado_individual']}")
    print(f"   Cant: {r['cantidad_producida']}")
    # Add check for timestamp delta vs tiempo_minutos


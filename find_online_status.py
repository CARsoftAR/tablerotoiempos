import os
import django
from django.utils import timezone
from django.db.models import Q

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from dashboard.models import VTMan, Maquina

fecha_target = timezone.datetime(2026, 1, 7).date()
fecha_inicio = timezone.make_aware(timezone.datetime.combine(fecha_target, timezone.datetime.min.time()))
fecha_fin = timezone.make_aware(timezone.datetime.combine(fecha_target, timezone.datetime.max.time()))

print(f"Searching for 'ONLINE' in range: {fecha_inicio} to {fecha_fin}")

# Search for 'ONLINE' in observations
online_regs = VTMan.objects.filter(
    fecha__range=(fecha_inicio, fecha_fin),
    observaciones__icontains='ONLINE'
)
print(f"Records with 'ONLINE' in observaciones: {online_regs.count()}")
for r in online_regs:
    print(f"FOUND ONLINE: ID={r.id_maquina}, Obs={r.observaciones}")

print("-" * 30)

# Search for the machine that was green in the image: HYUNDAI
# We don't know the exact ID, so let's look for it in Maquina definitions
hyundais = Maquina.objects.filter(descripcion__icontains='HYUNDAI')
print(f"Hyundai machines found: {hyundais.count()}")
for h in hyundais:
    print(f"ID: {h.id_maquina}, Desc: {h.descripcion}")
    
    # Check its records for today
    regs = VTMan.objects.filter(
        fecha__range=(fecha_inicio, fecha_fin),
        id_maquina=h.id_maquina
    )
    print(f"  Records on target date: {regs.count()}")
    for r in regs:
        print(f"    - [{r.id_orden}] Process:{r.es_proceso}, Intr:{r.es_interrupcion}, Obs: '{r.observaciones}'")

print("-" * 30)
# Check unique values in 'observaciones' to see if there's something similar
distinct_obs = VTMan.objects.filter(fecha__range=(fecha_inicio, fecha_fin)).values_list('observaciones', flat=True).distinct()
print("Distinct Observations found:")
for o in distinct_obs:
    if o:
        print(f"'{o}'")

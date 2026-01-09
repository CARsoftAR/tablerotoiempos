import os
import django
from django.db.models import Q

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from dashboard.models import VTMan, Maquina

print("--- MACHINE MAPPING ---")
for m in Maquina.objects.all():
    print(f"{m.id_maquina}: {m.descripcion}")

print("\n--- CHECKING FOR RUNNING JOBS (Null End Time) ---")
running = VTMan.objects.filter(hora_fin__isnull=True)
print(f"Records with valid IDMAQUINA and null hora_fin: {running.count()}")
for r in running[:5]:
    print(f"  ID: {r.id_maquina} (Date: {r.fecha}) Obs: {r.observaciones}")

print("\n--- CHECKING 'ONLINE' STRING IN ANY FIELD ---")
# Check a few text fields
online_any = VTMan.objects.filter(
    Q(observaciones__icontains='ONLINE') | 
    Q(id_concepto__icontains='ONLINE') |
    Q(id_operacion__icontains='ONLINE') |
    Q(formula__icontains='ONLINE') |
    Q(articulo__icontains='ONLINE')
)
print(f"Records with 'ONLINE' in text fields: {online_any.count()}")

print("\n--- HYUNDAI DEEP DIVE ---")
# Identify Hyundai ID from the list above first, but let's guess it's one of the active ones.
# We'll just dump the last 3 records for ALL machines that appeared in the user's image 
# (HAAS, NLX, TSUGAMI, TM1, etc)
target_names = ['HYUNDAI', 'HAAS', 'NLX', 'TSUGAMI', 'TM1', 'VF3']
ids_to_check = []
all_maquinas = Maquina.objects.all()
for m in all_maquinas:
    for t in target_names:
        if t in m.descripcion.upper():
            ids_to_check.append(m.id_maquina)

print(f"Checking IDs: {ids_to_check}")
for mid in ids_to_check:
    last = VTMan.objects.filter(id_maquina=mid).order_by('-fecha', '-hora_fin').first()
    if last:
        print(f"LAST RECORD for {mid}:")
        print(f"  Date: {last.fecha}, End: {last.hora_fin}")
        print(f"  Proceso: {last.es_proceso}, Interrupcion: {last.es_interrupcion}")
        print(f"  Obs: '{last.observaciones}'")
        print(f"  Concepto: '{last.id_concepto}'")
    else:
        print(f"No records for {mid}")

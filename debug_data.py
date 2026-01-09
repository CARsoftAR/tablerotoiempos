import os
import django
from django.utils import timezone
from datetime import timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from dashboard.models import VTMan

fecha_target = timezone.datetime(2026, 1, 7).date()
fecha_inicio = timezone.make_aware(timezone.datetime.combine(fecha_target, timezone.datetime.min.time()))
fecha_fin = timezone.make_aware(timezone.datetime.combine(fecha_target, timezone.datetime.max.time()))

print(f"Checking data for range: {fecha_inicio} to {fecha_fin}")

registros = VTMan.objects.filter(fecha__range=(fecha_inicio, fecha_fin))
print(f"Total records found: {registros.count()}")

if registros.exists():
    print("\nSample records:")
    for reg in registros[:10]:
        print(f"ID: {reg.id_maquina}, Time: {reg.tiempo_minutos}, Cotizado: {reg.tiempo_cotizado},  Cant: {reg.cantidad_producida}, Ops: {reg.observaciones}")

    print("\nAggregates by machine:")
    from django.db.models import Sum
    aggs = registros.values('id_maquina').annotate(
        total_time=Sum('tiempo_minutos'),
        total_cotizado=Sum('tiempo_cotizado'),
        total_cant=Sum('cantidad_producida')
    )
    for a in aggs:
        print(a)
else:
    print("No records found! Checking any records...")
    last_reg = VTMan.objects.last()
    if last_reg:
        print(f"Last available record date: {last_reg.fecha}")
    else:
        print("Table VTMan appears empty.")

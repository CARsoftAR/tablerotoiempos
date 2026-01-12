import os
import django
import datetime
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from dashboard.models import VTMan

# Saturday Jan 10, 2026
target_date = datetime.date(2026, 1, 10)
# Use UTC range as fixed in views.py
start = timezone.make_aware(datetime.datetime.combine(target_date, datetime.time.min), datetime.timezone.utc)
end = timezone.make_aware(datetime.datetime.combine(target_date, datetime.time.max), datetime.timezone.utc)

res = VTMan.objects.filter(fecha__range=(start, end)).values('id_maquina', 'tiempo_minutos', 'tiempo_cotizado', 'cantidad_producida', 'es_proceso', 'es_interrupcion')

print(f"Data for {target_date}:")
if not res.exists():
    print("NO RECORDS FOUND IN UTC RANGE")
else:
    totals = {}
    for r in res:
        mid = r['id_maquina']
        if mid not in totals: totals[mid] = {'prod_min': 0, 'std_hrs': 0}
        if r['es_proceso']:
            totals[mid]['prod_min'] += r['tiempo_minutos'] or 0
        totals[mid]['std_hrs'] += r['tiempo_cotizado'] or 0
    
    grand_prod = 0
    grand_std = 0
    for mid, t in totals.items():
        prod_hrs = t['prod_min'] / 60
        std_hrs = t['std_hrs']
        grand_prod += prod_hrs
        grand_std += std_hrs
        print(f"Machine: {mid} | Prod Hrs: {prod_hrs:.2f} | Std Hrs: {std_hrs:.2f}")
    
    print(f"TOTAL | Prod Hrs: {grand_prod:.2f} (Yellow ERP) | Std Hrs: {grand_std:.2f} (Orange ERP)")

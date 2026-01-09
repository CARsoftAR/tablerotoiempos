import os
import django
from django.db.models import Count

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from dashboard.models import VTMan

print("Running user's query logic: OBS = 'ONLINE'")

# Standard check without date filter
online_all = VTMan.objects.filter(observaciones='ONLINE')
print(f"Total records with OBS='ONLINE' (no date filter): {online_all.count()}")

# Group by Date to see if they are spread out or just today
by_date = online_all.values('fecha').annotate(count=Count('id_orden')).order_by('-fecha')
for d in by_date[:10]:
    print(f"Date: {d['fecha']} - Count: {d['count']}")
    
# Check specific machines from today
from django.utils import timezone
today = timezone.now().date()
print(f"\nChecking today ({today}):")
today_online = VTMan.objects.filter(observaciones='ONLINE', fecha__date=today)
print(f"Count for today: {today_online.count()}")

for r in today_online:
    print(f"  ID: {r.id_maquina} | Obs: '{r.observaciones}' | Date: {r.fecha}")

# Check with whitespace variations
print("\nChecking whitespace/case variations for today:")
today_fuzzy = VTMan.objects.filter(observaciones__icontains='ONLINE', fecha__date=today)
print(f"Fuzzy count for today: {today_fuzzy.count()}")
for r in today_fuzzy:
    print(f"  ID: {r.id_maquina} | Obs: '{r.observaciones}'")

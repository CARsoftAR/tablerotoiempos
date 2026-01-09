import os
import django
from django.utils import timezone
import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from dashboard.models import VTMan

print("--- DEBUG DATE FILTERING ---")
today = timezone.now().date()
print(f"Target Date (timezone.now().date()): {today}")

# 1. Try __date lookup
count_date = VTMan.objects.filter(fecha__date=today).count()
print(f"Filter by fecha__date={today}: {count_date}")

# 2. Try Exact Match (if they are exactly midnight)
# Need to construct a naive or aware datetime depending on settings
start_of_day = datetime.datetime.combine(today, datetime.time.min)
end_of_day = datetime.datetime.combine(today, datetime.time.max)
# Assuming UTC if settings use tz
if timezone.is_aware(timezone.now()):
    start_of_day = timezone.make_aware(start_of_day)
    end_of_day = timezone.make_aware(end_of_day)

count_range = VTMan.objects.filter(fecha__range=(start_of_day, end_of_day)).count()
print(f"Filter by range {start_of_day} to {end_of_day}: {count_range}")

# 3. Try Contains String (inefficient but distinct)
# count_str = VTMan.objects.filter(fecha__contains=str(today)).count() # Might not work on datetime
# print(f"Filter by string contains: {count_str}")

# 4. Check what records actually exist around now
print("Sample dates from DB:")
last_recs = VTMan.objects.all().order_by('-fecha')[:5]
for r in last_recs:
    print(f"  {r.fecha} (Type: {type(r.fecha)})")

# 5. Check 'starts with' for string representation if possible or year/month/day
count_ymd = VTMan.objects.filter(fecha__year=today.year, fecha__month=today.month, fecha__day=today.day).count()
print(f"Filter by Y/M/D parts: {count_ymd}")

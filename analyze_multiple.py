import os
import django
import datetime
from django.db.models import Sum, Q

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from dashboard.models import VTMan
import django.utils.timezone as timezone

def analyze_date_summary(date_str):
    print(f"=== Analysis for {date_str} ===")
    date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
    
    d_start = timezone.make_aware(datetime.datetime.combine(date_obj, datetime.time.min), datetime.timezone.utc)
    d_end = timezone.make_aware(datetime.datetime.combine(date_obj, datetime.time.max), datetime.timezone.utc)
    
    qs = VTMan.objects.filter(fecha__range=(d_start, d_end))
    h_std = qs.aggregate(s=Sum('tiempo_cotizado'))['s'] or 0.0
    h_prod = qs.aggregate(s=Sum('tiempo_minutos'))['s'] or 0.0
    
    perf = (h_std * 60.0 / h_prod * 100) if h_prod > 0 else 0
    
    print(f"  Records: {qs.count()}")
    print(f"  Real Mins: {h_prod:.1f}")
    print(f"  Std Mins: {h_std*60:.1f}")
    print(f"  Chart Perf: {perf:.2f}%")

if __name__ == "__main__":
    analyze_date_summary('2026-02-06') # Friday
    analyze_date_summary('2026-02-07') # Saturday
    analyze_date_summary('2026-02-09') # Today

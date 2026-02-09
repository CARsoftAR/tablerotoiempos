import os
import django
import datetime
from django.db.models import Sum, Q

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from dashboard.models import VTMan
import django.utils.timezone as timezone

def analyze_date_detailed(date_str):
    print(f"=== Detailed Analysis for {date_str} ===")
    
    date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
    
    # Method 2 Range
    d_start = timezone.make_aware(datetime.datetime.combine(date_obj, datetime.time.min), datetime.timezone.utc)
    d_end = timezone.make_aware(datetime.datetime.combine(date_obj, datetime.time.max), datetime.timezone.utc)
    
    qs_range = VTMan.objects.filter(fecha__range=(d_start, d_end))
    
    records = list(qs_range)
    print(f"Total records in UTC range: {len(records)}")
    
    print(f"{'FECHA (UTC)':<25} | {'CONVERT(date)':<15} | {'Real':<8} | {'Std':<8} | {'Perf %':<8}")
    print("-" * 75)
    
    for r in records[:50]: # Print first 50
        r_real = r.tiempo_minutos or 0.0
        r_std_mins = (r.tiempo_cotizado or 0.0) * 60.0
        r_perf = (r_std_mins / r_real * 100) if r_real > 0 else 0
        
        # We can't easily get CONVERT(date) here without another query, but we can check the date of FECHA
        fecha_val = r.fecha
        print(f"{str(fecha_val):<25} | {str(fecha_val.date()):<15} | {r_real:<8.1f} | {r_std_mins:<8.1f} | {r_perf:<8.1f}%")

if __name__ == "__main__":
    analyze_date_detailed('2026-02-07')

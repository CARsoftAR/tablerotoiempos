import os
import django
import datetime
from django.db.models import Sum, Q

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from dashboard.models import VTMan

def analyze_date(date_str):
    print(f"=== Analysis for {date_str} ===")
    
    date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
    
    # Method 1: Extra (CONVERT) - used in main dashboard logic
    qs_extra = VTMan.objects.extra(where=["CONVERT(date, FECHA) = %s"], params=[date_str])
    h_std_extra = qs_extra.aggregate(s=Sum('tiempo_cotizado'))['s'] or 0.0
    h_prod_extra = qs_extra.aggregate(s=Sum('tiempo_minutos'))['s'] or 0.0
    perf_extra = (h_std_extra * 60.0 / h_prod_extra * 100) if h_prod_extra > 0 else 0
    
    print(f"Method 1 (Extra/CONVERT):")
    print(f"  Records: {qs_extra.count()}")
    print(f"  Prod Mins: {h_prod_extra:.1f}")
    print(f"  Std Hours: {h_std_extra:.2f} ({h_std_extra*60:.1f} mins)")
    print(f"  Perf: {perf_extra:.2f}%")
    
    # Method 2: filter(fecha__range) - used in history_trend
    import django.utils.timezone as timezone
    d_start = timezone.make_aware(datetime.datetime.combine(date_obj, datetime.time.min), datetime.timezone.utc)
    d_end = timezone.make_aware(datetime.datetime.combine(date_obj, datetime.time.max), datetime.timezone.utc)
    
    qs_range = VTMan.objects.filter(fecha__range=(d_start, d_end))
    h_std_range = qs_range.aggregate(s=Sum('tiempo_cotizado'))['s'] or 0.0
    h_prod_range = qs_range.aggregate(s=Sum('tiempo_minutos'))['s'] or 0.0
    perf_range = (h_std_range * 60.0 / h_prod_range * 100) if h_prod_range > 0 else 0
    
    print(f"\nMethod 2 (filter/range UTC):")
    print(f"  Records: {qs_range.count()}")
    print(f"  Prod Mins: {h_prod_range:.1f}")
    print(f"  Std Hours: {h_std_range:.2f} ({h_std_range*60:.1f} mins)")
    print(f"  Perf: {perf_range:.2f}%")
    
    if perf_range > 100 or perf_extra > 100:
        print("\nTOP 10 RECORDS BY PERFORMANCE (STD/REAL):")
        # Fetch records and sort in python to avoid complex F expressions
        records = list(qs_extra if perf_extra > 100 else qs_range)
        records_with_perf = []
        for r in records:
            r_real = r.tiempo_minutos or 0.0
            r_std_mins = (r.tiempo_cotizado or 0.0) * 60.0
            r_perf = (r_std_mins / r_real * 100) if r_real > 0 else 0
            records_with_perf.append((r, r_real, r_std_mins, r_perf))
        
        records_with_perf.sort(key=lambda x: x[3], reverse=True)
        
        print(f"{'Machine':<10} | {'Order':<10} | {'Art':<20} | {'Real':<8} | {'Std':<8} | {'Perf %':<8}")
        print("-" * 75)
        for r, real, std, p in records_with_perf[:20]:
            print(f"{str(r.id_maquina):<10} | {str(r.id_orden):<10} | {str(r.articulod)[:20]:<20} | {real:<8.1f} | {std:<8.1f} | {p:<8.1f}%")

if __name__ == "__main__":
    analyze_date('2026-02-07')

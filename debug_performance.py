import os
import django
from django.utils import timezone
import datetime
from django.db.models import Sum

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from dashboard.models import VTMan

def debug_performance():
    # Target date: Yesterday (2026-01-08) as per context
    target_date = datetime.date(2026, 1, 8)
    
    start_utc = datetime.datetime.combine(target_date, datetime.time.min).replace(tzinfo=datetime.timezone.utc)
    end_utc = datetime.datetime.combine(target_date, datetime.time.max).replace(tzinfo=datetime.timezone.utc)
    
    print(f"--- Debugging Global Performance for {target_date} ---")
    
    # Fetch Data
    registros = VTMan.objects.filter(fecha__range=(start_utc, end_utc)).values(
        'id_maquina', 'tiempo_cotizado', 'cantidad_producida', 'tiempo_minutos', 'es_proceso'
    )
    
    machine_stats = {}
    
    for reg in registros:
        mid = reg['id_maquina']
        if mid not in machine_stats:
            machine_stats[mid] = {'std_hrs': 0.0, 'prod_min': 0.0}
            
        # Accumulate Standard Time (It is in Hours per record, already total for the batch/record)
        # Based on verified logic in views.py:
        val_std_hrs = float(reg['tiempo_cotizado']) if reg['tiempo_cotizado'] else 0.0
        
        # In views.py we do: order_stats['total_std_hrs'] += val_std_hrs
        machine_stats[mid]['std_hrs'] += val_std_hrs
        
        # Accumulate Production Time (Actual)
        if reg['es_proceso']:
             val_min = float(reg['tiempo_minutos']) if reg['tiempo_minutos'] else 0.0
             machine_stats[mid]['prod_min'] += val_min

    print(f"{'Maquina':<10} | {'Std (Hs)':<10} | {'Prod (Hs)':<10} | {'Perf %':<10}")
    print("-" * 50)
    
    global_std_hrs = 0.0
    global_prod_hrs = 0.0
    
    for mid, stats in machine_stats.items():
        std_hrs = stats['std_hrs']
        prod_hrs = stats['prod_min'] / 60.0
        
        perf = 0.0
        if prod_hrs > 0:
            perf = (std_hrs / prod_hrs) * 100.0
            
        print(f"{mid:<10} | {std_hrs:<10.2f} | {prod_hrs:<10.2f} | {perf:<10.2f}")
        
        global_std_hrs += std_hrs
        global_prod_hrs += prod_hrs
        
    print("-" * 50)
    global_perf = 0.0
    if global_prod_hrs > 0:
        global_perf = (global_std_hrs / global_prod_hrs) * 100.0
        
    print(f"GLOBAL     | {global_std_hrs:<10.2f} | {global_prod_hrs:<10.2f} | {global_perf:<10.2f}")

if __name__ == '__main__':
    debug_performance()

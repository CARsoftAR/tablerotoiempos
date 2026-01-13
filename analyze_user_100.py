
import os
import django
import datetime
from django.db.models import Sum

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from dashboard.models import VTMan, OperarioConfig

def check_user(legajo):
    print(f"Checking data for legajo: {legajo}")
    regs = VTMan.objects.filter(id_concepto=legajo).order_by('-fecha')
    if not regs.exists():
        print("No records found for this user.")
        return

    # Get the latest date with data
    unique_dates = regs.extra(select={'day': 'CAST(fecha AS DATE)'}).values_list('day', flat=True).distinct()[:5]
    print(f"Recent dates with data: {list(unique_dates)}")

    if not unique_dates:
        return

    for date in unique_dates:
        print(f"\nAnalyzing date: {date}")
        day_regs = VTMan.objects.filter(id_concepto=legajo).extra(where=["CAST(fecha AS DATE) = %s"], params=[date])
        
        total_qty = day_regs.aggregate(Sum('cantidad_producida'))['cantidad_producida__sum'] or 0
        total_time_mins = day_regs.aggregate(Sum('tiempo_minutos'))['tiempo_minutos__sum'] or 0
        total_std_hrs = day_regs.aggregate(Sum('tiempo_cotizado'))['tiempo_cotizado__sum'] or 0
        
        print(f"Total Quantity: {total_qty}")
        print(f"Total Time (mins): {total_time_mins}")
        print(f"Total Time (hrs): {total_time_mins / 60.0:.2f}")
        print(f"Total Std (hrs): {total_std_hrs:.2f}")
        
        if total_time_mins > 0:
            perf = (total_std_hrs * 60.0) / total_time_mins * 100.0
            print(f"Performance: {perf:.2f}%")

    print("\nDetailed Records for 2026-01-12:")
    day_regs_12 = VTMan.objects.filter(id_concepto=legajo).extra(where=["CAST(fecha AS DATE) = '2026-01-12'"])
    for r in day_regs_12.order_by('fecha'):
        print(f"Time: {r.fecha.strftime('%H:%M')} | Machine: {r.id_maquina} | Qty: {r.cantidad_producida} | Dur: {r.tiempo_minutos} min | Std: {r.tiempo_cotizado} hs | Art: {r.articulod} | Proc: {r.es_proceso} | Int: {r.es_interrupcion} | Obs: {r.observaciones}")

if __name__ == "__main__":
    check_user('100')

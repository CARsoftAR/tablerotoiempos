import os
import django
import datetime
from django.db.models import Sum, Q

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from dashboard.models import VTMan

def analyze_date(date_str):
    print(f"--- Analysis for {date_str} ---")
    
    # Range of the day
    date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
    start_dt = datetime.datetime.combine(date_obj, datetime.time.min)
    end_dt = datetime.datetime.combine(date_obj, datetime.time.max)
    
    # Filter records
    # Using the same logic as the dashboard history_trend
    qs = VTMan.objects.filter(fecha__range=(start_dt, end_dt))
    
    total_records = qs.count()
    if total_records == 0:
        print("No records found.")
        return

    h_std = qs.aggregate(s=Sum('tiempo_cotizado'))['s'] or 0.0
    h_prod = qs.aggregate(s=Sum('tiempo_minutos'))['s'] or 0.0
    
    std_mins = h_std * 60.0
    perf = (std_mins / h_prod * 100) if h_prod > 0 else 0
    
    print(f"Total Records: {total_records}")
    print(f"Total Actual Mins (tiempo_minutos): {h_prod:.2f}")
    print(f"Total Std Hours (tiempo_cotizado): {h_std:.2f}")
    print(f"Total Std Mins: {std_mins:.2f}")
    print(f"Calculated Performance (shown as OEE in chart): {perf:.2f}%")
    
    # Breakdown by machine
    print("\nTop machines contributing to high performance:")
    machines = qs.values('id_maquina').annotate(
        real=Sum('tiempo_minutos'),
        std=Sum('tiempo_cotizado')
    ).order_by('-std')
    
    print(f"{'Machine ID':<15} | {'Real (min)':<10} | {'Std (min)':<10} | {'Perf %':<10}")
    print("-" * 55)
    for m in machines:
        m_real = m['real'] or 0.0
        m_std_mins = (m['std'] or 0.0) * 60.0
        m_perf = (m_std_mins / m_real * 100) if m_real > 0 else 0
        print(f"{str(m['id_maquina']):<15} | {m_real:<10.1f} | {m_std_mins:<10.1f} | {m_perf:<10.1f}%")

    # Look for specific anomalies (very high std compared to real)
    print("\nPossible anomalies (records where Std > 2 * Real):")
    anomalies = qs.filter(tiempo_cotizado__gt=F('tiempo_minutos') / 30.0) # Std (hrs) > Real(mins)/30 => Std(mins) > 2*Real(mins)
    # Wait, F is not imported. Let me just loop.
    
    count_anomalies = 0
    for reg in qs:
        r_real = reg.tiempo_minutos or 0.0
        r_std_mins = (reg.tiempo_cotizado or 0.0) * 60.0
        if r_std_mins > r_real * 1.5:
            count_anomalies += 1
            if count_anomalies <= 10:
                print(f"ID: {reg.id} | Machine: {reg.id_maquina} | Order: {reg.id_orden} | Art: {reg.articulod} | Real: {r_real:.1f} | Std: {r_std_mins:.1f} | Obs: {reg.observaciones}")

    print(f"\nTotal records with Std > 1.5 * Real: {count_anomalies}")

if __name__ == "__main__":
    from django.db.models import F
    analyze_date('2025-02-07') # Assuming year is 2026? Wait, current local time is 2026-02-09.
    # The user says 7/2. So 2026-02-07.
    # Let me check current year. System says 2026-02-09.
    analyze_date('2026-02-07')


import os
import django
import datetime
from django.db.models import Sum

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from dashboard.models import VTMan

def audit_day(target_date):
    print(f"\n--- Audit for {target_date} ---")
    
    registros = VTMan.objects.extra(
        where=["CONVERT(date, FECHA) = %s"],
        params=[target_date.strftime('%Y-%m-%d')]
    ).values(
        'id_maquina', 'cantidad_producida', 'id_operacion', 'operacion', 'articulod', 'observaciones', 'tiempo_cotizado', 'tiempo_minutos', 'es_proceso'
    )
    
    total_good_qty = 0
    total_std_mins = 0
    total_prod_mins = 0
    
    for r in registros:
        qty = r['cantidad_producida'] or 0
        std_mins = (r['tiempo_cotizado'] or 0) * 60
        prod_mins = (r['tiempo_minutos'] or 0) if r['es_proceso'] else 0
        
        raw_id_op = str(r.get('id_operacion') or "").strip().upper()
        raw_art_d = str(r.get('articulod') or "").upper()
        raw_op_d = str(r.get('operacion') or "").strip().upper()
        raw_obs = str(r.get('observaciones') or "").strip().upper()

        non_prod_keywords = ['REPROCESO', 'RETRABAJO']
        
        is_repro = (
            raw_id_op in non_prod_keywords or 
            raw_op_d in non_prod_keywords or
            any(k in raw_art_d for k in non_prod_keywords) or
            any(k in raw_obs for k in non_prod_keywords)
        )
        
        if not is_repro:
            total_good_qty += qty
            total_std_mins += std_mins
        
        total_prod_mins += prod_mins

    print(f"Cant Real: {total_good_qty}")
    h_std, m_std = divmod(int(round(total_std_mins)), 60)
    print(f"Tiempo Std: {h_std} hs {m_std} min")
    
    global_std_hrs = total_std_mins / 60
    global_prod_hrs = total_prod_mins / 60
    global_perf = (global_std_hrs / global_prod_hrs) if global_prod_hrs > 0 else 0
    global_planned = (total_good_qty / global_perf) if global_perf > 0 else 0
    print(f"Cant Planif: {round(global_planned)}")

if __name__ == "__main__":
    audit_day(datetime.date(2026, 1, 9))
    audit_day(datetime.date(2026, 1, 8))
    audit_day(datetime.date(2026, 1, 7))


import os
import django
import datetime
from django.db.models import Sum

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from dashboard.models import VTMan

def breakdown_performance():
    today = datetime.date.today()
    print(f"Breakdown for {today}")
    
    registros = VTMan.objects.extra(
        where=["CONVERT(date, FECHA) = %s"],
        params=[today.strftime('%Y-%m-%d')]
    ).values(
        'id_maquina', 'cantidad_producida', 'id_operacion', 'operacion', 'articulod', 'observaciones', 'tiempo_cotizado', 'tiempo_minutos', 'es_proceso'
    )
    
    total_good_qty = 0
    total_std_mins = 0
    total_prod_mins = 0
    
    by_machine = {}
    
    for r in registros:
        mid = r['id_maquina'] or 'SIN ASIGNAR'
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
            
            if mid not in by_machine:
                by_machine[mid] = {'qty': 0, 'std_hrs': 0, 'prod_hrs': 0}
            
            by_machine[mid]['qty'] += qty
            by_machine[mid]['std_hrs'] += std_mins / 60
            by_machine[mid]['prod_hrs'] += prod_mins / 60
            
        total_prod_mins += prod_mins

    print(f"{'Maquina':<15} | {'Cant Real':<10} | {'Tiempo Std':<12} | {'Tiempo Real':<12} | {'Cant Planif':<10}")
    print("-" * 75)
    
    for mid, data in sorted(by_machine.items(), key=lambda x: x[1]['qty'], reverse=True):
        std_hrs = data['std_hrs']
        prod_hrs = data['prod_hrs']
        qty = data['qty']
        
        # Planned Qty per machine = Qty / (Performance/100) = Qty / (StdHrs / ProdHrs) = (Qty * ProdHrs) / StdHrs
        # No, Planned Qty = ProdHrs / IndividualCotizado.
        # Performance = StdHrs / ProdHrs.
        # Planned Qty = Qty / performance = Qty / (StdHrs/ProdHrs) = Qty * ProdHrs / StdHrs.
        
        perf = (std_hrs / prod_hrs) if prod_hrs > 0 else 0
        planned = (qty / perf) if perf > 0 else 0
        
        print(f"{mid:15} | {qty:<10.2f} | {std_hrs:<12.2f} | {prod_hrs:<12.2f} | {planned:<10.0f}")

    global_std_hrs = total_std_mins / 60
    global_prod_hrs = total_prod_mins / 60
    global_perf = (global_std_hrs / global_prod_hrs) if global_prod_hrs > 0 else 0
    global_planned = (total_good_qty / global_perf) if global_perf > 0 else 0
    
    print("-" * 75)
    print(f"{'TOTAL':15} | {total_good_qty:<10.2f} | {global_std_hrs:<12.2f} | {global_prod_hrs:<12.2f} | {global_planned:<10.0f}")
    
    h_std = int(total_std_mins // 60)
    m_std = int(round(total_std_mins % 60))
    print(f"\nTiempo Estándar Formateado: {h_std} hs {m_std} min")

if __name__ == "__main__":
    breakdown_performance()

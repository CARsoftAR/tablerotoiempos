
import os
import django
import datetime
from django.db.models import Sum

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from dashboard.models import VTMan

def breakdown_0901():
    target_date = datetime.date(2026, 1, 9)
    print(f"Detailed Breakdown for {target_date}")
    
    registros = VTMan.objects.extra(
        where=["CONVERT(date, FECHA) = %s"],
        params=[target_date.strftime('%Y-%m-%d')]
    ).values(
        'id_maquina', 'cantidad_producida', 'id_operacion', 'operacion', 'articulod', 'observaciones', 'tiempo_cotizado', 'tiempo_minutos', 'es_proceso'
    )
    
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
            if mid not in by_machine:
                by_machine[mid] = {'qty': 0, 'std_hrs': 0, 'prod_hrs': 0}
            by_machine[mid]['qty'] += qty
            by_machine[mid]['std_hrs'] += std_mins / 60
            by_machine[mid]['prod_hrs'] += prod_mins / 60

    print(f"{'Maquina':<15} | {'Cant Real':<10} | {'Tiempo Std':<12} | {'Tiempo Real':<12}")
    print("-" * 60)
    
    for mid, data in sorted(by_machine.items(), key=lambda x: x[1]['qty'], reverse=True):
        print(f"{mid:15} | {data['qty']:<10.1f} | {data['std_hrs']:<12.2f} | {data['prod_hrs']:<12.2f}")

if __name__ == "__main__":
    breakdown_0901()

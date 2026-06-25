import os
import django
import sys
import datetime

sys.path.append(r'c:\Sistemas ABBAMAT\tablerotoiempos')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from dashboard.models import MaquinaConfig

def diagnose_gap():
    target_date = "2026-03-11"
    print(f"=== DIAGNÓSTICO DE DIFERENCIA DE TIEMPOS - {target_date} ===")
    
    maquinas_activas_ids = set(MaquinaConfig.objects.filter(activa=True).values_list('id_maquina', flat=True))
    
    from django.db import connections
    with connections['sql_server'].cursor() as cursor:
        # 1. Total RAW (todo, sin filtros)
        cursor.execute(f"SELECT SUM(TIEMPO_MINUTOS) FROM V_TMAN WHERE CONVERT(date, FECHA) = '{target_date}'")
        raw_total = cursor.fetchone()[0] or 0

        # 2. Descansos
        cursor.execute(f"""SELECT SUM(TIEMPO_MINUTOS) FROM V_TMAN 
            WHERE CONVERT(date, FECHA) = '{target_date}'
            AND (ARTICULOD LIKE '%DESCANSO%' OR ARTICULOD LIKE '%ALMUERZO%' OR ARTICULOD LIKE '%PAUSA%'
                OR OBS LIKE '%DESCANSO%' OR OBS LIKE '%ALMUERZO%')""")
        descanso_total = cursor.fetchone()[0] or 0

        # 3. Matricería
        cursor.execute(f"""SELECT SUM(TIEMPO_MINUTOS) FROM V_TMAN 
            WHERE CONVERT(date, FECHA) = '{target_date}'
            AND (ARTICULOD LIKE '%MATR%' OR OPERACION LIKE '%MATR%' OR OBS LIKE '%MATR%')""")
        mat_total = cursor.fetchone()[0] or 0

        # 4. Registros sin máquina (IDMAQUINA vacío o no configurado)
        cursor.execute(f"""SELECT IDMAQUINA, SUM(TIEMPO_MINUTOS), COUNT(*) FROM V_TMAN 
            WHERE CONVERT(date, FECHA) = '{target_date}'
            AND (ARTICULOD NOT LIKE '%MATR%' OR ARTICULOD IS NULL)
            AND (OBS NOT LIKE '%MATR%' OR OBS IS NULL)
            AND (ARTICULOD NOT LIKE '%DESCANSO%' OR ARTICULOD IS NULL)
            AND (OBS NOT LIKE '%DESCANSO%' OR OBS IS NULL)
            GROUP BY IDMAQUINA
            ORDER BY SUM(TIEMPO_MINUTOS) DESC""")
        by_machine = cursor.fetchall()
        
        print(f"\nTotal RAW:          {raw_total:.0f} min ({raw_total/60:.2f} hs)")
        print(f"Descansos:          {descanso_total:.0f} min ({descanso_total/60:.2f} hs)")
        print(f"Matricería:         {mat_total:.0f} min ({mat_total/60:.2f} hs)")
        print(f"Resto:              {(raw_total-descanso_total-mat_total):.0f} min ({(raw_total-descanso_total-mat_total)/60:.2f} hs)")
        
        print("\nDetalle por Máquina (excluyendo Descansos y Matricería):")
        en_activas = 0
        sin_asignar = 0
        for mid, t_mins, cnt in by_machine:
            mid_str = str(mid).strip().upper() if mid else "SIN_MAC"
            en_activas_flag = "ACTIVA" if mid_str in maquinas_activas_ids else "sin config"
            
            if mid_str in maquinas_activas_ids:
                en_activas += (t_mins or 0)
            else:
                sin_asignar += (t_mins or 0)
            
            print(f"  {mid_str:10} | {(t_mins or 0):6.0f} min ({(t_mins or 0)/60:.2f} hs) | {cnt} regs | {en_activas_flag}")
        
        print(f"\nTOTAL EN MÁQUINAS ACTIVAS (post-filtros):  {en_activas:.0f} min ({en_activas/60:.2f} hs)")
        print(f"TOTAL SIN ASIGNAR (post-filtros):          {sin_asignar:.0f} min ({sin_asignar/60:.2f} hs)")
        print(f"\nDashboard muestra: Real=85 hs 40 min | Sin Asignar=49 hs 56 min")

if __name__ == "__main__":
    diagnose_gap()

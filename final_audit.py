import os
import django
import sys
import datetime

sys.path.append(r'c:\Sistemas ABBAMAT\tablerotoiempos')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from dashboard.models import VTMan, MaquinaConfig

def final_audit_11_march():
    target_date = "2026-03-11"
    print(f"=== AUDITORÍA FINAL POST-EXCLUSIÓN MATRICERÍA - {target_date} ===")
    
    # Obtener máquinas activas (configuradas)
    maquinas_activas_ids = list(MaquinaConfig.objects.filter(activa=True).values_list('id_maquina', flat=True))
    
    from django.db import connections
    with connections['sql_server'].cursor() as cursor:
        cursor.execute(f"""
            SELECT 
                IDMAQUINA, 
                TIEMPO_MINUTOS, 
                TIEMPO_COTIZADO, 
                CANTIDAD_PRODUCIDA, 
                ARTICULOD, 
                OPERACION, 
                OBS,
                IDOPERACION
            FROM V_TMAN 
            WHERE CONVERT(date, FECHA) = '{target_date}'
        """)
        rows = cursor.fetchall()
        
        # Filtros (idénticos a views.py tras el cambio)
        mat_kws = ['MATRIC', 'MATRIZ', 'MATR.', 'MATR']
        descanso_keywords = ['DESCANSO', 'ALMUERZO', 'PAUSA', 'PERSONAL', 'VACACIONES', 'LICENCIA']
        special_keywords = [
            'TAREAS GENERALES', 'AJUSTES', 'REBABADO', 'GRABADO', 'ARMADO', 'ACCESORIOS',
            'CAPACI', 'CAPACIT', 'TENSI', 'TENSION', 'HERRAMIENTA', 'MANTEN', 'REPAR',
            'CORRECTIVO', 'PREVENTIVO', 'AJUST', 'SET-UP', 'SETUP', 'LIMPIEZA', 
            'REUNION', 'REUNIÓN', 'MATERIAL', 'ESPERA', 'ENSAYO', 'INSPEC', 'ASIST', 'AUXILIO'
        ]

        # Acumuladores (Solo para máquinas configuradas)
        total_real_mins = 0
        total_std_mins = 0
        total_qty = 0
        
        # Acumuladores Sin Asignar
        unassigned_real = 0
        unassigned_qty = 0
        
        matriceria_total_mins = 0
        matriceria_count = 0

        for row in rows:
            mid, t_min, t_std_hs, qty, art, op_d, obs, id_op = row
            mid = str(mid).strip().upper() if mid else None
            art = str(art or "").upper()
            op_d = str(op_d or "").upper()
            obs = str(obs or "").upper()
            id_op = str(id_op or "").upper()
            
            full_text = f"{art} {op_d} {obs} {id_op}"
            
            is_matriceria = any(k in full_text for k in mat_kws)
            is_descanso = any(k in full_text for k in descanso_keywords)
            
            if is_matriceria:
                matriceria_total_mins += (t_min or 0)
                matriceria_count += 1
                continue
                
            if is_descanso:
                continue

            if not mid or mid not in maquinas_activas_ids:
                unassigned_real += (t_min or 0)
                unassigned_qty += (qty or 0)
                continue

            # Producción de Serie
            t_min_val = (t_min or 0)
            t_std_min = (t_std_hs or 0) * 60
            qty_val = (qty or 0)
            
            # Regla 1:1
            is_neutral = any(k in full_text for k in special_keywords)
            effective_std = t_std_min
            if is_neutral:
                effective_std = t_min_val
                
            total_real_mins += t_min_val
            total_std_mins += effective_std
            total_qty += qty_val

    def to_hs_min(m):
        h = int(m // 60)
        mins = int(round(m % 60))
        if mins == 60: h += 1; mins = 0
        return f"{h} hs {mins} min"

    print("-" * 50)
    print(f"MATRICERÍA EXCLUIDA: {matriceria_count} registros | Tiempo: {to_hs_min(matriceria_total_mins)}")
    print("-" * 50)
    print(f"RESUMEN DASHBOARD (MÁQUINAS):")
    print(f"Tiempo Real: {to_hs_min(total_real_mins)} (Foto: 85 hs 40 min)")
    print(f"Tiempo Estándar: {to_hs_min(total_std_mins)} (Foto: 16 hs 57 min)")
    print(f"Cantidad Real: {total_qty} (Foto: 115.0)")
    print("-" * 50)
    print(f"RESUMEN SIN ASIGNAR:")
    print(f"Tiempo Real: {to_hs_min(unassigned_real)} (Foto: 49 hs 56 min)")
    print(f"Cantidad: {unassigned_qty} (Foto: 21.0)")
    
    computed_perf = (total_std_mins / total_real_mins * 100) if total_real_mins > 0 else 0
    print("-" * 50)
    print(f"RENDIMIENTO CALCULADO: {computed_perf:.2f}% (Foto: 19.78%)")

if __name__ == "__main__":
    final_audit_11_march()

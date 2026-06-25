import os
import django
import sys
import datetime

sys.path.append(r'c:\Sistemas ABBAMAT\tablerotoiempos')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from dashboard.models import MaquinaConfig

def predict_new_values():
    target_date = "2026-03-11"
    print(f"=== PREDICCIÓN DE VALORES POST-CORRECCIÓN - {target_date} ===")
    
    maquinas_activas_ids = set(MaquinaConfig.objects.filter(activa=True).values_list('id_maquina', flat=True))
    configs = {m.id_maquina: m for m in MaquinaConfig.objects.filter(activa=True)}
    
    from django.db import connections
    with connections['sql_server'].cursor() as cursor:
        cursor.execute(f"""
            SELECT IDMAQUINA, ARTICULOD, OPERACION, OBS, IDOPERACION,
                   TIEMPO_MINUTOS, TIEMPO_COTIZADO, CANTIDAD_PRODUCIDA
            FROM V_TMAN 
            WHERE CONVERT(date, FECHA) = '{target_date}'
            ORDER BY HORA_D
        """)
        rows = cursor.fetchall()
        
    mat_kws = ['MATRIC', 'MATRIZ', 'MATR.', 'MATR']
    descanso_kws = ['DESCANSO', 'ALMUERZO', 'PAUSA', 'PERSONAL', 'VACACIONES']
    special_kws = ['AJUST', 'SET-UP', 'SETUP', 'LIMPIEZA', 'REUNION', 'MATERIAL', 'ESPERA', 'ENSAYO', 'INSPEC', 'ASIST', 'ARMADO', 'TAREAS', 'REBABADO', 'GRABADO']

    total_real = 0
    total_std = 0
    total_qty = 0
    mat_excluida = 0
    unassigned_real = 0
    unassigned_std = 0
    unassigned_qty = 0
    
    # Acumular por maquina
    mac_real = {}
    mac_disp = {}
    
    # Calcular disponibilidad total (turno por machina activa con actividad)
    macs_con_actividad = set()
    for row in rows:
        mid, art, op_d, obs, id_op, t_min, t_std, qty = row
        mid = str(mid).strip().upper() if mid else None
        full = f"{str(art or '')} {str(op_d or '')} {str(obs or '')} {str(id_op or '')}".upper()
        
        is_mat = any(k in full for k in mat_kws)
        is_desc = any(k in full for k in descanso_kws)
        
        if is_mat: mat_excluida += (t_min or 0); continue
        if is_desc: continue
        
        macs_con_actividad.add(mid)
    
    # Calcular disponibilidad por máquina activa que tuvo actividad
    total_disp = 0
    for mid in macs_con_actividad:
        if mid and mid in configs:
            c = configs[mid]
            start = c.horario_inicio_sem
            end = c.horario_fin_sem
            s = start.hour + start.minute/60.0
            e = end.hour + end.minute/60.0
            if e < s: e += 24
            total_disp += (e - s)
    
    # Restar matricería excluida
    disp_neta = total_disp - (mat_excluida / 60.0)
    
    # Calcular productivo
    for row in rows:
        mid, art, op_d, obs, id_op, t_min, t_std, qty = row
        mid = str(mid).strip().upper() if mid else None
        full = f"{str(art or '')} {str(op_d or '')} {str(obs or '')} {str(id_op or '')}".upper()
        
        is_mat = any(k in full for k in mat_kws)
        is_desc = any(k in full for k in descanso_kws)
        is_neutral = any(k in full for k in special_kws)
        
        if is_mat or is_desc: continue
        
        t_min_val = (t_min or 0)
        t_std_min = (t_std or 0) * 60
        qty_val = (qty or 0)
        
        if is_neutral: t_std_min = t_min_val
        
        if mid and mid in maquinas_activas_ids:
            total_real += t_min_val
            total_std += t_std_min
            total_qty += qty_val
        else:
            unassigned_real += t_min_val
            unassigned_std += t_std_min
            unassigned_qty += qty_val
    
    def to_hs_min(m):
        h = int(m // 60)
        mn = int(round(m % 60))
        if mn == 60: h += 1; mn = 0
        return f"{h} hs {mn} min"

    print(f"\nMatriceria excluida: {to_hs_min(mat_excluida)}")
    print(f"\nDisponibilidad de turno (maquinas activas con actividad): {total_disp:.2f} hs")
    print(f"Disponibilidad NETA (turno - matriceria): {disp_neta:.2f} hs")
    
    grand_real = total_real + unassigned_real
    grand_std = total_std + unassigned_std
    
    print(f"\nTiempo Real TOTAL (maquinas + sin asignar): {to_hs_min(grand_real)}")
    print(f"Tiempo Std TOTAL: {to_hs_min(grand_std)}")
    print(f"Cantidad Piezas: {total_qty + unassigned_qty:.0f}")
    
    base_disp = max(disp_neta, grand_real / 60.0)
    rendimiento = (grand_std / 60.0) / (grand_real / 60.0) * 100 if grand_real > 0 else 0
    disponibilidad = min(100, (grand_real / 60.0) / base_disp * 100) if base_disp > 0 else 0
    
    print(f"\n--- VALORES ESPERADOS EN TABLERO ---")
    print(f"Disponibilidad: {disponibilidad:.1f}%  (actual en pantalla: 100.0%)")
    print(f"Rendimiento: {rendimiento:.2f}%  (actual en pantalla: 19.78%)")
    print(f"Esperado: {to_hs_min(disp_neta * 60)}  (actual en pantalla: 61 hs 0 min)")
    print(f"Real: {to_hs_min(grand_real)}  (actual en pantalla: 85 hs 40 min)")
    print(f"Estándar: {to_hs_min(grand_std)}  (actual en pantalla: 16 hs 57 min)")

if __name__ == "__main__":
    predict_new_values()

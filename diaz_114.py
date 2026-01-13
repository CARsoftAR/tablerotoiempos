
import os
import pyodbc
import datetime

# Database connection configuration
DB_CONFIG = {
    'driver': '{ODBC Driver 17 for SQL Server}',
    'server': 'SERVIDORAID\\SQLEXPRESS',
    'database': 'TMAN_ABBAMAT_REAL',
    'user': 'sa',
    'pass': 'aid'
}

def check_diaz():
    conn_str = f"DRIVER={DB_CONFIG['driver']};SERVER={DB_CONFIG['server']};DATABASE={DB_CONFIG['database']};UID={DB_CONFIG['user']};PWD={DB_CONFIG['pass']}"
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        target_date = "2026-01-12"
        target_id = "114"
        
        query = """
            SELECT HORA_D, HORA_H, id_orden, articulod, cantidad, tpp, tpr, id_concepto, concepto, observaciones, es_proceso, es_interrupcion
            FROM V_TMAN
            WHERE CAST(HORA_D AS DATE) = ? AND id_concepto = ?
            ORDER BY HORA_D ASC
        """
        
        cursor.execute(query, (target_date, target_id))
        rows = cursor.fetchall()
        
        print(f"--- Data for {target_id} on {target_date} ---")
        total_qty = 0
        total_std_raw = 0
        total_real = 0
        total_descanso = 0
        
        for r in rows:
            hd = r.HORA_D
            hh = r.HORA_H
            dur = (hh - hd).total_seconds() / 3600.0
            qty = float(r.cantidad or 0)
            
            # In ERP, if is_proceso=1, tpp is usually total std?
            # Looking at Image 1: Row 1 (6 units) has Std .90. $0.90 / 6 = 0.15$.
            # So tpp seems to be total std for the record in this view.
            std_total = float(r.tpp or 0)
            
            is_descanso = "DESCANSO" in str(r.articulod).upper() or "DESCANSO" in str(r.observaciones).upper()
            
            print(f"Record: {hd.strftime('%H:%M')}-{hh.strftime('%H:%M')} | Art: {r.articulod} | Qty: {qty} | StdTotal: {std_total:.2f} | Real: {dur:.2f}")
            
            if is_descanso:
                total_descanso += dur
            else:
                total_qty += qty
                total_std_raw += std_total
                total_real += dur
                
        print("-" * 30)
        print(f"Total Qty (Excl Break): {total_qty}")
        print(f"Total Std (Hours): {total_std_raw:.2f}")
        print(f"Total Real (Hours): {total_real:.2f}")
        print(f"Total Break (Hours): {total_descanso:.2f}")
        
        perf = (total_std_raw / total_real * 100) if total_real > 0 else 0
        print(f"Performance (Std/Real): {perf:.2f}%")
        
        # OEE calculation with 9h base
        avail = (total_real / 9.0 * 100)
        oee = (avail * perf) / 100
        print(f"OEE (Base 9h): {oee:.2f}%")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_diaz()

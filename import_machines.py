from dashboard.models import Maquina, MaquinaConfig
import sys

def run():
    print("--- Iniciando Importación de Máquinas (SQL Server -> MySQL) ---")
    
    try:
        # Obtener todas las máquinas del ERP (SQL Server)
        maquinas_erp = Maquina.objects.all()
        print(f"Se encontraron {maquinas_erp.count()} máquinas en el ERP.")
        
        creadas = 0
        existentes = 0

        for m_sql in maquinas_erp:
            # Intentar crear en MySQL si no existe
            # Usamos 'get_or_create' para no duplicar ni sobrescribir si el usuario ya editó algo
            obj, created = MaquinaConfig.objects.get_or_create(
                id_maquina=m_sql.id_maquina,
                defaults={
                    'nombre': m_sql.descripcion,  # Usamos la descripción del ERP como nombre inicial
                    'horario_inicio_sem': '07:00',
                    'horario_fin_sem': '16:00',
                    'trabaja_sabado': False,
                    'trabaja_domingo': False
                }
            )
            
            if created:
                creadas += 1
                print(f"[NUEVA] {m_sql.id_maquina}: {m_sql.descripcion}")
            else:
                existentes += 1
        
        print("-" * 30)
        print(f"Proceso Terminado.\nMáquinas importadas: {creadas}\nMáquinas ya existentes: {existentes}")

    except Exception as e:
        print(f"ERROR CRÍTICO: {e}")

if __name__ == '__main__':
    run()

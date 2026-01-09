import os
import django
import sys

# Add project root to path if needed (though running from root usually works)
sys.path.append(os.getcwd())

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from dashboard.models import MaquinaConfig

def run():
    # Lista de máquinas manuales
    # Puedes agregar más diccionarios a esta lista
    machines = [
        {"id": "MAC05", "name": "BANCO SOLDADURA 1"},
        {"id": "MAC40", "name": "NLX 2500"},
        {"id": "MAC42", "name": "HYUNDA ME020"},
        {"id": "MAC06", "name": "BANCO TRABAJO 1"},
        {"id": "MAC43", "name": "HAAS MILL ME048"},
        {"id": "MAC38", "name": "TSUGAMI TAM8J"},
        {"id": "MAC08", "name": "HAAS"},
        {"id": "MAC13", "name": "TM1"},
    ]
    
    print("--- Iniciando Carga Manual de Máquinas ---")
    
    # 1. Cargar las explícitas con nombres conocidos
    for m in machines:
        obj, created = MaquinaConfig.objects.get_or_create(
            id_maquina=m["id"],
            defaults={
                "nombre": m["name"],
                "horario_inicio_sem": "07:00", 
                "horario_fin_sem": "16:00",
                "trabaja_sabado": False,
                "trabaja_domingo": False
            }
        )
        if created:
            print(f"[NUEVA] {m['id']} - {m['name']}")
        else:
             # Solo actualizamos nombre si es uno de los "conocidos" y difiere (opcional)
             if obj.nombre != m["name"]:
                print(f"[EXISTE] {m['id']} - {obj.nombre} (Mantenemos nombre actual)")
             else:
                print(f"[EXISTE] {m['id']} - {m['name']}")

    # 2. Descubrir otras desde V_TMAN
    print("\n--- Buscando máquinas adicionales en historial de producción (V_TMAN) ---")
    try:
        from dashboard.models import VTMan
        from datetime import timedelta
        from django.utils import timezone
        
        cutoff = timezone.now() - timedelta(days=90)
        # IDs únicos últimos 90 días
        found_ids = VTMan.objects.filter(fecha__gte=cutoff).values_list('id_maquina', flat=True).distinct()
        # Limpiar
        found_ids = [mid for mid in found_ids if mid]
        
        cnt = 0
        for mid in set(found_ids):
            # Si no existe en MaquinaConfig, crearla
            if not MaquinaConfig.objects.filter(id_maquina=mid).exists():
                MaquinaConfig.objects.create(
                    id_maquina=mid,
                    nombre=f"Maquina {mid}", # Nombre provisional
                    horario_inicio_sem="07:00",
                    horario_fin_sem="16:00"
                )
                print(f"[DESCUBIERTA] {mid} - Agregada como 'Maquina {mid}'")
                cnt += 1
        
        print(f"-> Se agregaron {cnt} máquinas descubiertas automáticamente.")

    except Exception as e:
        print(f"Error descubriendo máquinas: {e}")

    print("-" * 30)
    print("Carga completa.")

if __name__ == "__main__":
    run()

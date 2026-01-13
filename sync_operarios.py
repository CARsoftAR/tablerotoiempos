import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from dashboard.models import VTMan, OperarioConfig
from django.utils import timezone
from datetime import timedelta

def sync_operarios():
    print("Buscando operarios con actividad en los últimos 30 días...")
    
    # Buscamos registros de los últimos 30 días para considerar al personal "activo"
    hace_30_dias = timezone.now() - timedelta(days=30)
    
    # Obtenemos legajos únicos de la vista de SQL Server (En este ERP se guardan en IDCONCEPTO)
    legajos_activos = VTMan.objects.filter(
        fecha__gte=hace_30_dias
    ).values_list('id_concepto', flat=True).distinct()
    
    # Lista de operarios que NO son de producción o ya no están activos (solicitado por el usuario)
    EXCLUDE_OPERARIOS = ['CRISTIAN', 'DALLAGASSA', 'DPADOVANI', 'JMOROCHI', 'JOSE', 'LEANDRO', 'MARIANO']
    
    count_new = 0
    count_deactivated = 0
    
    for legajo in legajos_activos:
        if not legajo:
            continue
            
        legajo = str(legajo).strip()
        
        # Si está en la lista de excluidos, nos aseguramos de que no esté activo
        if legajo in EXCLUDE_OPERARIOS:
            operario = OperarioConfig.objects.filter(legajo=legajo).first()
            if operario and operario.activo:
                operario.activo = False
                operario.save()
                print(f" [!] Operario {legajo} desactivado (excluido por configuración).")
                count_deactivated += 1
            continue
        
        # Si no existe en la tabla de configuración (MySQL), lo creamos
        operario, created = OperarioConfig.objects.get_or_create(
            legajo=legajo,
            defaults={
                'nombre': f"Operario {legajo}", # Placeholder
                'sector': 'PRODUCCION',
                'activo': True
            }
        )
        
        if created:
            print(f" [+] Nuevo operario detectado y agregado: {legajo}")
            count_new += 1
        else:
            # Si ya existe, nos aseguramos de que esté marcado como activo (si no está en la lista negra)
            if not operario.activo:
                operario.activo = True
                operario.save()
                print(f" [*] Operario {legajo} reactivado.")

    print(f"\nSincronización finalizada.")
    print(f"- Se agregaron {count_new} nuevos operarios.")
    print(f"- Se desactivaron {count_deactivated} operarios excluidos.")

if __name__ == "__main__":
    sync_operarios()

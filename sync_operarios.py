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
    
    # Obtenemos legajos y nombres únicos de la vista de SQL Server
    # En este ERP, IDCONCEPTO es el legajo y CONCEPTO es el nombre
    operarios_erp = VTMan.objects.filter(
        fecha__gte=hace_30_dias
    ).values('id_concepto', 'concepto').distinct()
    
    # Lista de operarios que NO son de producción o ya no están activos
    EXCLUDE_OPERARIOS = ['CRISTIAN', 'DALLAGASSA', 'DPADOVANI', 'JMOROCHI', 'JOSE', 'LEANDRO', 'MARIANO']
    
    count_new = 0
    count_updated = 0
    count_deactivated = 0
    
    # Procesamos los resultados del ERP
    for entry in operarios_erp:
        legajo = entry['id_concepto']
        nombre_erp = entry['concepto']
        
        if not legajo:
            continue
            
        legajo = str(legajo).strip()
        nombre_erp = str(nombre_erp).strip() if nombre_erp else f"Operario {legajo}"
        
        # Si está en la lista de excluidos, nos aseguramos de que no esté activo
        if legajo in EXCLUDE_OPERARIOS:
            operario = OperarioConfig.objects.filter(legajo=legajo).first()
            if operario and operario.activo:
                operario.activo = False
                operario.save()
                print(f" [!] Operario {legajo} desactivado (excluido por configuración).")
                count_deactivated += 1
            continue
        
        # Buscamos si ya existe
        operario = OperarioConfig.objects.filter(legajo=legajo).first()
        
        if not operario:
            # Lo creamos con el nombre real del ERP
            OperarioConfig.objects.create(
                legajo=legajo,
                nombre=nombre_erp,
                sector='PRODUCCION',
                activo=True
            )
            print(f" [+] Nuevo operario detectado: {nombre_erp} ({legajo})")
            count_new += 1
        else:
            # Si ya existe, actualizamos el nombre si era un placeholder o si cambió
            cambio = False
            if operario.nombre != nombre_erp and (operario.nombre == f"Operario {legajo}" or not operario.nombre):
                print(f" [*] Actualizando nombre de {operario.nombre} a {nombre_erp}")
                operario.nombre = nombre_erp
                cambio = True
            
            if not operario.activo:
                operario.activo = True
                cambio = True
                print(f" [*] Operario {legajo} reactivado.")
                
            if cambio:
                operario.save()
                count_updated += 1

    print(f"\nSincronización finalizada.")
    print(f"- Se agregaron {count_new} nuevos operarios.")
    print(f"- Se actualizaron {count_updated} operarios.")
    print(f"- Se desactivaron {count_deactivated} operarios excluidos.")

if __name__ == "__main__":
    sync_operarios()

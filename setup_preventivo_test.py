import os
import django
import datetime
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from dashboard.models import MaquinaConfig

def setup_test():
    mc = MaquinaConfig.objects.first()
    if not mc:
        print("No hay máquinas configuradas.")
        return

    print(f"Configurando mantenimiento preventivo para: {mc.nombre}")
    
    # Configurar para que requiera service cada 500 horas
    mc.frecuencia_preventivo_horas = 500
    
    # Fingir que el último service fue hace 6 meses
    # Esto debería causar que acumule muchas horas de la base de datos real
    last_service = timezone.now() - datetime.timedelta(days=180)
    mc.fecha_ultimo_preventivo = last_service
    
    mc.save()
    print(f"Hecho. Frecuencia: {mc.frecuencia_preventivo_horas}h, Último Service: {mc.fecha_ultimo_preventivo}")

if __name__ == "__main__":
    setup_test()

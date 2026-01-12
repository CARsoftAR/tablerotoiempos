import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()
from dashboard.models import MaquinaConfig

maquinas = MaquinaConfig.objects.all()
print(f"{'ID':<10} | {'Sem Inicio':<10} | {'Sem Fin':<10} | {'Sab':<5} | {'Sab Inicio':<10} | {'Sab Fin':<10}")
print("-" * 75)
for m in maquinas:
    print(f"{m.id_maquina:<10} | {str(m.horario_inicio_sem):<10} | {str(m.horario_fin_sem):<10} | {str(m.trabaja_sabado):<5} | {str(m.horario_inicio_sab):<10} | {str(m.horario_fin_sab):<10}")

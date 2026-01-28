import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from dashboard.models import MaquinaConfig

data = """
MAC02 AGUJEREADORA
MAC03 AGUJEREADORA DE COLUMNA
MAC04 BANCO PULIDO 1
MAC04a BANCO PULIDO 2
MAC04b BANCO PULIDO 3
MAC05 BANCO SOLDADURA 1
MAC05a BANCO SOLDADURA 2
MAC05b BANCO SOLDADURA 3
MAC06 BANCO TRABAJO 1
MAC06a BANCO TRABAJO 2
MAC06b BANCO TRABAJO 3
MAC07 DECKEL
MAC08 HAAS
MAC09 LAGUN
MAC10 LE-PEC
MAC11 (OBSOLETO) OKUMA
MAC12 T-23
MAC13 TM1
MAC14 TORNO CHINO
MAC15 TORNO COPIADOR 1
MAC16 TORNO PULIDO 1
MAC16a TORNO PULIDO 2
MAC17 TURRI 180
MAC18 VF2
MAC19 (OBSOLETO) VF3-1
MAC20 VF3-2
MAC21 W-52
MAC22 HORNO
MAC23 VM3
MAC24 CONTROL
MAC25 AGUJEREADORA NEUMATICA
MAC26 TURRI 190
MAC27 PC DISEÑO 1
MAC28 PC DISEÑO 2
MAC29 PC DISEÑO 3
MAC30 ASPIRADORA
MAC31 PC ARMADOS EXTERNOS
MAC32 BANCO DE MANTENIMIENTO
MAC33 FRESA TORRETA
MAC34 TORNO WING
MAC35 EROSIONADORA
MAC36 SENSITIVA
MAC37 DMG 800V
MAC38 TSUGAMI TAM8J
MAC39 ISAJE DE EMBALAJE
MAC40 NLX 2500
MAC41 RECTIFICADORA TANGENCIAL
MAC42 HYUNDA ME020
MAC43 HAAS MILL ME048
MAC44 HYUNDA ME021
MAC45 HAAS MILL 049
"""

lines = data.strip().split('\n')
print(f"Found {len(lines)} lines to process.")

for line in lines:
    parts = line.strip().split(' ', 1)
    if len(parts) == 2:
        id_maquina = parts[0].strip()
        nombre = parts[1].strip()
        
        try:
            obj, created = MaquinaConfig.objects.update_or_create(
                id_maquina=id_maquina,
                defaults={'nombre': nombre}
            )
            print(f"{'Created' if created else 'Updated'}: {id_maquina} - {nombre}")
        except Exception as e:
            print(f"Error processing {id_maquina}: {e}")
    else:
        print(f"Skipping invalid line: {line}")

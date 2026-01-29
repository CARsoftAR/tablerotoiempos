
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from dashboard.views import dashboard_produccion, plant_map
from dashboard.models import MaquinaConfig, Mantenimiento
from django.test import RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware
import json

rf = RequestFactory()
req = rf.get('/')
middleware = SessionMiddleware(lambda x: None)
middleware.process_request(req)
req.session.save()

# Call plant_map directly to see what it returns to the template
# We need to mock the response or just use the logic inside it
prod_ctx = dashboard_produccion(req, return_context=True, force_date='today')
mants_activos = Mantenimiento.objects.filter(estado__in=['ABIERTO', 'PROCESO'])
maquinas_en_reparacion = [m.maquina_id for m in mants_activos]

kpi_lookup = {}
for k in prod_ctx.get('kpis', []):
    kid = str(k.get('id') or '').strip().upper()
    kname = str(k.get('name') or '').strip().upper()
    if kid: kpi_lookup[kid] = k
    if kname: kpi_lookup[kname] = k

machines_config = MaquinaConfig.objects.all()

print(f"{'MANTENIMIENTO ACTIVOS (IDs)':<30}: {maquinas_en_reparacion}")
print("-" * 100)
print(f"{'NOMBRE':25} | {'ID':4} | {'STATUS':10} | {'REASON':30} | {'IDLE'}")
print("-" * 100)

for m in machines_config:
    mid = str(m.id_maquina).strip().upper()
    mname = str(m.nombre).strip().upper()
    data = kpi_lookup.get(mid) or kpi_lookup.get(mname)
    
    status = 'OFFLINE'
    reason = "---"
    idle = 0
    
    if m.id in maquinas_en_reparacion:
        status = 'REPAIR'
        reason = "MANTENIMIENTO"

    if data:
        reason = str(data.get('last_reason', '')).upper()
        idle = data.get('idle_mins', 999)
        is_effectively_online = data.get('is_online') or (idle < 60.0)
        
        repair_keywords = ['MANTEN', 'REPAR', 'CORRECTIVO', 'PREVENTIVO', 'FALLA', 'ROTURA']
        wait_keywords = ['HERRAMIENTA', 'AJUST', 'TENSI', 'CAPACI', 'CAPACIT', 'ESPERA', 'SET-UP', 'SETUP', 'LIMPIEZA', 'MATERIAL', 'ENSAYO', 'INSPEC', 'ASIST', 'AUXILIO']
        break_keywords = ['DESCANSO', 'ALMUERZO', 'PAUSA', 'REUNION', 'REUNIÓN', 'PERSONAL']
        
        # This is the logic in views.py
        if m.id in maquinas_en_reparacion or any(k in reason for k in repair_keywords):
            status = 'REPAIR'
        elif data.get('is_producing_now'):
            status = 'RUNNING'
        elif is_effectively_online:
            if any(k in reason for k in wait_keywords):
                status = 'WAIT'
            elif any(k in reason for k in break_keywords):
                status = 'BREAK'
            elif 'ONLINE' in reason:
                status = 'RUNNING'
            else:
                status = 'STOPPED'
        else:
            status = 'STOPPED'
            
    print(f"{m.nombre:25} | {m.id:4} | {status:10} | {reason:30} | {idle}")

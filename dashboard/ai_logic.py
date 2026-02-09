import datetime
import re
import requests
import json
from django.utils import timezone
from django.db.models import Sum, Q
from .models import VTMan, MaquinaConfig, OperarioConfig

# --- CONFIGURACION GEMINI ---
GEMINI_API_KEY = "AIzaSyDzCZm2WEnKKfdqUtNy2iA1J7K2a3kRPWA"
# --- CONFIGURACION GEMINI ---
GEMINI_API_KEY = "AIzaSyDzCZm2WEnKKfdqUtNy2iA1J7K2a3kRPWA"
# --- CONFIGURACION GEMINI ---
GEMINI_API_KEY = "AIzaSyDzCZm2WEnKKfdqUtNy2iA1J7K2a3kRPWA"
# --- CONFIGURACION GEMINI ---
GEMINI_API_KEY = "AIzaSyDzCZm2WEnKKfdqUtNy2iA1J7K2a3kRPWA"
# --- CONFIGURACION GEMINI ---
GEMINI_API_KEY = "AIzaSyDzCZm2WEnKKfdqUtNy2iA1J7K2a3kRPWA"
# --- CONFIGURACION GEMINI ---
GEMINI_API_KEY = "AIzaSyDzCZm2WEnKKfdqUtNy2iA1J7K2a3kRPWA"
# --- CONFIGURACION GEMINI ---
GEMINI_API_KEY = "AIzaSyDzCZm2WEnKKfdqUtNy2iA1J7K2a3kRPWA"
# --- CONFIGURACION GEMINI ---
GEMINI_API_KEY = "AIzaSyDzCZm2WEnKKfdqUtNy2iA1J7K2a3kRPWA"
# MODELO LISTADO DISPONIBLE: gemini-flash-latest (Alias para la versión Flash actual)
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={GEMINI_API_KEY}"

def call_gemini(prompt, image_b64=None):
    """
    Llama a la API REST de Gemini 1.5 Flash.
    """
    parts = [{"text": prompt}]
    
    if image_b64:
        # Extraer header si existe (e.g. "data:image/png;base64,")
        if "base64," in image_b64:
            image_b64 = image_b64.split("base64,")[1]
            
        parts.append({
            "inline_data": {
                "mime_type": "image/jpeg", # Asumimos jpeg o png, Gemini es flexible
                "data": image_b64
            }
        })

    payload = {
        "contents": [{
            "parts": parts
        }],
        "generationConfig": {
            "temperature": 0.4,
            "maxOutputTokens": 4096,
        }
    }
    
    try:
        response = requests.post(GEMINI_URL, headers={'Content-Type': 'application/json'}, json=payload, timeout=20)
        
        if response.status_code == 200:
            result = response.json()
            try:
                # Intentar ruta estándar
                if 'candidates' in result and len(result['candidates']) > 0:
                    candidate = result['candidates'][0]
                    if 'content' in candidate and 'parts' in candidate['content']:
                        return candidate['content']['parts'][0]['text']
                    
                    # Si no hay contenido, revisar finishReason
                    if 'finishReason' in candidate:
                        return f"Gemini se detuvo por: {candidate['finishReason']} (Posible bloqueo de seguridad o filtro)."
                
                # Si llegamos aquí, la estructura es válida pero vacía o inesperada
                return f"Respuesta vacía o inesperada de Gemini: <br><pre>{json.dumps(result, indent=2)}</pre>"
            except Exception as e:
                return f"Error procesando JSON: {str(e)} <br>Raw: {json.dumps(result)}"
        else:
            return f"Error HTTP {response.status_code}: {response.text}"
    except Exception as e:
        return f"Error de conexión: {str(e)}"

def get_ai_analysis(query, context_url="", image_data=None):
    """
    Cerebro Híbrido:
    1. Calcula métricas duras ("Hard Data") usando los algoritmos locales (analyze_day) para garantizar precisión 100%.
    2. Si hay imagen, o la pregunta es compleja, envía Hard Data + Pregunta + Imagen a Gemini.
    3. Gemini genera la respuesta en lenguaje natural basada en los datos reales.
    """
    query_lower = query.lower()
    today = timezone.localtime(timezone.now()).date()
    
    # 1. Detectar Contexto (Fecha y Máquina)
    date_target = today
    # ... (Lógica de fechas existente)
    date_match = re.search(r'(\d{1,2})[/-](\d{1,2})', query)
    if date_match:
        day, month = int(date_match.group(1)), int(date_match.group(2))
        try:
            date_target = datetime.date(today.year, month, day)
            if date_target > today: date_target = datetime.date(today.year - 1, month, day)
        except ValueError: pass
    elif 'ayer' in query_lower:
        date_target = today - datetime.timedelta(days=1)

    machine_target = None
    all_machines = MaquinaConfig.objects.filter(activa=True)
    for m in all_machines:
        if m.id_maquina.lower() in query_lower or m.nombre.lower() in query_lower:
            machine_target = m
            break

    # 2. Generar "Hard Data" (Contexto Oficial)
    # Ejecutamos las funciones locales que ya sincronizamos para obtener los números precisos
    hard_data_context = ""
    
    if machine_target:
        hard_data_context = analyze_machine(machine_target, date_target)
    elif "mantenimiento" in query_lower:
        hard_data_context = analyze_maintenance_context(date_target)
    else:
        # Default global
        hard_data_context = analyze_day(date_target)

    # Limpiar HTML del contexto para ahorrar tokens y no confundir a Gemini (opcional, pero ayuda)
    # Por ahora se lo pasamos raw, Gemini entiende bien.
    
    # 3. Decidir si usar Gemini o Respuesta Rápida
    # Si hay imagen, SIEMPRE usar Gemini
    # Si la pregunta es muy simple ("status"), podríamos devolver hard_data directo, 
    # PERO el usuario quiere "mayor entendimiento", asi que usaremos Gemini para enriquecer siempre que no sea un comando simple.
    
    use_gemini = True 
    
    if use_gemini:
        system_prompt = f"""
        Eres ABBAMAT AI, el auditor industrial experto de esta planta.
        
        TU CONTEXTO DE DATOS REALES (FUENTE DE VERDAD):
        {hard_data_context}
        
        FECHA DE HOY: {today.strftime('%d/%m/%Y')}
        
        INSTRUCCIONES CRÍTICAS DE PRIORIDAD:
        1. ANÁLISIS VISUAL PRIMERO: Si el usuario envía una imagen, ERES UN EXPERTO EN VISIÓN ARTIFICIAL.
           - Busca explícitamente FECHAS en la imagen. Si la imagen dice "07 Feb 2026", EL ANÁLISIS ES DE ESE DÍA, ignora la fecha de hoy.
           - Lee los números (OEE, Disponibilidad, Rendimiento) DIRECTAMENTE DE LA IMAGEN. Si difieren de tu "Contexto de Datos Reales", USA LOS DE LA IMAGEN (es lo que el usuario está viendo y preguntando).
        
        2. Si NO hay imagen, usa el "CONTEXTO DE DATOS REALES" como tu fuente de verdad absoluta.

        3. Responde a la pregunta del usuario: "{query}" dentro del contexto detectado (Visual o de Datos).
        
        4. Sé conciso, profesional y directo.
        """
        
        # Feedback visual de que está pensando (manejado en frontend, aquí solo procesamos)
        gemini_response = call_gemini(system_prompt, image_data)
        
        # Post-procesamiento ligero para convertir Markdown a HTML básico si es necesario, 
        # o confiamos en que el frontend renderice markdown (idealmente).
        # El frontend actual espera HTML básico (<br>, <b>).
        # Vamos a convertir saltos de línea a <br> y ** a <b> para compatibilidad legacy.
        
        formatted_response = gemini_response.replace('\n', '<br>').replace('**', '<b>').replace('##', '<br><b>')
        
        return formatted_response

    # Fallback legacy (no debería alcanzarse si use_gemini=True)
    return hard_data_context

def analyze_day(date_target):
    date_str = date_target.strftime('%Y-%m-%d')
    # IMPORTANTE: Ordenar por hora_inicio para correcta evaluacion de estado (Matriceria)
    qs = VTMan.objects.extra(where=["CONVERT(date, FECHA) = %s"], params=[date_str]).order_by('hora_inicio')
    
    if not qs.exists():
        return f"No hay datos registrados para el día {date_target.strftime('%d/%m/%y')}."

    # --- MÉTRICA SINCRONIZADA CON DASHBOARD_PRODUCCION ---
    # 1. Configuración de Máquinas (Identificar Activas e Inactivas)
    maquinas_configs = {}
    active_configs = []
    maquinas_inactivas_ids = set()
    
    try:
        all_configs = MaquinaConfig.objects.all()
        for conf in all_configs:
            maquinas_configs[conf.id_maquina] = conf
            if conf.activa:
                active_configs.append(conf)
            else:
                maquinas_inactivas_ids.add(conf.id_maquina)
    except: pass

    # 2. Cálculo de Disponibilidad Teórica (Horas Disponibles)
    total_horas_disp = 0.0
    
    # Determinar si es hoy para el cálculo de horas transcurridas
    is_today = (date_target == timezone.localtime(timezone.now()).date())
    now_dec = timezone.localtime(timezone.now()).hour + timezone.localtime(timezone.now()).minute/60.0
    
    for m in active_configs:
        weekday = date_target.weekday()
        works = True
        if weekday < 5: 
            s, e = m.horario_inicio_sem, m.horario_fin_sem
        elif weekday == 5:
            works, s, e = m.trabaja_sabado, m.horario_inicio_sab or datetime.time(7,0), m.horario_fin_sab or datetime.time(13,0)
        else:
            works, s, e = m.trabaja_domingo, m.horario_inicio_dom or datetime.time(7,0), m.horario_fin_dom or datetime.time(13,0)
            
        if works:
            s_dec = s.hour + s.minute/60.0
            e_dec = e.hour + e.minute/60.0
            full = e_dec - s_dec
            if is_today:
                # Si hoy ya paso el turno, sumar todo. Si no ha empezado, 0. Si esta en curso, lo que va.
                if now_dec < s_dec: pass
                elif now_dec > e_dec: total_horas_disp += full
                else: total_horas_disp += (now_dec - s_dec)
            else:
                total_horas_disp += full

    # 3. Datos Reales de VTMAN con lógica de Auditoría (Matricería y Descansos)
    descanso_keywords = ['DESCANSO', 'ALMUERZO', 'PAUSA', 'VACACIONES', 'LICENCIA']
    special_keywords = [
        'MATRICER', 'TAREAS GENERALES', 'AJUSTES', 'REBABADO', 'GRABADO', 'ARMADO',
        'CAPACI', 'CAPACIT', 'TENSI', 'TENSION', 'HERRAMIENTA', 'MANTEN', 'REPAR',
        'CORRECTIVO', 'PREVENTIVO', 'AJUST', 'SET-UP', 'SETUP', 'LIMPIEZA', 
        'REUNION', 'REUNIÓN', 'MATERIAL', 'ESPERA', 'ENSAYO', 'INSPEC', 'ASIST', 'AUXILIO'
    ]

    # Acumuladores Globales independientes
    # En views.py se usan acumuladores separados y luego se suman
    unassigned_time = 0.0
    unassigned_std = 0.0
    
    # Estado por máquina (Solo asignadas/activas) para seguimiento de Matricería
    machine_state = {} 
    
    # Inicializar estado para todas las activas (para asegurar que existen en el dict)
    for conf in active_configs:
        machine_state[conf.id_maquina] = {
            'prod_mins': 0.0,
            'std_mins': 0.0,
            'has_matriceria': False,
            'latest_obs': '' # Para lógica de persistencia visual, aunque aqui solo importa el cálculo
        }
        
    for r in qs:
        dur = r.tiempo_minutos or 0.0
        std = (r.tiempo_cotizado or 0.0) * 60.0
        obs = str(r.observaciones or "").upper()
        art = str(r.articulod or "").upper()
        oper = str(r.operacion or "").upper()
        mid = str(r.id_maquina).strip() if r.id_maquina else None
        
        is_descanso = any(k in obs for k in descanso_keywords) or any(k in art for k in descanso_keywords) or any(k in oper for k in descanso_keywords)
        is_ma = any(k in obs for k in special_keywords) or any(k in art for k in special_keywords) or any(k in oper for k in special_keywords)
        
        is_online_record = (obs == 'ONLINE')
        
        # Detectar si es "Sin Asignar"
        # views.py: is_unassigned = (not mid or mid in maquinas_inactivas_ids)
        is_unassigned = (not mid or mid in maquinas_inactivas_ids)
        if mid == 'MAC40': is_unassigned = False # NLX siempre asignada exception
        
        if is_unassigned:
            # Lógica Sin Asignar (views.py)
            # views.py suma TODO el tiempo a unassigned_time y TODO el std a unassigned_std
            unassigned_time += dur
            unassigned_std += std
                
        else:
            # Lógica Máquina Asignada
            if mid not in machine_state:
                # Si llega una maquina que no estaba en active_configs (pero no esta en inactivas? raro)
                # o si la logica de inactivas falló. Asumimos nueva entrada.
                machine_state[mid] = {
                    'prod_mins': 0.0,
                    'std_mins': 0.0,
                    'has_matriceria': False,
                    'latest_obs': ''
                }
            
            data = machine_state[mid]
            
            # Actualizar flag matriceria persistente
            if is_ma:
                data['has_matriceria'] = True
            
            # Filtro de Validez (views.py):
            # is_valid_machine_prod = not (is_descanso or reg['es_interrupcion'])
            # if is_valid_machine_prod...
            if not (is_descanso or r.es_interrupcion):
                data['prod_mins'] += dur
                
                # Std Logic
                should_treat_as_matriceria = is_ma or (data['has_matriceria'] and is_online_record)
                
                if should_treat_as_matriceria:
                    data['std_mins'] += dur # Std = Real
                else:
                    data['std_mins'] += std # Std = ERP

    # 4. Consolidación Final de KPIs
    
    # Sumar Asignadas
    total_assigned_prod = 0.0
    total_assigned_std = 0.0
    
    for mid, data in machine_state.items():
        total_assigned_prod += data['prod_mins']
        total_assigned_std += data['std_mins']
        
    # Convertir a Horas y Sumar Unassigned (como en views.py)
    # views.py: 
    #   h_unassigned_std = unassigned_std / 60.0
    #   h_unassigned_prod = unassigned_time / 60.0
    #   total_horas_std += h_unassigned_std
    #   total_horas_prod += h_unassigned_prod
    
    h_unassigned_prod = unassigned_time / 60.0
    h_unassigned_std = unassigned_std / 60.0
    
    h_assigned_prod = total_assigned_prod / 60.0
    h_assigned_std = total_assigned_std / 60.0
    
    h_prod = h_assigned_prod + h_unassigned_prod
    h_std = h_assigned_std + h_unassigned_std
    
    # CORRECCIÓN DE LÓGICA OEE (NORMALIZACIÓN AL 100% - CONSISTENCIA CON DASHBOARD):
    # Si hay producción en máquinas "Sin Asignar" (Inactivas o Viejas), debemos
    # sumar ese tiempo al DISPONIBLE también.
    if h_unassigned_prod > 0:
        total_horas_disp += h_unassigned_prod
    
    # Sincronización de OEE: (Std_Total / Disp_Total) * 100
    # OEE = (Horas Std / Horas Disp) * 100
    oee = (h_std / total_horas_disp * 100.0) if total_horas_disp > 0 else 0.0
    
    # Disponibilidad = (Horas Prod / Horas Disp) * 100
    avail = (h_prod / total_horas_disp * 100.0) if total_horas_disp > 0 else 0.0
    
    # Rendimiento = (Horas Std / Horas Prod) * 100
    perf = (h_std / h_prod * 100.0) if h_prod > 0 else 0.0

    resp = f"<b>ANÁLISIS GLOBAL - {date_target.strftime('%d/%m/%Y')}</b>:<br><br>"
    resp += f"• <b>OEE Planta:</b> <span class='text-amber-400 font-bold'>{oee:.2f}%</span><br>"
    resp += f"• <b>Disponibilidad:</b> {avail:.2f}% (Uso del tiempo)<br>"
    resp += f"• <b>Rendimiento:</b> {perf:.2f}% (Velocidad vs ERP)<br><br>"
    resp += f"• <b>Horas Estándar:</b> {h_std:.2f} hs<br>"
    resp += f"• <b>Horas Productivas:</b> {h_prod:.2f} hs<br>"
    resp += f"• <b>Horas Disponibles:</b> {total_horas_disp:.2f} hs<br><br>"
    
    if perf > 130:
        resp += "🔍 <b>Nota:</b> El OEE está alto debido a rendimientos excepcionales en algunas órdenes.<br>"
    
    return resp

def analyze_machine(m, date_target):
    date_str = date_target.strftime('%Y-%m-%d')
    qs = VTMan.objects.extra(where=["CONVERT(date, FECHA) = %s"], params=[date_str]).filter(id_maquina=m.id_maquina)
    
    if not qs.exists():
        return f"No tengo registros para <b>{m.nombre}</b> el {date_target.strftime('%d/%m/%Y')}."

    # Lógica de Auditoría (Matricería y Descansos)
    descanso_keywords = ['DESCANSO', 'ALMUERZO', 'PAUSA', 'VACACIONES', 'LICENCIA']
    special_keywords = [
        'MATRICER', 'TAREAS GENERALES', 'AJUSTES', 'REBABADO', 'GRABADO', 'ARMADO',
        'CAPACI', 'CAPACIT', 'TENSI', 'TENSION', 'HERRAMIENTA', 'MANTEN', 'REPAR',
        'CORRECTIVO', 'PREVENTIVO', 'AJUST', 'SET-UP', 'SETUP', 'LIMPIEZA', 
        'REUNION', 'REUNIÓN', 'MATERIAL', 'ESPERA', 'ENSAYO', 'INSPEC', 'ASIST', 'AUXILIO'
    ]

    total_std_mins = 0.0
    total_prod_mins = 0.0
    
    for r in qs:
        dur = r.tiempo_minutos or 0.0
        std = (r.tiempo_cotizado or 0.0) * 60.0
        obs_r = str(r.observaciones or "").upper()
        art_r = str(r.articulod or "").upper()
        oper_r = str(r.operacion or "").upper()
        
        is_desc = any(k in obs_r for k in descanso_keywords) or any(k in art_r for k in descanso_keywords) or any(k in oper_r for k in descanso_keywords)
        is_ma = any(k in obs_r for k in special_keywords) or any(k in art_r for k in special_keywords) or any(k in oper_r for k in special_keywords)
        
        if not (is_desc or r.es_interrupcion):
            total_prod_mins += dur
            if is_ma:
                total_std_mins += dur
            else:
                total_std_mins += std

    # Lógica de Disponibilidad Local
    weekday = date_target.weekday()
    if weekday < 5: s, e = m.horario_inicio_sem, m.horario_fin_sem
    elif weekday == 5: s, e = m.horario_inicio_sab or datetime.time(7,0), m.horario_fin_sab or datetime.time(13,0)
    else: s, e = m.horario_inicio_dom or datetime.time(7,0), m.horario_fin_dom or datetime.time(13,0)
    
    s_dec, e_dec = s.hour + s.minute/60.0, e.hour + e.minute/60.0
    disp_hrs = e_dec - s_dec
    
    if date_target == timezone.localtime(timezone.now()).date():
        now_dec = timezone.localtime(timezone.now()).hour + timezone.localtime(timezone.now()).minute/60.0
        if now_dec < s_dec: disp_hrs = 0.01
        elif now_dec < e_dec: disp_hrs = now_dec - s_dec

    avail = (total_prod_mins / (disp_hrs * 60) * 100.0) if disp_hrs > 0 else 0
    perf = (total_std_mins / total_prod_mins * 100.0) if total_prod_mins > 0 else 0
    oee = (min(100, avail) * min(300, perf)) / 100.0

    resp = f"<b>{m.nombre} ({m.id_maquina})</b> [{date_target.strftime('%d/%m/%y')}]:<br><br>"
    resp += f"• <b>OEE:</b> <span class='text-amber-400 font-bold'>{oee:.1f}%</span><br>"
    resp += f"• <b>Disponibilidad:</b> {avail:.1f}%<br>"
    resp += f"• <b>Rendimiento:</b> {perf:.1f}%<br>"
    return resp


def analyze_maintenance_context(date_target):
    from .models import Mantenimiento
    incidencias = Mantenimiento.objects.filter(fecha_reporte__date=date_target)
    cant = incidencias.count()
    if cant == 0: return f"Hoy no hay avisos de mantenimiento registrados."
    
    total_mins = incidencias.aggregate(s=Sum('duracion_minutos'))['s'] or 0
    resp = f"<b>MANTENIMIENTO ({date_target.strftime('%d/%m/%y')}):</b><br><br>"
    resp += f"• <b>Total Incidencias:</b> {cant}<br>"
    resp += f"• <b>Tiempo de parada:</b> {total_mins} min<br>"
    return resp

def analyze_bottlenecks(date_target):
    date_str = date_target.strftime('%Y-%m-%d')
    qs = VTMan.objects.extra(where=["CONVERT(date, FECHA) = %s"], params=[date_str]).filter(es_interrupcion=False)
    machine_data = qs.values('id_maquina').annotate(real=Sum('tiempo_minutos'), std=Sum('tiempo_cotizado'))
    bottlenecks = []
    for m in machine_data:
        m_perf = ((m['std'] or 0) * 60 / (m['real'] or 1) * 100)
        if m_perf < 80 and m['real'] > 30: bottlenecks.append({'id': m['id_maquina'], 'perf': m_perf})
    if not bottlenecks: return "No hay cuellos de botella críticos hoy."
    bottlenecks = sorted(bottlenecks, key=lambda x: x['perf'])[:3]
    resp = "<b>CUELLOS DE BOTELLA:</b><br>"
    for b in bottlenecks:
        m_name = b['id']
        try: m_name = MaquinaConfig.objects.get(id_maquina=b['id']).nombre
        except: pass
        resp += f"• <b>{m_name}:</b> {b['perf']:.1f}% rendimiento.<br>"
    return resp

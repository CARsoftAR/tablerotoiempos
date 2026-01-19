import json
import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Sum, Q, F, Count, Max
from django.utils import timezone
from datetime import timedelta
from .models import VTMan, Maquina, MaquinaConfig, OperarioConfig, Mantenimiento, AuditLog
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.template.loader import get_template
from xhtml2pdf import pisa


def dashboard_produccion(request, return_context=False, force_date=None, force_start=None, force_end=None, force_format=None):
    # Rango de fechas: HOY (para ver estado en tiempo real)
    # Rango de fechas: HOY
    # Lógica de Fecha:
    # 1. Si el usuario pide fecha específica, usarla.
    # 2. Si no, buscar hacia atrás desde AYER el primer día con datos (Max 15 días).
    #    (Requisito usuario: "consultar siempre al dia anterior... si ayer no se trabajó... fijarte el anterior")
    
    import datetime
    from dateutil import parser
    
    # Manejo de Formato de Tiempo (Decimal vs Reloj)
    time_format = request.GET.get('format')
    if time_format:
        request.session['time_format'] = time_format
    else:
        time_format = request.session.get('time_format', 'clock')

    if force_format:
        time_format = force_format

    is_tv_mode = request.GET.get('mode') == 'tv'
    if is_tv_mode:
        request.session['is_tv_mode'] = True
    elif 'mode' in request.GET: # Si viene mode=normal o similar
        request.session['is_tv_mode'] = False
    
    is_tv_mode = request.session.get('is_tv_mode', False)

    if force_date:
        fecha_param = str(force_date)
    else:
        fecha_param = request.GET.get('date') or request.GET.get('fecha')
        
    start_param = force_start or request.GET.get('start_date')
    end_param = force_end or request.GET.get('end_date')

    now_local = timezone.localtime(timezone.now())
    today_date = now_local.date()
    
    fecha_target_start = None
    fecha_target_end = None
    view_type = request.GET.get('view', 'machines')
    is_viewing_today = False

    if start_param and end_param:
        try:
            fecha_target_start = parser.parse(start_param).date()
            fecha_target_end = parser.parse(end_param).date()
            is_viewing_today = (fecha_target_start == fecha_target_end == today_date)
        except:
            fecha_param = 'today' # Fallback

    if not fecha_target_start:
        found_date = None
        if fecha_param:
            if fecha_param == 'yesterday':
                if today_date.weekday() == 0:
                    found_date = today_date - datetime.timedelta(days=2)
                else:
                    found_date = today_date - datetime.timedelta(days=1)
            elif fecha_param == 'today':
                found_date = today_date
            else:
                try:
                    found_date = parser.parse(fecha_param).date()
                except:
                    found_date = today_date - datetime.timedelta(days=1)
        else:
            # BÚSQUEDA AUTOMÁTICA: Empezar desde HOY, si no hay datos ir hacia atrás.
            check_date = today_date
            for _ in range(15): 
                if check_date.weekday() == 6: check_date -= datetime.timedelta(days=1)
                c_start = timezone.make_aware(datetime.datetime.combine(check_date, datetime.time.min), datetime.timezone.utc)
                c_end = timezone.make_aware(datetime.datetime.combine(check_date, datetime.time.max), datetime.timezone.utc)
                if VTMan.objects.filter(fecha__range=(c_start, c_end)).exists():
                    found_date = check_date
                    break
                check_date -= datetime.timedelta(days=1)
            if not found_date: found_date = today_date - datetime.timedelta(days=1)
        
        fecha_target_start = found_date
        fecha_target_end = found_date
        is_viewing_today = (fecha_target_start == today_date)

    # RANGO DE CONSULTA UTC
    fecha_inicio_utc = timezone.make_aware(datetime.datetime.combine(fecha_target_start, datetime.time.min), datetime.timezone.utc)
    fecha_fin_utc = timezone.make_aware(datetime.datetime.combine(fecha_target_end, datetime.time.max), datetime.timezone.utc)
    
    # 1. Obtener nombres y configs
    maquinas_db = Maquina.objects.all()
    nombres_maquinas = {m.id_maquina: m.descripcion for m in maquinas_db}
    maquinas_inactivas_ids = set()
    maquinas_configs = {} 
    try:
        configs_locales = MaquinaConfig.objects.all()
        for conf in configs_locales:
            nombres_maquinas[conf.id_maquina] = conf.nombre
            maquinas_configs[conf.id_maquina] = conf
            if not conf.activa: maquinas_inactivas_ids.add(conf.id_maquina)
    except: pass 

    # 1.5 Obtener nombres y configuración de operarios
    nombres_operarios = {}
    operarios_activos_ids = set()
    try:
        operarios_db = OperarioConfig.objects.all()
        for o in operarios_db:
            nombres_operarios[o.legajo] = o.nombre
            if o.activo and o.sector == 'PRODUCCION':
                operarios_activos_ids.add(o.legajo)
    except: pass

    # 1.6 Obtener estados de mantenimiento ACTIVOS DURANTE EL PERIODO (MySQL)
    # Una falla es relevante si: empezó antes que termine el día Y (no terminó o terminó después que empiece el día)
    mantenimientos_periodo = Mantenimiento.objects.filter(
        fecha_reporte__lte=fecha_fin_utc
    ).exclude(
        estado='CERRADO', fecha_fin__lt=fecha_inicio_utc
    ).select_related('maquina')
    
    maquina_mantenimiento = {} # {id_maquina: {estado, tipo, tecnico}}
    for m in mantenimientos_periodo:
        # Si estamos viendo HOY (tiempo real), ignoramos las incidencias que ya se cerraron.
        # Solo queremos que el tablero parpadee si la máquina está rota AHORA.
        if is_viewing_today and m.estado == 'CERRADO':
            continue

        maquina_mantenimiento[m.maquina.id_maquina] = {
            'estado': m.estado,
            'estado_display': m.get_estado_display(),
            'tipo': m.tipo,
            'tecnico': m.tecnico_asignado
        }

    fecha_str = fecha_target_start.strftime('%Y-%m-%d')

    # OPTIMIZACIÓN DE QUERY (RANGO DE FECHAS)
    # Reemplazamos CONVERT(date, FECHA) que prevenía el uso de índices (Full Table Scan)
    # por un filtro de rango nativo.
    # Usamos datetime naive para que Django no convierta la zona horaria y busque "literalmente" en la DB
    # tal como están guardados los registros (similar a lo que hacía el CONVERT).
    f_start_naive = datetime.datetime.combine(fecha_target_start, datetime.time.min)
    f_end_naive = datetime.datetime.combine(fecha_target_end, datetime.time.max)

    # Usamos CONVERT para asegurar coincidencia total con la lógica de auditoría
    # Esto evita problemas de Timezone donde fecha__range corta registros de la tarde/noche
    start_str = fecha_target_start.strftime('%Y-%m-%d')
    end_str = fecha_target_end.strftime('%Y-%m-%d')
    
    registros_data = VTMan.objects.extra(
        where=["CONVERT(date, FECHA) >= %s AND CONVERT(date, FECHA) <= %s"],
        params=[start_str, end_str]
    ).order_by('hora_inicio').values(
        'id_maquina', 'tiempo_minutos', 'tiempo_cotizado', 'cantidad_producida',
        'es_proceso', 'es_interrupcion', 'observaciones', 'fecha', 'id_orden', 'operacion',
        'articulod', 'id_operacion', 'op_usuario', 'id_concepto', 'hora_inicio', 'hora_fin'
    )

    kpi_por_maquina = {}
    actual_online_ids = set()
    if is_viewing_today:
        online_qs = VTMan.objects.filter(
            fecha__range=(f_start_naive, f_end_naive),
            observaciones='ONLINE'
        ).values_list('id_maquina', flat=True)
        actual_online_ids = set(online_qs)

    # Pre-inicializar TODAS las máquinas configuradas y activas
    for mid, conf in maquinas_configs.items():
        if conf.activa:
            kpi_por_maquina[mid] = {
                'id_maquina': mid,
                'nombre_maquina': conf.nombre,
                'tiempo_operativo': 0.0,
                'tiempo_paradas': 0.0,
                'tiempo_cotizado': 0.0,
                'cantidad_producida': 0.0,
                'cantidad_rechazada': 0.0,
                'latest_obs': '',
                'latest_date': None,
                'latest_activity_time': None,
                'latest_operator': 'S/A',
                'latest_article': '---',
                'current_order': '---',
                'is_found_online': False,
                'audit_log': []
            }

    # Acumuladores Globales
    unassigned_time = 0.0
    unassigned_qty = 0.0
    unassigned_std = 0.0
    unassigned_interruption_time = 0.0
    unassigned_process_time = 0.0

    global_planned_time = 0.0 
    global_actual_time = 0.0 
    global_downtime = 0.0
    global_actual_qty = 0.0 # Piezas Buenas
    global_rejected_qty = 0.0 # Reprocesos/Scrap
    global_repro_time = 0.0 # Horas de reproceso

    machine_orders = {} 
    kpi_por_personal = {}
    
    # Acumuladores Globales

    for reg in registros_data:
        mid = reg['id_maquina']
        duracion = reg['tiempo_minutos'] or 0.0
        qty = reg['cantidad_producida'] or 0.0
        std_mins = (reg['tiempo_cotizado'] or 0.0) * 60.0
        
        # Identificar Reproceso o tareas que no deben sumar a Cantidad Real
        raw_id_op = str(reg.get('id_operacion') or "").strip().upper()
        raw_art_d = str(reg.get('articulod') or "").strip().upper()
        raw_op_d = str(reg.get('operacion') or "").strip().upper()
        raw_obs = str(reg.get('observaciones') or "").strip().upper()

        non_prod_keywords = ['REPROCESO', 'RETRABAJO']
        descanso_keywords = ['DESCANSO', 'ALMUERZO', 'PAUSA']
        
        is_repro = (
            raw_id_op in non_prod_keywords or 
            raw_op_d in non_prod_keywords or
            any(k in raw_art_d for k in non_prod_keywords) or
            any(k in raw_obs for k in non_prod_keywords)
        )

        is_descanso = (
            raw_op_d in descanso_keywords or
            any(k in raw_art_d for k in descanso_keywords) or
            any(k in raw_obs for k in descanso_keywords)
        )
        
        # El 'ONLINE' a veces trae cantidad 1 para marcar actividad, pero no es producción real terminada
        is_online_record = (raw_obs == 'ONLINE')

        # Lógica especial para MATRICERÍA, TAREAS GENERALES y TAREAS MANUALES (Ajustes, Rebabado, etc.)
        # El estándar en estas tareas suele ser nulo en el ERP, así que las tratamos como 100% eficientes.
        raw_clean = str(reg.get('articulod') or "").upper() + " " + str(reg.get('operacion') or "").upper()
        special_keywords = ['MATRICER', 'TAREAS GENERALES', 'AJUSTES', 'REBABADO', 'GRABADO']
        is_matriceria = any(k in raw_clean for k in special_keywords)
        is_armado = ('ARMADO' in raw_clean) and not is_matriceria
        
        id_orden = reg.get('id_orden')
        
        add_std_global = True

        # 1. Caso: Sin Asignar (Máquina vacía o inactiva)
        is_unassigned = (not mid or mid in maquinas_inactivas_ids)
        
        if is_unassigned:
            unassigned_time += duracion
            if reg['es_proceso']:
                unassigned_process_time += duracion
            elif reg['es_interrupcion']:
                unassigned_interruption_time += duracion

            if is_repro:
                global_rejected_qty += qty
                global_repro_time += duracion
            else:
                unassigned_qty += qty
                global_actual_qty += qty
                if add_std_global:
                    unassigned_std += std_mins
        
        # 2. Caso: Máquina Asignada (Solo si no es unassigned)
        data = None
        if not is_unassigned:
            if mid not in kpi_por_maquina:
                kpi_por_maquina[mid] = {
                    'id_maquina': mid,
                    'nombre_maquina': nombres_maquinas.get(mid, mid),
                    'tiempo_operativo': 0.0, 
                    'tiempo_paradas': 0.0,
                    'tiempo_cotizado': 0.0, 
                    'cantidad_producida': 0.0,
                    'cantidad_rechazada': 0.0,
                    'latest_obs': '',
                    'latest_date': None,
                    'current_order': '---',
                    'is_found_online': False,
                    'audit_log': []
                }

            data = kpi_por_maquina[mid]
            
            # Tracking de última actividad real
            act_time = reg.get('hora_fin') or reg.get('hora_inicio') or reg.get('fecha')
            if not data['latest_activity_time'] or (act_time and data['latest_activity_time'] and act_time > data['latest_activity_time']):
                data['latest_activity_time'] = act_time
                if reg['observaciones']:
                    data['latest_obs'] = str(reg['observaciones']).strip().upper()
                data['latest_date'] = reg['fecha']
                data['current_order'] = reg['id_orden']
            
            # Siempre guardamos el último operario y artículo visto (ya que viene ordenado por hora_inicio)
            uid = str(reg.get('id_concepto') or '').strip()
            if uid:
                data['latest_operator'] = nombres_operarios.get(uid, f"Operario {uid}")
            
            art_desc = str(reg.get('articulod') or "").strip().upper()
            if art_desc:
                data['latest_article'] = art_desc

            if is_repro:
                data['cantidad_rechazada'] += qty
                global_rejected_qty += qty
                global_repro_time += duracion
            elif is_descanso:
                # El descanso NO suma cantidad ni tiempo cotizado
                pass
            else:
                data['cantidad_producida'] += qty
                global_actual_qty += qty
                
                # REGLA OEE MATRICERÍA: En trabajos de larga duración, tratamos la matricería como 100% eficiente (Estándar = Real).
                added_row_std = False
                art_name_m = str(reg.get('articulod') or "").strip().upper()
                if is_matriceria:
                    val_std = duracion
                    data['tiempo_cotizado'] += val_std
                    global_planned_time += val_std
                    added_row_std = True
                else:
                    # Para trabajos de SERIE (incluido ARMADO): Sumamos el estándar del ERP.
                    # El usuario dice que para Armado la cantidad siempre es 1 (para cálculo de std).
                    if qty > 0 or (is_armado and std_mins > 0):
                        val_std = std_mins
                        data['tiempo_cotizado'] += val_std
                        if add_std_global:
                            global_planned_time += val_std
                        added_row_std = True
            
            # Cálculo de Tiempos
            if is_descanso or reg['es_interrupcion']:
                # El descanso y las interrupciones declaradas se cuentan como Parada
                data['tiempo_paradas'] += duracion
                global_downtime += duracion
            else:
                # Si no es parada explícita, se considera tiempo operativo de máquina
                data['tiempo_operativo'] += duracion
                global_actual_time += duracion

        # --- Lógica por Personal ---
        # ATENCIÓN: En este ERP, el ID de la persona (legajo) viene en 'id_concepto',
        # mientras que 'op_usuario' es la persona que cargó la orden (supervisor/administración).
        uid = str(reg.get('id_concepto') or '').strip()
        if not uid or uid == 'None':
            uid = 'SIN IDENTIFICAR'
            
        if uid not in kpi_por_personal:
            kpi_por_personal[uid] = {
                'id_personal': uid,
                'nombre_personal': nombres_operarios.get(uid, f"Operario {uid}"),
                'tiempo_operativo': 0.0,
                'tiempo_paradas': 0.0,
                'tiempo_cotizado': 0.0,
                'cantidad_producida': 0.0,
                'cantidad_rechazada': 0.0,
                'latest_obs': '',
                'latest_machine': '',
                'current_order': '',
                'articulos': {}, # { nombre: {qty, std} }
                'descanso_mins': 0.0,
                'descanso_qty': 0.0,
                'latest_article': '---',
                'has_matriceria': False,
                'has_any_obs': False,
                'audit_log': []
            }
        
        per = kpi_por_personal[uid]
        obs_val = str(reg.get('observaciones') or "").strip()
        reg_time = reg.get('hora_inicio') or reg.get('fecha')

        # Actualizar lo más reciente (que no sea descanso)
        if not is_descanso:
            if not per.get('max_time') or (reg_time and per['max_time'] and reg_time >= per['max_time']):
                per['max_time'] = reg_time
                per['latest_obs'] = (obs_val or "ONLINE").strip().upper()
                per['latest_machine'] = mid or per.get('latest_machine', '')
                per['current_order'] = reg['id_orden']
                # Fallback: si no hay artículo, usamos el nombre de la operación
                art_d = (str(reg.get('articulod') or "").strip() or str(reg.get('operacion') or "").strip()).upper()
                if art_d:
                    per['latest_article'] = art_d
            elif not per.get('max_time'): # Si es el primero que vemos
                per['max_time'] = reg_time
                per['latest_obs'] = (obs_val or "ONLINE").strip().upper()
                per['latest_machine'] = mid or per.get('latest_machine', '')
                art_d = (str(reg.get('articulod') or "").strip() or str(reg.get('operacion') or "").strip()).upper()
                if art_d:
                    per['latest_article'] = art_d
                per['current_order'] = reg['id_orden']
        elif not per.get('latest_obs'):
            # Si solo hay descansos por ahora, guardamos uno como fallback pero seguimos buscando
            per['latest_obs'] = (obs_val or str(reg['articulod'] or "")).strip().upper()
            per['latest_machine'] = mid
            per['current_order'] = reg['id_orden']
        
        if obs_val:
            per['has_any_obs'] = True

        h_inicio = reg.get('hora_inicio')
        h_fin = reg.get('hora_fin')
        intervalo = "--:--"
        if h_inicio:
            intervalo = h_inicio.strftime('%H:%M')
            if h_fin:
                intervalo += f" - {h_fin.strftime('%H:%M')}"

        # Guardar en log (con fecha real para ordenar luego)
        log_entry = {
            'fecha_dt': reg_time,
            'fecha': intervalo,
            'maquina': mid or 'S/A',
            'orden': reg['id_orden'] or '---',
            'articulo': reg['articulod'][:30] if reg['articulod'] else 'Sin Artículo',
            'tiempo': round(duracion, 1),
            'std': round(std_mins, 1),
            'cant': round(qty, 1),
            'es_interrupcion': reg['es_interrupcion'] or is_descanso,
            'obs': reg['observaciones'] or ''
        }
        if data:
            data['audit_log'].append(log_entry)
        per['audit_log'].append(log_entry)
        
        upers = kpi_por_personal[uid]
        if is_repro:
            upers['cantidad_rechazada'] += qty
        elif is_descanso:
            # No suma cantidad
            pass
        else:
            upers['cantidad_producida'] += qty
            
            # REGLA OEE MATRICERÍA para Personal
            added_row_std_p = False
            art_name_p = str(reg.get('articulod') or "").strip().upper()
            if is_matriceria:
                upers['has_matriceria'] = True
                upers['tiempo_cotizado'] += duracion
                added_row_std_p = True
            else:
                # Trabajos normales: Sumar estándar si hay piezas (o si es Armado con estándar)
                if qty > 0 or (is_armado and std_mins > 0):
                    upers['tiempo_cotizado'] += std_mins
                    added_row_std_p = True
        
        if is_descanso:
            upers['tiempo_paradas'] += duracion
            upers['descanso_mins'] += duracion
            upers['descanso_qty'] += qty
        elif reg['es_interrupcion']:
            upers['tiempo_paradas'] += duracion
        else:
            # Es TIEMPO OPERATIVO (Proceso o similar que no es parada)
            upers['tiempo_operativo'] += duracion
            # Sumar al detalle de artículos (para el total final que vea en el análisis)
            art_name = str(reg.get('articulod') or "Sin Artículo").strip().upper()
            if art_name not in upers['articulos']:
                upers['articulos'][art_name] = {'qty': 0.0, 'std': 0.0}
            upers['articulos'][art_name]['qty'] += qty
            
            # Agregamos al desglose solo lo que sumó al KPI para que sea consistente
            if added_row_std_p:
                if is_matriceria:
                    upers['articulos'][art_name]['std'] += duracion
                else:
                    upers['articulos'][art_name]['std'] += std_mins

    # 3. Calcular KPIs finales
    lista_kpis = []
    now = timezone.now()
    total_horas_std = 0.0
    total_horas_prod = 0.0
    total_horas_disp = 0.0

    # Determinar los días del periodo
    delta = fecha_target_end - fecha_target_start
    dias_periodo = [fecha_target_start + datetime.timedelta(days=i) for i in range(delta.days + 1)]

    for mid, data in kpi_por_maquina.items():
        t_op_hrs = data['tiempo_operativo'] / 60.0
        t_std_hrs = data['tiempo_cotizado'] / 60.0
        qty = data['cantidad_producida']
        
        config = maquinas_configs.get(mid)
        t_disp_periodo = 0.0

        for d in dias_periodo:
            weekday = d.weekday()
            start_time = datetime.time(7, 0)
            end_time = datetime.time(16, 0)
            works_today = True
            
            if config:
                if weekday < 5: 
                    start_time = config.horario_inicio_sem
                    end_time = config.horario_fin_sem
                elif weekday == 5: # Sabado
                    works_today = config.trabaja_sabado
                    start_time = config.horario_inicio_sab or datetime.time(7,0)
                    end_time = config.horario_fin_sab or datetime.time(13,0)
                else: # Domingo
                    works_today = config.trabaja_domingo
                    start_time = config.horario_inicio_dom or datetime.time(7,0)
                    end_time = config.horario_fin_dom or datetime.time(13,0)
            
            if works_today:
                def time_to_decimal(t): return t.hour + t.minute/60.0
                start_dec = time_to_decimal(start_time)
                end_dec = time_to_decimal(end_time)
                if end_dec < start_dec: end_dec += 24.0 
                full_shift_hrs = end_dec - start_dec
                
                if is_viewing_today and d == today_date:
                    now_local = timezone.localtime(now)
                    now_dec_local = now_local.hour + now_local.minute/60.0
                    if now_dec_local < start_dec: t_disp_periodo += 0.0
                    elif now_dec_local > end_dec: t_disp_periodo += full_shift_hrs
                    else: t_disp_periodo += (now_dec_local - start_dec)
                else:
                    t_disp_periodo += full_shift_hrs

        if t_disp_periodo < t_op_hrs:
            t_disp_periodo = t_op_hrs
        if t_disp_periodo < 0.01:
            t_disp_periodo = 0.01

        # KPIs
        availability = (t_op_hrs / t_disp_periodo) * 100.0
        performance = (t_std_hrs / t_op_hrs) * 100.0 if t_op_hrs > 0 else 0.0
        total_p = qty + data['cantidad_rechazada']
        quality = (qty / total_p * 100.0) if total_p > 0 else 100.0
        oee = (availability * performance * quality) / 10000.0
        
        # Estado
        is_online = (mid in actual_online_ids) if is_viewing_today else False

        # Modificamos la función de formato para que use decimal si así se pide
        def format_time_display(hours_val):
            if time_format == 'decimal':
                return f"{hours_val:.2f}"
            
            total_minutes = hours_val * 60
            h = int(total_minutes // 60)
            m = int(round(total_minutes % 60))
            if m == 60: h += 1; m = 0
            if h > 0:
                return f"{h} hs {m} min"
            else:
                return f"{m} min"

        # Preparar log para serializar SIN modificar el original (porque se comparte con personal)
        serializable_log = []
        for entry in data['audit_log']:
            copy_entry = entry.copy()
            copy_entry.pop('fecha_dt', None)
            serializable_log.append(copy_entry)

        # Ordenar log por fecha (usando los originales que si tienen fecha_dt)
        sorted_log = sorted(serializable_log, key=lambda x: data['audit_log'][serializable_log.index(x)]['fecha_dt'] if data['audit_log'][serializable_log.index(x)]['fecha_dt'] else datetime.datetime.min)
        
        # Simplificamos: Ordenamos el original y sacamos copia limpia
        temp_sorted = sorted(data['audit_log'], key=lambda x: x['fecha_dt'] if x['fecha_dt'] else datetime.datetime.min)
        clean_log = []
        for entry in temp_sorted:
            c = entry.copy()
            c.pop('fecha_dt', None)
            clean_log.append(c)

        idle_mins = 0
        if is_viewing_today and data['latest_activity_time']:
            l_act = data['latest_activity_time']
            # Corrección de Zona Horaria (FIX DEFINITIVO v2):
            # El usuario ve "180 MIN INACTIVO" constantemente.
            # Esto indica que el registro de la DB (l_act) está 3 horas ATRÁS de la hora actual (Wall Clock).
            # Ejemplo: Ahora es 10:55. DB dice 07:55. Diferencia = 3h (180 min).
            # Solución: Asumimos que la DB guarda en UTC naive o con delay de zona.
            # Le SUMAMOS 3 horas a la fecha de la DB para traerla a la hora Argentina.
            
            now_local = timezone.localtime(timezone.now()).replace(tzinfo=None)
            
            if timezone.is_aware(l_act):
                l_act = timezone.make_naive(l_act)
            
            # Compensación del Offset de 3 horas
            l_act_adjusted = l_act + datetime.timedelta(hours=3)
            
            diff = now_local - l_act_adjusted
            idle_mins = max(0, diff.total_seconds() / 60.0)

        lista_kpis.append({
            'id': mid,
            'name': data['nombre_maquina'],
            'is_online': is_online,
            'oee': round(oee, 2),
            'availability': round(availability, 2),
            'performance': round(performance, 2),
            'quality': round(quality, 2),
            'id_orden': data['current_order'],
            'horas_std': t_std_hrs,
            'horas_prod': t_op_hrs,
            'actual_qty': data['cantidad_producida'],
            'rejected_qty': data['cantidad_rechazada'],
            'actual_time_formatted': format_time_display(t_op_hrs),
            'standard_time_formatted': format_time_display(t_std_hrs),
            'last_reason': data['latest_obs'],
            'operator_name': data['latest_operator'],
            'article_desc': data['latest_article'],
            'mantenimiento': maquina_mantenimiento.get(mid),
            'last_machine': None,
            'latest_date': data['latest_date'],
            'current_order': data['current_order'],
            'is_active_production': t_op_hrs > 0.001,
            'idle_mins': round(idle_mins, 1),
            'audit_log': json.dumps(clean_log)
        })
        
        total_horas_std += t_std_hrs
        total_horas_prod += t_op_hrs
        total_horas_disp += t_disp_periodo 
        global_downtime += max(0, (t_disp_periodo - t_op_hrs) * 60)

    # 4. Calcular KPIs finales por Personal
    lista_kpis_personal = []
    total_hrs_std_p = 0.0
    total_hrs_prod_p = 0.0
    total_hrs_disp_p = 0.0

    count_p = len(dias_periodo)
    for uid, data in kpi_por_personal.items():
        t_op_hrs = data['tiempo_operativo'] / 60.0
        t_std_hrs = data['tiempo_cotizado'] / 60.0
        qty = data['cantidad_producida']
        
        # Turno promedio para personal (9hs por día trabajado o del periodo)
        # Para hoy, usamos el tiempo transcurrido del turno para que el OEE sea real
        t_disp_p = 0.0
        for d in dias_periodo:
            start_h = 7.0 # Default start 07:00
            end_h = 16.0  # Default end 16:00 (9hs shift)
            
            if is_viewing_today and d == today_date:
                now_local = timezone.localtime(now)
                now_dec = now_local.hour + now_local.minute/60.0
                if now_dec < start_h: t_disp_p += 0.0
                elif now_dec > end_h: t_disp_p += (end_h - start_h)
                else: t_disp_p += (now_dec - start_h)
            else:
                t_disp_p += (end_h - start_h)
        
        if t_disp_p < t_op_hrs: t_disp_p = t_op_hrs
        if t_disp_p < 0.01: t_disp_p = 0.01
        
        availability = (t_op_hrs / t_disp_p) * 100.0 if t_disp_p > 0 else 0.0
        performance = (t_std_hrs / t_op_hrs) * 100.0 if t_op_hrs > 0 else 0.0
        total_p = qty + data['cantidad_rechazada']
        quality = (qty / total_p * 100.0) if total_p > 0 else 100.0
        oee = (availability * performance * quality) / 10000.0

        def format_time_display(hours_val):
            if time_format == 'decimal': return f"{hours_val:.2f}"
            total_minutes = hours_val * 60
            h = int(total_minutes // 60)
            m = int(round(total_minutes % 60))
            if m == 60: h += 1; m = 0
            if h > 0:
                return f"{h} hs {m} min"
            else:
                return f"{m} min"

        # FILTRADO: Solo mostrar personal activo y de producción
        if uid not in operarios_activos_ids:
            continue

        # Ordenar log por fecha y sacar copia limpia (para no romper logs compartidos ni dar KeyError)
        temp_sorted_p = sorted(data['audit_log'], key=lambda x: x['fecha_dt'] if x.get('fecha_dt') else datetime.datetime.min)
        clean_log_p = []
        for entry in temp_sorted_p:
            c = entry.copy()
            c.pop('fecha_dt', None)
            clean_log_p.append(c)

        # Cálculo de desviaciones
        factor_velocidad = (t_op_hrs / t_std_hrs) if t_std_hrs > 0.001 else 0

        # Generar Resumen de Análisis
        art_summary = []
        for a_name, a_data in data['articulos'].items():
            std_per_unit_mins = (a_data['std'] / a_data['qty']) if a_data['qty'] > 0 else 0
            art_summary.append(f"• {a_data['qty']:.1f} unidades de '{a_name}' (Estándar: {std_per_unit_mins:.2f} min/pz)")

        analysis_text = f"<span class='report-main-title'>DIAGNÓSTICO DETALLADO: {data['nombre_personal']}</span>\n\n"
        
        analysis_text += f"<span class='text-indigo-400 font-bold'>1. VERIFICACIÓN DE TIEMPOS (TABLERO VS ERP):</span>\n"
        analysis_text += f"    • <span class='text-slate-200'>Tiempo Estándar:</span> <span class='text-white font-bold'>{t_std_hrs:.2f} hs</span> (Total acumulado por piezas).\n"
        analysis_text += f"    • <span class='text-slate-200'>Tiempo Real (Operativo):</span> <span class='text-white font-bold'>{t_op_hrs:.2f} hs</span> (Tiempo frente a máquina).\n"
        analysis_text += f"    • <span class='text-slate-200'>Tiempo Fichado (Turno):</span> <span class='text-white font-bold'>{t_disp_p:.2f} hs</span> (Base de cálculo de disponibilidad).\n\n"

        analysis_text += f"<span class='text-indigo-400 font-bold'>2. CÁLCULO DE LA EFICIENCIA ({oee:.1f}%):</span>\n"
        analysis_text += f"    El sistema cruza la Disponibilidad y el Rendimiento:\n"
        analysis_text += f"    • <span class='text-emerald-400 font-bold'>Disponibilidad ({availability:.1f}%):</span> Resulta de {t_op_hrs:.2f} hrs trabajadas / {t_disp_p:.2f} hrs de turno.\n"
        analysis_text += f"    • <span class='text-emerald-400 font-bold'>Rendimiento ({performance:.1f}%):</span> Resulta de {t_std_hrs:.2f} hrs estándar / {t_op_hrs:.2f} hrs reales.\n"
        analysis_text += f"    • <span class='text-emerald-400 font-bold'>Eficiencia Final (OEE):</span> {availability:.1f}% x {performance:.1f}% = <span class='text-emerald-400 font-bold'>{oee:.1f}%</span>.\n\n"

        # --- SECCIÓN EXPLICATIVA SOLICITADA ---
        analysis_text += f"<span class='text-indigo-400 font-bold'>3. ¿POR QUÉ ESTE VALOR ES EL CORRECTO?</span>\n"
        analysis_text += f"    El sistema analiza el comportamiento de {data['nombre_personal']}:\n"
        
        if data.get('has_matriceria'):
            analysis_text += f"    • <span class='text-sky-300 font-bold'>Matricería (Neutral):</span> Detectamos registros de Matricería. En estas tareas, la eficiencia se fija en 100% (tiempo estándar = tiempo real) para no inflar el OEE con trabajos de larga duración, contando como tiempo cumplido.\n"
        else:
            analysis_text += f"    • <span class='text-slate-400'>Matricería:</span> No se detectaron trabajos de matricería en este periodo.\n"

        if performance > 105:
            analysis_text += f"    • <span class='text-emerald-400 font-bold'>Producción (Alto Rendimiento):</span> El operario está trabajando significativamente más rápido que el estándar del ERP para las piezas en serie, lo que eleva su Rendimiento al {performance:.1f}%.\n"
        elif performance < 80 and t_std_hrs > 0:
            analysis_text += f"    • <span class='text-amber-400 font-bold'>Producción (Bajo Rendimiento):</span> El tiempo reportado excede el estándar teórico del ERP para las piezas producidas.\n"
        else:
            analysis_text += f"    • <span class='text-sky-300 font-bold'>Producción (Normal):</span> El ritmo de trabajo se encuentra dentro de los parámetros esperados según los estándares del ERP.\n"

        if is_viewing_today:
             analysis_text += f"    • <span class='text-indigo-300 font-bold'>Disponibilidad Inteligente:</span> Al ser 'Hoy', el cálculo de disponibilidad se ajusta automáticamente al tiempo transcurrido desde el inicio del turno (07:00). Esto evita que el OEE se vea bajo artificialmente al principio del día.\n\n"
        else:
             analysis_text += f"    • <span class='text-slate-400'>Disponibilidad Fija:</span> Para días pasados, se toma el turno completo (9 horas) para el cálculo histórico.\n\n"

        analysis_text += f"<span class='text-indigo-400 font-bold'>4. DESGLOSE TÉCNICO DE PRODUCCIÓN:</span>\n"
        art_indented = [f"    {a}" for a in art_summary]
        analysis_text += "\n".join(art_indented) + "\n\n"

        analysis_text += f"<span class='text-indigo-400 font-bold'>5. CONCLUSIÓN Y ANÁLISIS DE DESVÍO:</span>\n"
        
        # Lógica de Puntaje Resiliente
        performance_status = ""
        if t_op_hrs > 0 and qty == 0:
            performance_status = "<span class='text-amber-400 font-bold underline'>SIN PRODUCCIÓN REPORTADA</span>\n    <span class='text-[10px] text-slate-400'>* Se registra tiempo de trabajo pero no se cerraron piezas (Cantidad = 0).</span>"
        elif t_std_hrs == 0 and qty > 0:
            performance_status = "<span class='text-amber-400 font-bold underline'>SIN ESTÁNDAR TÉCNICO</span>\n    <span class='text-[10px] text-slate-400'>* Se detectó producción ({qty:.1f} pz) pero el ERP no tiene tiempos estándar cargados.</span>"
        elif performance >= 95:
             performance_status = "<span class='text-emerald-400 font-bold underline'>MUY BUENO</span>"
        elif performance >= 80:
             performance_status = "<span class='text-sky-400 font-bold underline'>BUENO</span>"
        elif performance >= 65:
             performance_status = "<span class='text-amber-400 font-bold underline'>REGULAR</span>"
        else:
             performance_status = "<span class='text-red-400 font-bold underline'>MALO</span>"

        analysis_text += f"    Puntaje de Desempeño: {performance_status}\n\n"

        if factor_velocidad > 1.1:
            analysis_text += f"    <i class='fas fa-exclamation-triangle text-amber-400 mr-2'></i>El operario trabajó a una velocidad <span class='text-amber-400 font-bold'>{factor_velocidad:.1f} veces menor</span> que la del tiempo estándar.\n"
        elif 0 < factor_velocidad <= 0.9:
            analysis_text += f"    <i class='fas fa-rocket text-emerald-400 mr-2'></i>El operario superó el estándar, trabajando un <span class='text-emerald-400 font-bold'>{((1-factor_velocidad)*100):.1f}% más rápido</span> de lo previsto.\n"
        elif t_std_hrs == 0:
            analysis_text += f"    <i class='fas fa-info-circle text-sky-400 mr-2'></i>No se registran tiempos estándar para los artículos producidos, lo que impide calcular el rendimiento real.\n"
        else:
            analysis_text += f"    El ritmo de trabajo se mantiene dentro de los parámetros estándar.\n"

        if not data['has_any_obs']:
            analysis_text += f"\n    <span class='text-sky-300 italic'>Nota: No se detectaron observaciones manuales en los registros para este periodo.</span>"

        lista_kpis_personal.append({
            'id': uid,
            'name': f"{data['nombre_personal']} ({uid})",
            'oee': round(oee, 2),
            'availability': round(availability, 2),
            'performance': round(performance, 2),
            'quality': round(quality, 2),
            'horas_std': t_std_hrs,
            'horas_prod': t_op_hrs,
            'actual_qty': qty,
            'rejected_qty': data['cantidad_rechazada'],
            'standard_time_formatted': format_time_display(t_std_hrs),
            'actual_time_formatted': format_time_display(t_op_hrs),
            'is_active_production': t_op_hrs > 0.001,
            'last_reason': data['latest_obs'],
            'last_machine': nombres_maquinas.get(data['latest_machine'], data['latest_machine'] or 'S/M'),
            'operator_name': data['nombre_personal'],
            'article_desc': data['latest_article'],
            'current_order': data['current_order'],
            'audit_log': json.dumps(clean_log_p),
            'analysis_summary': analysis_text
        })
        total_hrs_std_p += t_std_hrs
        total_hrs_prod_p += t_op_hrs
        total_hrs_disp_p += t_disp_p

    lista_kpis_personal.sort(key=lambda x: x['oee'], reverse=True)

    # 5. Globales Máquinas
    # Sumar el tiempo sin asignar a los acumuladores de tiempo real/std para que coincida con ERP
    # Ya lo sumamos arriba en el loop previo? No, arriba solo sumamos unassigned_time/std/qty
    
    # Convertir a horas para los KPIs globales
    h_unassigned_std = unassigned_std / 60.0
    h_unassigned_prod = unassigned_time / 60.0

    total_horas_std += h_unassigned_std
    total_horas_prod += h_unassigned_prod
    # total_horas_disp no se toca por unassigned porque no tienen turno

    if total_horas_disp > 0:
        promedio_oee = (total_horas_std / total_horas_disp) * 100.0
        avg_availability = (total_horas_prod / total_horas_disp) * 100.0 
    else:
        promedio_oee = avg_availability = 0.0
        
    avg_performance = (total_horas_std / total_horas_prod) * 100.0 if total_horas_prod > 0 else 0.0
    
    # CALIDAD: (Aceptadas / Totales) * 100
    total_piezas_real = global_actual_qty + global_rejected_qty
    avg_quality = (global_actual_qty / total_piezas_real * 100.0) if total_piezas_real > 0 else 100.0
    
    # avg_downtime para gráfico: porcentaje de tiempo perdido respecto al disponible
    res_avg_downtime = (global_downtime / (total_horas_disp * 60) * 100.0) if total_horas_disp > 0 else 0.0
    
    # Nuevo: Tiempo Estándar Total (Yellow ERP)
    global_standard_time = total_horas_std

    # Globales Personal
    if total_hrs_disp_p > 0:
        oee_p = (total_hrs_std_p / total_hrs_disp_p) * 100.0
        avail_p = (total_hrs_prod_p / total_hrs_disp_p) * 100.0
    else:
        oee_p = avail_p = 0.0
    
    perf_p = (total_hrs_std_p / total_hrs_prod_p) * 100.0 if total_hrs_prod_p > 0 else 0.0
    qual_p = avg_quality # Usamos la misma global de calidad por ahora

    for kpi in lista_kpis:
        kpi['is_active_production'] = kpi['horas_prod'] > 0.001
    
    lista_kpis.sort(key=lambda x: (not x['is_online'], not x['is_active_production'], x['id']))

    maquinas_activas = sum(1 for m in lista_kpis if m['is_online'])
    total_maquinas = len(lista_kpis)

    def fmt_mins_global(m_raw):
        # m_raw está en minutos
        if time_format == 'decimal':
            return f"{m_raw/60.0:.2f}"
        
        h, mins = divmod(int(round(m_raw)), 60)
        return f"{h} hs {mins} min" if h > 0 else f"{mins} min"

    resumen_maquinas = {
        'promedio_oee': round(promedio_oee, 2),
        'avg_availability': round(avg_availability, 2),
        'avg_performance': round(avg_performance, 2),
        'avg_quality': round(avg_quality, 2),
        'avg_rejected': round(100.0 - avg_quality, 2) if total_piezas_real > 0 else 0.0,
        'avg_downtime': round(res_avg_downtime, 2),
        'perf_multiplier': round(avg_performance / 100.0, 1) if avg_performance > 0 else 0.0,
        'active_count': maquinas_activas,
        'total_maquinas': total_maquinas,
        'global_planned_formatted': fmt_mins_global(total_horas_disp * 60),
        'global_actual_formatted': fmt_mins_global(total_horas_prod * 60),
        'global_standard_formatted': fmt_mins_global(total_horas_std * 60),
        'global_downtime_formatted': fmt_mins_global(global_downtime),
        'global_planned_qty': round(global_actual_qty / (avg_performance/100)) if avg_performance > 0 else 0,
        'global_actual_qty': round(global_actual_qty, 1),
        'global_rejected_qty': round(global_rejected_qty, 1),
        'global_total_qty': round(global_actual_qty + global_rejected_qty, 1),
        'global_repro_time_formatted': fmt_mins_global(global_repro_time),
        'unassigned_qty': round(unassigned_qty, 1),
        'unassigned_time_formatted': fmt_mins_global(unassigned_time),
        'unassigned_time_decimal': round(unassigned_time / 60.0, 2),
        'unassigned_process_formatted': fmt_mins_global(unassigned_process_time),
        'unassigned_interruption_formatted': fmt_mins_global(unassigned_interruption_time),
        'unassigned_std_formatted': fmt_mins_global(unassigned_std),
    }

    resumen_personal_dict = {
        'promedio_oee': round(oee_p, 2),
        'avg_availability': round(avail_p, 2),
        'avg_performance': round(perf_p, 2),
        'avg_quality': round(qual_p, 2),
        'perf_multiplier': round(perf_p / 100.0, 1) if perf_p > 0 else 0.0,
        'global_planned_formatted': fmt_mins_global(total_hrs_disp_p * 60),
        'global_actual_formatted': fmt_mins_global(total_hrs_prod_p * 60),
        'global_standard_formatted': fmt_mins_global(total_hrs_std_p * 60),
        'global_actual_qty': round(global_actual_qty, 1),
        'global_rejected_qty': round(global_rejected_qty, 1),
        'global_total_qty': round(global_actual_qty + global_rejected_qty, 1),
        'active_count': len(lista_kpis_personal),
    }

    # --- NUEVOS DATOS PARA GRÁFICOS PROFESIONALES ---
    
    # 1. Gráfico de Tendencia (Últimos 7 días)
    history_trend = []
    days_back = 7
    for i in range(days_back - 1, -1, -1):
        d_check = today_date - datetime.timedelta(days=i)
        if d_check.weekday() == 6: continue # Saltar domingos
        
        # Básicamente: sumamos std y prod de ese día
        d_start = timezone.make_aware(datetime.datetime.combine(d_check, datetime.time.min), datetime.timezone.utc)
        d_end = timezone.make_aware(datetime.datetime.combine(d_check, datetime.time.max), datetime.timezone.utc)
        
        # Simplificamos Performance para el histórico (Ratio de sumas)
        hist_data = VTMan.objects.filter(fecha__range=(d_start, d_end))
        h_std = hist_data.aggregate(s=Sum('tiempo_cotizado'))['s'] or 0.0
        h_prod = hist_data.aggregate(s=Sum('tiempo_minutos'))['s'] or 0.0
            
        h_perf = (h_std * 60 / h_prod * 100) if h_prod > 0 else 0
        history_trend.append({
            'day': d_check.strftime('%d/%m'),
            'oee': round(h_perf * 0.8, 1) # Estimación rápida OEE Histórico
        })

    # 2. Pareto de Paradas (Motivos de interrupción)
    # OPTIMIZACIÓN Y CORRECCIÓN PARETO: Incluir Mantenimientos y Fix Query
    # 1. Interrupciones de Producción (VTMan)
    # 2. Pareto de Paradas (Motivos de interrupción)
    # OPTIMIZACIÓN Y CORRECCIÓN PARETO: Incluir Mantenimientos y Fix Query
    # 1. Interrupciones de Producción (VTMan)
    
    interrupciones = VTMan.objects.filter(
        fecha__range=(f_start_naive, f_end_naive)
    ).filter(Q(es_interrupcion=True) | Q(articulod__icontains='DESCANSO'))
    
    reasons = {}
    for inter in interrupciones:
        r = str(inter.observaciones or inter.articulod or "S/M").strip().upper()
        if not r or r == 'NONE': r = "OTRO"
        # Limpiamos prefijos comunes para agrupar mejor
        r = r.replace("PARADA POR ", "").replace("INTERRUPCION ", "")
        reasons[r] = reasons.get(r, 0) + (inter.tiempo_minutos or 0)

    # 2. Incidencias de Mantenimiento (Tabla MySQL)
    # Las paradas por mantenimiento CRÍTICAS suelen estar aquí y no en VTMan
    for m in mantenimientos_periodo:
        try:
            # Calcular duración efectiva dentro del periodo visualizado
            # Inicio del problema (o inicio del periodo si empezó antes)
            start_m = max(m.fecha_reporte, fecha_inicio_utc)
            
            # Fin del problema
            if m.fecha_fin:
                end_m = min(m.fecha_fin, fecha_fin_utc)
            elif is_viewing_today:
                # Si sigue abierta y es hoy, contamos hasta AHORA
                end_m = timezone.now()
            else:
                # Si sigue abierta pero estamos viendo el pasado, contamos hasta fin del día
                end_m = fecha_fin_utc
            
            if end_m > start_m:
                duration_mins = (end_m - start_m).total_seconds() / 60.0
                
                # Etiqueta para el gráfico
                # Usamos el TIPO o la Falla como motivo
                if m.tipo == 'CORRECTIVO':
                    label = f"ROTURA: {m.maquina.nombre}" 
                else:
                    label = f"MANT: {m.tipo}"
                
                # Sumamos al Pareto
                reasons[label] = reasons.get(label, 0) + duration_mins
        except Exception as e:
            pass
    
    # Sort and Process for Chart
    sorted_reasons = sorted(reasons.items(), key=lambda x: x[1], reverse=True)[:8] # Top 8
    
    pareto_labels = []
    pareto_values = []     # Hours
    pareto_cumulative = [] # Percentage
    
    total_downtime_mins = sum([x[1] for x in sorted_reasons])
    current_sum = 0
    
    for name, mins in sorted_reasons:
        pareto_labels.append(name[:15]) # Short label
        pareto_values.append(round(mins, 1)) # Minutes (Raw for frontend formatting)
        
        current_sum += mins
        perc = (current_sum / total_downtime_mins * 100) if total_downtime_mins > 0 else 0
        pareto_cumulative.append(round(perc, 1))

    pareto_data = {
        'labels': pareto_labels,
        'values': pareto_values,
        'cumulative': pareto_cumulative
    }

    context = {
        'kpis': lista_kpis,
        'fecha_target': fecha_target_start,
        'fecha_fin_target': fecha_target_end,
        'is_today': is_viewing_today,
        'is_range': (fecha_target_start != fecha_target_end),
        'time_format': time_format,
        'resumen': resumen_maquinas,
        'view_type': view_type,
        'resumen_activo': resumen_personal_dict if view_type == 'personnel' else resumen_maquinas,
        'cards_data': lista_kpis_personal if view_type == 'personnel' else lista_kpis,
        'kpis_personal': lista_kpis_personal,
        'resumen_personal': resumen_personal_dict,
        'is_tv_mode': is_tv_mode,
        'history_trend': json.dumps(history_trend),
        'pareto_data': json.dumps(pareto_data)
    }
    if return_context:
        return context
    return render(request, 'dashboard/produccion.html', context)


# --- GESTIÓN DE MÁQUINAS (MySQL) ---

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

def gestion_maquinas(request):
    maquinas_list = MaquinaConfig.objects.all().order_by('id_maquina')
    
    # Paginación: 6 máquinas por página
    paginator = Paginator(maquinas_list, 6) 
    page = request.GET.get('page')
    
    try:
        maquinas = paginator.page(page)
    except PageNotAnInteger:
        # Si la página no es un entero, mostrar la primera
        maquinas = paginator.page(1)
    except EmptyPage:
        # Si la página está fuera de rango, mostrar la última
        maquinas = paginator.page(paginator.num_pages)

    return render(request, 'dashboard/gestion_maquinas.html', {'maquinas': maquinas})

def crear_maquina(request):
    if request.method == 'POST':
        try:
            # Validar y limpiar datos básicos
            id_maquina = request.POST.get('id_maquina').strip()
            nombre = request.POST.get('nombre').strip()
            
            if not id_maquina or not nombre:
                messages.error(request, 'El ID y Nombre son obligatorios.')
                return render(request, 'dashboard/form_maquina.html')

            mc = MaquinaConfig.objects.create(
                id_maquina=id_maquina,
                nombre=nombre,
                activa=request.POST.get('activa') == 'on',
                horario_inicio_sem=request.POST.get('horario_inicio_sem') or '07:00',
                horario_fin_sem=request.POST.get('horario_fin_sem') or '16:00',
                trabaja_sabado=request.POST.get('trabaja_sabado') == 'on',
                horario_inicio_sab=request.POST.get('horario_inicio_sab') or None,
                horario_fin_sab=request.POST.get('horario_fin_sab') or None,
                horario_inicio_dom=request.POST.get('horario_inicio_dom') or None,
                horario_fin_dom=request.POST.get('horario_fin_dom') or None,
                frecuencia_preventivo_horas=int(request.POST.get('frecuencia_preventivo_horas') or 0),
                fecha_ultimo_preventivo=request.POST.get('fecha_ultimo_preventivo') or None,
                fecha_proximo_preventivo=request.POST.get('fecha_proximo_preventivo') or None
            )
            
            # Audit
            AuditLog.objects.create(
                usuario=request.user.username if request.user.is_authenticated else 'Admin',
                modelo='MaquinaConfig',
                referencia_id=id_maquina,
                accion='CREATE',
                detalle=f"Creación de máquina {nombre}"
            )
            
            messages.success(request, 'Máquina creada correctamente.')
            return redirect('gestion_maquinas')
        except Exception as e:
             messages.error(request, f'Error al crear máquina: {e}')
             
    return render(request, 'dashboard/form_maquina.html')

from django.urls import reverse

def editar_maquina(request, pk):
    maquina = get_object_or_404(MaquinaConfig, pk=pk)
    # Capturamos la página actual para mantener la navegación
    page = request.GET.get('page') or request.POST.get('page') or 1
    
    if request.method == 'POST':
        try:
            maquina.id_maquina = request.POST.get('id_maquina').strip()
            maquina.nombre = request.POST.get('nombre').strip()
            maquina.activa = request.POST.get('activa') == 'on'
            maquina.horario_inicio_sem = request.POST.get('horario_inicio_sem')
            maquina.horario_fin_sem = request.POST.get('horario_fin_sem')
            maquina.trabaja_sabado = request.POST.get('trabaja_sabado') == 'on'
            maquina.horario_inicio_sab = request.POST.get('horario_inicio_sab') or None
            maquina.horario_fin_sab = request.POST.get('horario_fin_sab') or None
            maquina.horario_inicio_dom = request.POST.get('horario_inicio_dom') or None
            maquina.horario_fin_dom = request.POST.get('horario_fin_dom') or None
            
            # Nuevos Campos Preventivos
            maquina.frecuencia_preventivo_horas = int(request.POST.get('frecuencia_preventivo_horas') or 0)
            
            fecha_str = request.POST.get('fecha_ultimo_preventivo')
            maquina.fecha_ultimo_preventivo = fecha_str if fecha_str else None
            
            fecha_prox = request.POST.get('fecha_proximo_preventivo')
            maquina.fecha_proximo_preventivo = fecha_prox if fecha_prox else None

            # Detect changes (basic)
            maquina.save()
            
            AuditLog.objects.create(
                usuario=request.user.username if request.user.is_authenticated else 'Admin',
                modelo='MaquinaConfig',
                referencia_id=maquina.id_maquina,
                accion='UPDATE',
                detalle=f"Actualización de configuración: {maquina.nombre}"
            )

            messages.success(request, 'Máquina actualizada.')
            
            # Redirigir a la misma página del listado
            return redirect(reverse('gestion_maquinas') + f'?page={page}')
            
        except Exception as e:
            messages.error(request, f'Error al actualizar: {e}')
            
    return render(request, 'dashboard/form_maquina.html', {'maquina': maquina, 'page': page})

def eliminar_maquina(request, pk):
    maquina = get_object_or_404(MaquinaConfig, pk=pk)
    mid = maquina.id_maquina
    maquina.delete()
    
    AuditLog.objects.create(
        usuario=request.user.username if request.user.is_authenticated else 'Admin',
        modelo='MaquinaConfig',
        referencia_id=mid,
        accion='DELETE',
        detalle=f"Eliminación de máquina {mid}"
    )
    
    messages.success(request, 'Máquina eliminada.')
    return redirect('gestion_maquinas')

# --- GESTIÓN DE PERSONAL (MySQL) ---

def gestion_personal(request):
    operarios_list = OperarioConfig.objects.all().order_by('nombre')
    
    # Paginación: 6 operarios por página
    paginator = Paginator(operarios_list, 6) 
    page = request.GET.get('page')
    
    try:
        operarios = paginator.page(page)
    except PageNotAnInteger:
        operarios = paginator.page(1)
    except EmptyPage:
        operarios = paginator.page(paginator.num_pages)

    return render(request, 'dashboard/gestion_personal.html', {'operarios': operarios})

def crear_operario(request):
    if request.method == 'POST':
        try:
            legajo = request.POST.get('legajo').strip()
            nombre = request.POST.get('nombre').strip()
            sector = request.POST.get('sector').strip() or "PRODUCCION"
            
            if not legajo or not nombre:
                messages.error(request, 'El Legajo y Nombre son obligatorios.')
                return render(request, 'dashboard/form_operario.html')

            OperarioConfig.objects.create(
                legajo=legajo,
                nombre=nombre,
                sector=sector,
                activo=request.POST.get('activo') == 'on'
            )
            messages.success(request, 'Operario creado correctamente.')
            return redirect('gestion_personal')
        except Exception as e:
             messages.error(request, f'Error al crear operario: {e}')
             
    return render(request, 'dashboard/form_operario.html')

def editar_operario(request, pk):
    operario = get_object_or_404(OperarioConfig, pk=pk)
    page = request.GET.get('page') or request.POST.get('page') or 1
    
    if request.method == 'POST':
        try:
            operario.legajo = request.POST.get('legajo').strip()
            operario.nombre = request.POST.get('nombre').strip()
            operario.sector = request.POST.get('sector').strip() or "PRODUCCION"
            operario.activo = request.POST.get('activo') == 'on'
            operario.save()
            messages.success(request, 'Operario actualizado.')
            return redirect(reverse('gestion_personal') + f'?page={page}')
        except Exception as e:
             messages.error(request, f'Error al actualizar: {e}')
    
    return render(request, 'dashboard/form_operario.html', {'operario': operario, 'page': page})

def eliminar_operario(request, pk):
    operario = get_object_or_404(OperarioConfig, pk=pk)
    operario.delete()
    messages.success(request, 'Operario eliminado.')
    return redirect('gestion_personal')

def obtener_auditoria(request):
    """ API para el modal de auditoría individual """
    import datetime
    from django.http import JsonResponse
    from dateutil import parser
    from django.utils import timezone
    from django.db.models import Q
    
    uid = request.GET.get('id')
    view_type = request.GET.get('view', 'machines')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date') or start_date
    
    if not uid or not start_date:
        return JsonResponse({'status': 'error', 'message': 'Faltan parámetros'})
    
    try:
        d1 = parser.parse(start_date).date()
        d2 = parser.parse(end_date).date()
    except:
        return JsonResponse({'status': 'error', 'message': 'Fechas inválidas'})
        
    start_str = d1.strftime('%Y-%m-%d')
    end_str = d2.strftime('%Y-%m-%d')
    
    registros_raw = VTMan.objects.extra(
        where=["CONVERT(date, FECHA) >= %s AND CONVERT(date, FECHA) <= %s"],
        params=[start_str, end_str]
    ).order_by('fecha')

    if view_type == 'personnel':
        registros_raw = registros_raw.filter(id_concepto__contains=uid)
    else:
        registros_raw = registros_raw.filter(id_maquina=uid)
        
    audit_log = []
    total_std_mins = 0.0
    total_prod_mins = 0.0
    total_qty = 0.0
    total_rejected_qty = 0.0
    articulos_resumen = {} 
    has_mat_audit = False
    has_special_tasks = False
    matriceria_std_done_audit = set()
    
    for reg_obj in registros_raw:
        reg_uid = str(reg_obj.id_concepto or '').strip()
        if view_type == 'personnel' and reg_uid != uid:
            continue
            
        duracion = reg_obj.tiempo_minutos or 0.0
        qty = reg_obj.cantidad_producida or 0.0
        std_hrs = reg_obj.tiempo_cotizado or 0.0
        std_mins = std_hrs * 60.0
        
        raw_id_op = str(reg_obj.id_operacion or "").strip().upper()
        raw_art_d = str(reg_obj.articulod or "").upper()
        raw_op_d = str(reg_obj.operacion or "").strip().upper()
        raw_obs = str(reg_obj.observaciones or "").strip().upper()

        non_prod_keywords = ['REPROCESO', 'RETRABAJO']
        descanso_keywords = ['DESCANSO', 'ALMUERZO', 'PAUSA']
        
        is_repro = (raw_id_op in non_prod_keywords or raw_op_d in non_prod_keywords or
                    any(k in raw_art_d for k in non_prod_keywords) or
                    any(k in raw_obs for k in non_prod_keywords))
        is_descanso = (raw_op_d in descanso_keywords or
                       any(k in raw_art_d for k in descanso_keywords) or
                       any(k in raw_obs for k in descanso_keywords))

        special_audit_keywords = ['MATRICER', 'TAREAS GENERALES', 'AJUSTES', 'REBABADO', 'GRABADO', 'ARMADO']
        is_matriceria = any(k in raw_art_d or k in raw_op_d for k in special_audit_keywords)
        id_orden = reg_obj.id_orden
        
        this_std = std_mins
        if is_matriceria:
            this_std = duracion
            if 'MATRICER' in raw_art_d or 'MATRICER' in raw_op_d:
                has_mat_audit = True
            else:
                has_special_tasks = True

        h_inicio = reg_obj.hora_inicio
        h_fin = reg_obj.hora_fin

        audit_log.append({
            'inicio': h_inicio.strftime('%H:%M:%S') if h_inicio else '--:--:--',
            'fin': h_fin.strftime('%H:%M:%S') if h_fin else '--:--:--',
            'maquina': reg_obj.id_maquina or 'S/A',
            'orden': reg_obj.id_orden or '---',
            'articulo': reg_obj.articulod[:40] if reg_obj.articulod else 'Sin Artículo',
            'cliente': '-',
            'cantidad': round(qty, 1),
            'tiempo': f"{round(duracion, 1)} min",
            'estandar': f"{round(this_std, 1)} min",
            'observacion': reg_obj.observaciones or ''
        })
        
        if is_repro:
            total_rejected_qty += qty
        elif not is_descanso:
            total_qty += qty
            if is_matriceria:
                total_std_mins += duracion
                this_std = duracion # Para el visual del log
            elif qty > 0:
                total_std_mins += std_mins
                this_std = std_mins
            else:
                this_std = 0
        
        # Sincronización de Tiempo Operativo (Downtime vs Process)
        if not is_descanso and not reg_obj.es_interrupcion:
            total_prod_mins += duracion

    now_arg = timezone.localtime(timezone.now())
    is_viewing_today = (d1 == now_arg.date())
    if is_viewing_today:
        sh, eh = 7.0, 16.0
        now_dec = now_arg.hour + now_arg.minute / 60.0
        if now_dec < sh: total_disp_mins = 0.01
        elif now_dec > eh: total_disp_mins = (eh - sh) * 60.0
        else: total_disp_mins = (now_dec - sh) * 60.0
    else:
        total_disp_mins = 9 * 60.0

    if total_disp_mins < total_prod_mins: total_disp_mins = total_prod_mins

    availability = (total_prod_mins / total_disp_mins * 100) if total_disp_mins > 0 else 0
    performance = (total_std_mins / total_prod_mins * 100) if total_prod_mins > 0 else 0
    
    total_piezas_p = total_qty + total_rejected_qty
    quality = (total_qty / total_piezas_p * 100.0) if total_piezas_p > 0 else 100.0
    
    oee = (availability * performance * quality) / 10000.0
    
    nombre_display = uid
    try:
        if view_type == 'personnel':
            nombre_display = OperarioConfig.objects.get(legajo=uid).nombre
        else:
            nombre_display = MaquinaConfig.objects.get(id_maquina=uid).nombre
    except: pass

    # DETERMINAR SI ES HOY PARA EL TEXTO
    is_actually_today = (d1 == timezone.localtime(timezone.now()).date())

    analysis_conversational = f"<span class='report-main-title'>ANÁLISIS DE DESEMPEÑO INTELIGENTE</span>\n"
    analysis_conversational += f"<div class='mb-6 p-5 bg-indigo-500/10 rounded-2xl border-l-4 border-indigo-500 shadow-inner'>\n"
    analysis_conversational += f"  <span class='text-lg font-black text-white italic'>\"¡Sí! El valor de <span class='text-indigo-400'>{oee:.1f}%</span> que ves ahora es un valor muy real y correcto para la situación actual de {nombre_display}.\"</span>\n"
    analysis_conversational += f"</div>\n\n"

    analysis_conversational += "<span class='text-indigo-400 font-black text-xl uppercase tracking-tighter'>¿POR QUÉ ESE VALOR ES EL CORRECTO?</span>\n"
    analysis_conversational += f"Si miramos los datos del <span class='text-white font-bold'>{d1.strftime('%d/%m/%Y')}</span> de <span class='text-white font-bold'>{nombre_display} ({uid})</span>, el sistema está haciendo lo siguiente:\n\n"
    
    # 1. MATRICERÍA / TAREAS ESPECIALES (Solo si aplica)
    if has_mat_audit or has_special_tasks:
        tipo_tarea = "Matricería" if has_mat_audit else "Tareas Especiales"
        if has_mat_audit and has_special_tasks:
            tipo_tarea = "Matricería y Tareas Especiales"
            
        analysis_conversational += f"<span class='text-emerald-400 font-black'>• {tipo_tarea.upper()} (REGLA 1:1):</span> {nombre_display} realizó <span class='text-white font-bold'>{tipo_tarea.lower()}</span>. Este tiempo se computa con <span class='text-white underline font-bold'>eficiencia neutra (100%)</span> para no penalizar el OEE en trabajos sin estándar fijo.\n\n"
    
    # 2. RENDIMIENTO
    if performance > 115:
        analysis_conversational += f"<span class='text-emerald-400 font-black'>• PRODUCCIÓN DE SERIE (ALTO RENDIMIENTO):</span> En las órdenes de serie, se está trabajando <span class='text-white font-bold'>sensiblemente más rápido</span> que el estándar del ERP. El OEE superior al 100% es real y refleja una cadencia de producción superior a la estimada.\n\n"
    elif performance > 100:
        analysis_conversational += f"<span class='text-lime-400 font-black'>• PRODUCCIÓN DE SERIE (BUEN RITMO):</span> Se está trabajando por encima del estándar del ERP.\n\n"
    elif performance < 80 and total_std_mins > 0:
        analysis_conversational += f"<span class='text-amber-400 font-black'>• PRODUCCIÓN DE SERIE (BAJO RENDIMIENTO):</span> El ritmo actual (<span class='font-black'>{performance:.1f}%</span>) es inferior al estándar esperado por el sistema.\n\n"
    elif total_std_mins > 0:
        analysis_conversational += f"<span class='text-sky-300 font-black'>• PRODUCCIÓN DE SERIE (ESTABLE):</span> El ritmo de trabajo coincide con los estándares del ERP.\n\n"
    else:
        analysis_conversational += f"<span class='text-slate-400 font-bold italic'>• SIN PRODUCCIÓN DE SERIE:</span> No hay piezas de serie terminadas reportadas en este periodo.\n\n"


    # 3. DISPONIBILIDAD
    if is_actually_today:
        analysis_conversational += f"<span class='text-indigo-300 font-black'>• DISPONIBILIDAD REAL ({availability:.1f}%):</span> El sistema es <span class='text-white italic underline font-bold'>INTELIGENTE</span>: compara el tiempo trabajado contra el tiempo transcurrido hoy (07:00 AM hasta este momento).\n\n"
    else:
        analysis_conversational += f"<span class='text-slate-400 font-black'>• DISPONIBILIDAD TOTAL ({availability:.1f}%):</span> Al tratarse de un día pasado, comparamos el tiempo trabajado contra el turno completo de <span class='text-white font-bold'>9 horas</span>.\n\n"

    # REPORTE 2: MÉTRICAS DETALLADAS (El que pedía el usuario)
    analysis_detailed = f"<span class='report-main-title'>MÉTRICAS TÉCNICAS DE CONTROL</span>\n\n"
    analysis_detailed += "<span class='text-sky-400 font-bold uppercase'>1. VERIFICACIÓN DE TIEMPOS (TABLERO VS ERP)</span>\n"
    analysis_detailed += f"    • Tiempo Estándar Computado: <span class='text-white font-bold'>{total_std_mins/60.0:.2f} hs</span>\n"
    analysis_detailed += f"    • Tiempo Real Operativo: <span class='text-white font-bold'>{total_prod_mins/60.0:.2f} hs</span>\n"
    analysis_detailed += f"    • Tiempo Fichado Turno: <span class='text-white font-bold'>{total_disp_mins/60.0:.2f} hs</span>\n\n"
    
    analysis_detailed += f"<span class='text-sky-400 font-bold uppercase'>2. CÁLCULO DE LA EFICIENCIA ({oee:.1f}%)</span>\n"
    analysis_detailed += f"    • Disponibilidad ({availability:.1f}%): {total_prod_mins/60.0:.2f} hrs / {total_disp_mins/60.0:.2f} hrs.\n"
    analysis_detailed += f"    • Rendimiento ({performance:.1f}%): {total_std_mins/60.0:.2f} hrs / {total_prod_mins/60.0:.2f} hrs.\n"
    analysis_detailed += f"    • Calidad ({quality:.1f}%): {total_qty:.1f} buenas / {total_piezas_p:.1f} totales.\n"
    analysis_detailed += f"    • OEE Final: {oee:.1f}%.\n\n"

    rating = "EXCELENTE" if oee >= 100 else "MUY BUENO" if oee >= 85 else "BUENO" if oee >= 70 else "REGULAR" if oee >= 50 else "A REVISAR"
    analysis_detailed += f"<div class='mt-6 p-4 bg-white/5 border border-white/10 rounded-xl text-center'>\n"
    analysis_detailed += f"  <span class='text-slate-500 font-black text-[10px] uppercase'>Clasificación de Turno</span>\n"
    analysis_detailed += f"  <h4 class='text-2xl font-black text-white'>{rating}</h4>\n"
    analysis_detailed += f"</div>"

    # 3. MANUAL DE CÁLCULO DE RENDIMIENTO (Agregado por pedido del usuario)
    analysis_detailed += f"\n\n<div class='mt-8 p-6 bg-blue-500/5 border border-blue-500/20 rounded-2xl'>\n"
    analysis_detailed += "  <div class='flex items-center gap-3 mb-4'>\n"
    analysis_detailed += "    <div class='w-8 h-8 rounded-lg bg-blue-600/20 flex items-center justify-center text-blue-400'>\n"
    analysis_detailed += "      <i class='fas fa-book'></i>\n"
    analysis_detailed += "    </div>\n"
    analysis_detailed += "    <h5 class='text-sm font-black text-white uppercase tracking-wider'>Guía Técnica: ¿Cómo calculamos tu Rendimiento?</h5>\n"
    analysis_detailed += "  </div>\n\n"
    
    analysis_detailed += "  <div class='space-y-4 text-[12px] text-slate-300 leading-relaxed font-medium'>\n"
    analysis_detailed += "    <p>El rendimiento es el motor de tu eficiencia. Compara cuánto tiempo <span class='text-white underline'>debería</span> haber tardado el trabajo contra cuánto tiempo <span class='text-white underline'>tardó realmente</span>.</p>\n\n"
    
    analysis_detailed += "    <div class='bg-slate-950/40 p-4 rounded-xl border border-white/5 font-mono text-center'>\n"
    analysis_detailed += f"      <span class='text-blue-400 font-bold'>Rendimiento ({performance:.1f}%)</span> = ( {total_std_mins/60.0:.2f} hs Estándar / {total_prod_mins/60.0:.2f} hs Real ) x 100\n"
    analysis_detailed += "    </div>\n\n"
    
    analysis_detailed += "    <div>\n"
    analysis_detailed += "      <span class='text-white font-bold block mb-1'>1. ¿De dónde salen los números?</span>\n"
    analysis_detailed += f"      • <span class='text-blue-300'>TIEMPO ESTÁNDAR ({total_std_mins/60.0:.2f} hs):</span> Es el tiempo objetivo cargado en el ERP para las piezas terminadas.\n"
    analysis_detailed += f"      • <span class='text-blue-300'>TIEMPO REAL ({total_prod_mins/60.0:.2f} hs):</span> Es el tiempo cronometrado que el operario estuvo trabajando físicamente.\n"
    analysis_detailed += "    </div>\n\n"
    
    analysis_detailed += "    <div>\n"
    analysis_detailed += "      <span class='text-white font-bold block mb-1'>2. Casos Especiales</span>\n"
    analysis_detailed += "      • <span class='text-emerald-400'>REGLA 1:1 (NEUTRA):</span> En tareas como Matricería, Ajustes o Tareas Generales (sin estándar fijo), asignamos Tiempo Estándar = Tiempo Real. Esto da siempre 100% de rendimiento para no penalizar el OEE.\n"
    analysis_detailed += "      • <span class='text-amber-400'>DEDUPLICACIÓN:</span> El sistema limpia registros repetidos del ERP para que el cálculo sea 100% justo y no se infle artificialmente.\n"
    analysis_detailed += "    </div>\n"
    
    analysis_detailed += "    <div class='pt-2 italic text-slate-500'>\n"
    analysis_detailed += "      En resumen: Si el valor es > 100%, estás ganando tiempo sobre lo previsto; si es < 100%, la producción fue más lenta que el estándar.\n"
    analysis_detailed += "    </div>\n"
    analysis_detailed += "  </div>\n"
    analysis_detailed += "</div>"

    # 4. MANUAL DE CÁLCULO DE DISPONIBILIDAD (Agregado por pedido del usuario)
    analysis_detailed += f"\n\n<div class='mt-4 p-6 bg-indigo-500/5 border border-indigo-500/20 rounded-2xl'>\n"
    analysis_detailed += "  <div class='flex items-center gap-3 mb-4'>\n"
    analysis_detailed += "    <div class='w-8 h-8 rounded-lg bg-indigo-600/20 flex items-center justify-center text-indigo-400'>\n"
    analysis_detailed += "      <i class='fas fa-clock'></i>\n"
    analysis_detailed += "    </div>\n"
    analysis_detailed += "    <h5 class='text-sm font-black text-white uppercase tracking-wider'>Guía Técnica: ¿Cómo calculamos tu Disponibilidad?</h5>\n"
    analysis_detailed += "  </div>\n\n"
    
    analysis_detailed += "  <div class='space-y-4 text-[12px] text-slate-300 leading-relaxed font-medium'>\n"
    analysis_detailed += "    <p>La Disponibilidad mide qué tan bien estamos aprovechando el tiempo del turno. Es el porcentaje del tiempo total que el operario o la máquina estuvieron realmente produciendo.</p>\n\n"
    
    analysis_detailed += "    <div class='bg-slate-950/40 p-4 rounded-xl border border-white/5 font-mono text-center'>\n"
    analysis_detailed += "      <span class='text-indigo-400 font-bold'>1. La Fórmula Matemática</span><br>\n"
    analysis_detailed += f"      <span class='text-white font-bold'>Disponibilidad ({availability:.1f}%)</span> = ( {total_prod_mins/60.0:.2f} hs Real / {total_disp_mins/60.0:.2f} hs Turno ) x 100\n"
    analysis_detailed += "    </div>\n\n"
    
    analysis_detailed += "    <div>\n"
    analysis_detailed += "      <span class='text-white font-bold block mb-1'>2. ¿De dónde salen los números?</span>\n"
    analysis_detailed += f"      • <span class='text-indigo-300'>NUMERADOR (Tiempo Real):</span> Suma de todos los minutos de trabajo reportados en el ERP ({total_prod_mins/60.0:.2f} hs).\n"
    analysis_detailed += f"      • <span class='text-indigo-300'>DENOMINADOR (Tiempo de Turno):</span> Aquí el sistema es <span class='text-white italic underline font-bold'>Inteligente</span>:<br>\n"
    if is_viewing_today:
        analysis_detailed += f"        <span class='text-indigo-400 ml-4 font-bold'>→ Mirando HOY:</span> Medimos desde las 07:00 AM hasta este momento ({now_arg.strftime('%H:%M')}). Disponibilidad actual: {total_disp_mins/60.0:.2f} hs.<br>\n"
    else:
        analysis_detailed += "        <span class='text-slate-400 ml-4 font-bold'>→ Día Pasado:</span> Se toma el turno completo fijo (9 horas o 540 min).<br>\n"
    analysis_detailed += "    </div>\n\n"

    analysis_detailed += "    <div class='bg-indigo-900/10 p-4 rounded-xl border border-indigo-500/20'>\n"
    analysis_detailed += "      <span class='text-white font-bold block mb-1'>3. Ejemplo Práctico (Smart Availability)</span>\n"
    analysis_detailed += "      Si son las 10:00 AM y el operario trabajó 2.5 horas (150 min) y tuvo 30 min de paradas desde las 07:00 AM:<br>\n"
    analysis_detailed += "      Cálculo: (150 min / 180 min transcurridos) x 100 = <span class='text-indigo-400 font-bold'>83.3% de Disponibilidad</span>.\n"
    analysis_detailed += "    </div>\n\n"

    analysis_detailed += "    <div>\n"
    analysis_detailed += "      <span class='text-white font-bold block mb-1'>4. ¿Por qué el sistema es \"Inteligente\"?</span>\n"
    analysis_detailed += "      A diferencia de otros sistemas que te castigarían a la mañana (diciendo que tu disponibilidad es baja porque solo trabajaste 2 horas de un turno de 9), este tablero se adapta a la hora actual. A las 08:00 AM te mide contra 1 hora; a las 02:00 PM te mide contra 7 horas.\n"
    analysis_detailed += "    </div>\n\n"
    
    analysis_detailed += "    <div class='pt-2 italic text-slate-500'>\n"
    analysis_detailed += "      La meta siempre es estar cerca del 100%, lo que significaría que no hubo baches de tiempo sin reportes desde que arrancó el día.\n"
    analysis_detailed += "    </div>\n"
    analysis_detailed += "  </div>\n"
    analysis_detailed += "</div>"

    # 5. MANUAL DE CÁLCULO DE OEE (Agregado por pedido del usuario)
    analysis_detailed += f"\n<div class='mt-4 p-6 bg-amber-500/5 border border-amber-500/20 rounded-2xl'>\n"
    analysis_detailed += "  <div class='flex items-center gap-3 mb-4'>\n"
    analysis_detailed += "    <div class='w-8 h-8 rounded-lg bg-amber-600/20 flex items-center justify-center text-amber-400'>\n"
    analysis_detailed += "      <i class='fas fa-trophy'></i>\n"
    analysis_detailed += "    </div>\n"
    analysis_detailed += "    <h5 class='text-sm font-black text-white uppercase tracking-wider'>Guía Técnica: El Indicador OEE</h5>\n"
    analysis_detailed += "  </div>\n\n"
    
    analysis_detailed += "  <div class='space-y-4 text-[12px] text-slate-300 leading-relaxed font-medium'>\n"
    analysis_detailed += "    <p>El OEE (Overall Equipment Effectiveness) es el <span class='text-amber-400 font-bold'>Indicador Maestro</span>. No solo mide si estuviste trabajando, sino qué tan bien lo hiciste considerando tiempo, velocidad y calidad.</p>\n\n"
    
    analysis_detailed += "    <div class='bg-slate-950/40 p-4 rounded-xl border border-white/5 font-mono text-center'>\n"
    analysis_detailed += "      <span class='text-amber-400 font-bold'>Fórmula Maestro OEE</span><br>\n"
    analysis_detailed += f"      <span class='text-white font-bold'>{oee:.1f}% OEE</span> = {availability:.1f}% (Disp) x {performance:.1f}% (Rend) x {quality:.1f}% (Cal)\n"
    analysis_detailed += "    </div>\n\n"
    
    analysis_detailed += "    <div class='grid grid-cols-1 md:grid-cols-3 gap-3'>\n"
    # Disponibilidad
    analysis_detailed += "      <div class='p-5 bg-white/5 rounded-2xl border border-white/10'>\n"
    analysis_detailed += "        <span class='text-indigo-400 text-sm font-black uppercase tracking-wider block mb-3 text-center border-b border-indigo-500/30 pb-2'>1. Disponibilidad</span>\n"
    analysis_detailed += "        <p class='text-sm text-white font-bold mb-4 italic text-center underline decoration-indigo-500/30'>¿Estuvo operando?</p>\n"
    analysis_detailed += "        <ul class='text-[13px] text-slate-200 space-y-2 list-disc pl-5'>\n"
    analysis_detailed += "          <li>Mide el <span class='text-indigo-300 font-bold'>TIEMPO</span>.</li>\n"
    analysis_detailed += "          <li>Si el turno es de 9hs y reportó 8hs, la respuesta es 'Casi todo'.</li>\n"
    analysis_detailed += "          <li>Si hay muchos 'baches' sin reportes, este número baja.</li>\n"
    analysis_detailed += "        </ul>\n"
    analysis_detailed += "      </div>\n"
    # Rendimiento
    analysis_detailed += "      <div class='p-5 bg-white/5 rounded-2xl border border-white/10'>\n"
    analysis_detailed += "        <span class='text-lime-400 text-sm font-black uppercase tracking-wider block mb-3 text-center border-b border-lime-500/30 pb-2'>2. Rendimiento</span>\n"
    analysis_detailed += "        <p class='text-sm text-white font-bold mb-4 italic text-center underline decoration-lime-500/30'>¿A qué velocidad?</p>\n"
    analysis_detailed += "        <ul class='text-[13px] text-slate-200 space-y-2 list-disc pl-5'>\n"
    analysis_detailed += "          <li>Mide la <span class='text-lime-300 font-bold'>VELOCIDAD</span>.</li>\n"
    analysis_detailed += "          <li>Debe cumplir la velocidad que pide el ERP.</li>\n"
    analysis_detailed += "          <li>Si la pieza pide 1 min y tardó 1.5 min, este número baja.</li>\n"
    analysis_detailed += "        </ul>\n"
    analysis_detailed += "      </div>\n"
    # Calidad
    analysis_detailed += "      <div class='p-5 bg-white/5 rounded-2xl border border-white/10'>\n"
    analysis_detailed += "        <span class='text-amber-500 text-sm font-black uppercase tracking-wider block mb-3 text-center border-b border-amber-500/30 pb-2'>3. Calidad</span>\n"
    analysis_detailed += "        <p class='text-sm text-white font-bold mb-4 italic text-center underline decoration-amber-500/30'>¿Sin reprocesos?</p>\n"
    analysis_detailed += "        <ul class='text-[13px] text-slate-200 space-y-2 list-disc pl-5'>\n"
    analysis_detailed += "          <li>Mide las <span class='text-amber-300 font-bold'>PIEZAS BUENAS</span>.</li>\n"
    analysis_detailed += "          <li>¿Cuántas salieron bien a la primera?</li>\n"
    analysis_detailed += "          <li>Si hizo 100 piezas y 10 son reproceso, la calidad es del 90%.</li>\n"
    analysis_detailed += "        </ul>\n"
    analysis_detailed += "      </div>\n"
    analysis_detailed += "    </div>\n\n"

    analysis_detailed += "    <div class='bg-amber-900/10 p-4 rounded-xl border border-amber-500/20'>\n"
    analysis_detailed += "      <span class='text-white font-bold block mb-1'>¿Por qué es tan exigente?</span>\n"
    analysis_detailed += "      El OEE es una multiplicación. Si uno de los factores baja, el resultado final se resiente. Un OEE del 85% es considerado de Clase Mundial.\n"
    analysis_detailed += "    </div>\n"
    
    analysis_detailed += "    <div class='pt-4 text-center'>\n"
    analysis_detailed += "      <span class='text-amber-400 font-bold text-sm italic underline decoration-amber-500/30'>\n"
    analysis_detailed += "        Este indicador te permite saber exactamente dónde está la pérdida de eficiencia en el turno.\n"
    analysis_detailed += "      </span>\n"
    analysis_detailed += "    </div>\n"
    analysis_detailed += "  </div>\n"
    analysis_detailed += "</div>"

    return JsonResponse({
        'status': 'success',
        'audit_log': audit_log,
        'analysis_conversational': analysis_conversational,
        'analysis_detailed': analysis_detailed
    })

# --- MÓDULO DE MANTENIMIENTO ---

def lista_mantenimiento(request):
    """
    Vista principal de mantenimiento: Lista de incidencias y formulario de reporte.
    """
    incidencias = Mantenimiento.objects.all().order_by('-fecha_reporte')
    maquinas = MaquinaConfig.objects.filter(activa=True)
    
    # Filtros simples
    maquina_id = request.GET.get('maquina')
    estado = request.GET.get('estado')
    
    if maquina_id:
        incidencias = incidencias.filter(maquina_id=maquina_id)

    # --- LÓGICA PREVENTIVA ---
    preventivos = []
    # Solo procesamos si hay maquinas activas
    for m in maquinas:
        if m.frecuencia_preventivo_horas > 0 or m.fecha_proximo_preventivo:
            # Calcular uso desde el último service
            start_date = m.fecha_ultimo_preventivo
            
            # Query base
            qs = VTMan.objects.filter(id_maquina=m.id_maquina)
            if start_date:
                qs = qs.filter(fecha__gt=start_date)
            
            # Sumar tiempo productivo
            agg = qs.aggregate(total=Sum('tiempo_minutos'))
            used_mins = agg['total'] or 0.0
            used_hours = used_mins / 60.0
            
            completion_pct = 0.0
            if m.frecuencia_preventivo_horas > 0:
                completion_pct = (used_hours / m.frecuencia_preventivo_horas * 100.0)
            
            status = 'OK'
            details = []

            # 1. Comprobación por HORAS (solo si frecuencia > 0)
            if m.frecuencia_preventivo_horas > 0:
                if used_hours >= m.frecuencia_preventivo_horas:
                    status = 'CRITICAL'
                    details.append("Límite de horas excedido")
                elif completion_pct >= 85:
                    status = 'WARNING' if status != 'CRITICAL' else status
                    details.append("Próximo a límite de horas")
            
            # 2. Comprobación por FECHA (Agenda)
            agenda_msg = ""
            days_diff = None
            if m.fecha_proximo_preventivo:
                today = timezone.now().date()
                delta = m.fecha_proximo_preventivo - today
                days_diff = delta.days
                
                if days_diff < 0:
                    status = 'CRITICAL'
                    msg = f"Vencido hace {abs(days_diff)} días"
                    details.append(msg)
                    agenda_msg = msg
                elif days_diff == 0:
                    status = 'CRITICAL'
                    msg = "Vence HOY"
                    details.append(msg)
                    agenda_msg = msg
                elif days_diff <= 7:
                    status = 'WARNING' if status != 'CRITICAL' else status
                    msg = f"Vence en {days_diff} días"
                    details.append(msg)
                    agenda_msg = msg
                
            if status != 'OK':
                preventivos.append({
                    'maquina': m,
                    'used_hours': round(used_hours, 1),
                    'limit_hours': m.frecuencia_preventivo_horas,
                    'progress': min(round(completion_pct, 1), 100),
                    'status': status,
                    'last_service': m.fecha_ultimo_preventivo,
                    'next_service_date': m.fecha_proximo_preventivo,
                    'agenda_msg': agenda_msg,
                    'days_diff': days_diff
                })
            
    # Ordenar: Críticos primero
    preventivos.sort(key=lambda x: (x['status'] == 'CRITICAL', x['progress']), reverse=True)

    # Conteos para los cuadros de arriba
    today_local = timezone.localtime(timezone.now()).date()
    counts = {
        'abiertos': Mantenimiento.objects.filter(estado='ABIERTO').count(),
        'proceso': Mantenimiento.objects.filter(estado='PROCESO').count(),
        'cerrados_hoy': Mantenimiento.objects.filter(estado='CERRADO', fecha_fin__date=today_local).count(),
        'preventivos_vencidos': sum(1 for p in preventivos if p['status'] == 'CRITICAL')
    }
        
    return render(request, 'dashboard/mantenimiento.html', {
        'incidencias': incidencias,
        'maquinas': maquinas,
        'counts': counts,
        'preventivos': preventivos, # Nueva lista
        'filtros': {
            'maquina': maquina_id,
            'estado': estado
        }
    })

def crear_incidencia(request):
    """
    API/Vista para reportar una nueva avería o servicio programado.
    """
    if request.method == 'POST':
        maquina_id = request.POST.get('maquina')
        tipo = request.POST.get('tipo')
        descripcion = request.POST.get('descripcion')
        tecnico = request.POST.get('tecnico')
        fecha_str = request.POST.get('fecha')
        
        fecha_final = timezone.now()
        if fecha_str:
            try:
                # El formato de datetime-local es YYYY-MM-DDTHH:MM
                fecha_final = timezone.make_aware(datetime.datetime.strptime(fecha_str, '%Y-%m-%dT%H:%M'))
            except:
                pass
        
        Mantenimiento.objects.create(
            maquina_id=maquina_id,
            tipo=tipo,
            descripcion_falla=descripcion,
            tecnico_asignado=tecnico,
            fecha_reporte=fecha_final,
            estado='ABIERTO'
        )
        messages.success(request, "Incidencia reportada correctamente.")
        return redirect('lista_mantenimiento')
    return redirect('lista_mantenimiento')

def gestionar_incidencia(request, pk):
    """
    Cambia el estado de una incidencia (Iniciar reparación o Finalizar).
    """
    incidencia = get_object_or_404(Mantenimiento, pk=pk)
    accion = request.POST.get('accion')
    
    if accion == 'iniciar':
        incidencia.estado = 'PROCESO'
        incidencia.fecha_inicio_reparacion = timezone.now()
        messages.info(request, f"Se ha iniciado la reparación de la máquina {incidencia.maquina.nombre}.")
    elif accion == 'cerrar':
        incidencia.estado = 'CERRADO'
        incidencia.fecha_fin = timezone.now()
        incidencia.observaciones_tecnicas = request.POST.get('observaciones')
        messages.success(request, f"Reparación finalizada. La máquina {incidencia.maquina.nombre} vuelve a estar operativa.")
        
    incidencia.save()
    return redirect('lista_mantenimiento')

def eliminar_incidencia(request, pk):
    """
    Elimina una incidencia de mantenimiento.
    """
    incidencia = get_object_or_404(Mantenimiento, pk=pk)
    nombre_maq = incidencia.maquina.nombre
    incidencia.delete()
    messages.warning(request, f"Se ha eliminado la incidencia de la máquina {nombre_maq}.")
    return redirect('lista_mantenimiento')

def auditoria_cambios(request):
    logs = AuditLog.objects.all().order_by('-fecha')
    return render(request, 'dashboard/auditoria_cambios.html', {'logs': logs})

def generar_reporte_pdf(request):
    # Reuse dashboard logic to get data
    # Force context return
    # Explicitly extract params to ensure they are passed
    date_param = request.GET.get('date')
    start_param = request.GET.get('start_date')
    end_param = request.GET.get('end_date')
    
    context = dashboard_produccion(request, return_context=True, force_date=date_param, force_start=start_param, force_end=end_param, force_format='clock')
    
    if not isinstance(context, dict):
        return HttpResponse("Error al generar datos del reporte", status=500)

    machines = context.get('cards_data', [])
    operators = context.get('kpis_personal', [])
    
    # Global OEE Average (Active Machines only)
    active_machines = [m for m in machines if m['is_active_production']]
    total_oee = sum([m['oee'] for m in active_machines])
    count_active = len(active_machines)
    global_oee = total_oee / count_active if count_active > 0 else 0
    
    # Top 5 Operators (Dashboard logic sorts them by OEE descending already)
    # But let's make sure
    operators_sorted = sorted(operators, key=lambda x: x['oee'], reverse=True)
    top_operators = operators_sorted[:5]
    
    # Top 5 Downtime Machines (Lowest Availability)
    # Filter only those that had planned time (don't count unused machines as downtime)
    machines_with_work = [m for m in machines if m['horas_std'] > 0 or m['horas_prod'] > 0]
    top_downtime_machines = sorted(machines_with_work, key=lambda x: x['availability'])[:5]
    
    pdf_context = {
        'fecha': context.get('fecha_target'),
        'global_oee': round(global_oee, 2),
        'top_operators': top_operators,
        'top_downtime_machines': top_downtime_machines,
        'machines': machines, # Full list
    }
    
    template_path = 'dashboard/reporte_pdf.html'
    template = get_template(template_path)
    html = template.render(pdf_context)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'filename="reporte_diario.pdf"'

    pisa_status = pisa.CreatePDF(html, dest=response)

    if pisa_status.err:
        return HttpResponse('We had some errors <pre>' + html + '</pre>')
    return response

def estadisticas_avanzadas(request):
    """
    Vista para analíticas visuales e históricas: Trend OEE, Pareto, Ranking.
    """
    days = int(request.GET.get('period', 7))
    
    # Range Definition
    now_local = timezone.localtime(timezone.now())
    today_date = now_local.date()
    start_date = today_date - datetime.timedelta(days=days-1) 

    trend_data = [] 
    global_pareto = {} 
    operator_stats = {} 
    
    # Main Loop over Days (avoiding cross-db aggregation issues)
    for i in range(days):
        d_loop = start_date + datetime.timedelta(days=i)
        
        d_start = timezone.make_aware(datetime.datetime.combine(d_loop, datetime.time.min))
        d_end = timezone.make_aware(datetime.datetime.combine(d_loop, datetime.time.max))
        
        # We need specific filtering per day
        # To match dashboard logic, we convert date
        start_str = d_loop.strftime('%Y-%m-%d')
        qs_day = VTMan.objects.extra(where=["CONVERT(date, FECHA) = %s"], params=[start_str])
        
        # --- Daily Aggregation ---
        aggregation = qs_day.aggregate(
            sum_real=Sum('tiempo_minutos'),
            sum_std=Sum('tiempo_cotizado'),
            count_recs=Count('row_id')
        )
        
        if not aggregation['count_recs']:
            trend_data.append({'date': d_loop.strftime('%d/%m'), 'oee': 0})
            continue
            
        # Active Machines Count
        active_machines_count = qs_day.values('id_maquina').distinct().count() or 1
        
        if d_loop.weekday() == 6: # Skip Sunday from trend visual if 0 (optional)
             trend_data.append({'date': d_loop.strftime('%d/%m'), 'oee': 0})
        else:
            # Approx Global Availability
            total_planned_mins = active_machines_count * 540 # 9 hour shift
            total_real_mins = aggregation['sum_real'] or 0
            
            avail = (total_real_mins / total_planned_mins) if total_planned_mins > 0 else 0
            if avail > 1: avail = 1.0
            
            # Approx Performance
            total_std_hours = aggregation['sum_std'] or 0
            # Get only production time (exclude interruptions) for performance denominator ideally
            prod_mins_only = qs_day.filter(es_interrupcion=False).aggregate(s=Sum('tiempo_minutos'))['s'] or 0
            prod_hours_only = prod_mins_only / 60.0
            
            perf = (total_std_hours / prod_hours_only) if prod_hours_only > 0 else 0
            
            qual = 1.0 # Approximation
            
            oee_day = (avail * perf * qual) * 100
            if oee_day > 100: oee_day = 100
            
            trend_data.append({
                'date': d_loop.strftime('%d/%m'),
                'oee': round(oee_day, 1)
            })

        # --- Pareto Accumulation ---
        # Incluimos también Tareas Generales y Limpieza para que el Pareto sea más completo
        interrupciones = qs_day.filter(
            Q(es_interrupcion=True) | 
            Q(articulod__icontains='DESCANSO') | 
            Q(observaciones__icontains='DESCANSO') |
            Q(articulod__icontains='TAREAS GENERALES') |
            Q(articulod__icontains='LIMPIEZA') |
            Q(articulod__icontains='MANTENIMIENTO')
        )
        for inter in interrupciones:
            # Si es Tareas Generales y tiene observación, usar la observación como razón
            reason_raw = (inter.observaciones or inter.articulod or "S/M").strip().upper()
            
            # Limpieza de strings
            reason = reason_raw.replace("PARADA POR ", "").replace("INTERRUPCION ", "")
            
            # Agrupar Tareas Generales vacías
            if "TAREA" in reason and len(reason) < 20: 
                reason = "TAREAS GENERALES"
                
            if not reason: reason = "OTRO"
            micros = inter.tiempo_minutos or 0
            global_pareto[reason] = global_pareto.get(reason, 0) + micros

        # --- Ranking Accumulation ---
        ops_day = qs_day.values('id_concepto').annotate(
            day_std=Sum('tiempo_cotizado'),
            day_real=Sum('tiempo_minutos'), 
            day_qty=Sum('cantidad_producida'),
            day_recs=Count('row_id')
        )
        
        for od in ops_day:
            uid = od['id_concepto']
            if not uid: continue
            uid = str(uid).strip()
            if uid == 'None': continue
            
            if uid not in operator_stats:
                operator_stats[uid] = {'std': 0, 'real': 0, 'qty': 0}
            
            operator_stats[uid]['std'] += (od['day_std'] or 0)
            operator_stats[uid]['real'] += ((od['day_real'] or 0) / 60.0) 
            operator_stats[uid]['qty'] += (od['day_qty'] or 0)

    # 3. Final Processing
    
    # Pareto Processing
    pareto_sorted = sorted(global_pareto.items(), key=lambda x: x[1], reverse=True)[:10]
    pareto_labels = [p[0] for p in pareto_sorted]
    pareto_values = [round(p[1], 1) for p in pareto_sorted]
    
    # Calculate Cumulative %
    total_downtime = sum([p[1] for p in pareto_sorted])
    pareto_cumulative = []
    current_sum = 0
    for p in pareto_sorted:
        current_sum += p[1]
        perc = (current_sum / total_downtime * 100) if total_downtime > 0 else 0
        pareto_cumulative.append(round(perc, 1))
    
    # Ranking
    ranking_list = []
    from .models import OperarioConfig
    all_ops_db = {o.legajo: o.nombre for o in OperarioConfig.objects.all()}
    
    for uid, stats in operator_stats.items():
        if stats['real'] < 0.5: continue 
        
        perf = (stats['std'] / stats['real']) * 100 if stats['real'] > 0 else 0
        name = all_ops_db.get(uid, f"{uid}")
        
        ranking_list.append({
            'legajo': uid,
            'name': name,
            'oee': round(perf, 1), 
            'total_qty': stats['qty']
        })
    
    ranking_list.sort(key=lambda x: x['oee'], reverse=True)
    
    chart_json = {
        'trend': trend_data,
        'pareto': {
            'labels': pareto_labels, 
            'values': pareto_values,
            'cumulative': pareto_cumulative
        }
    }
    
    return render(request, 'dashboard/estadisticas.html', {
        'period': days,
        'chart_json': json.dumps(chart_json),
        'ranking_data': ranking_list[:20] 
    })

def check_alerts(request):
    """
    API Endpoint JSON para verificar alertas en tiempo real.
    1. Máquinas detenidas > 20 minutos sin incidencia abierta.
    2. (Opcional) OEE Global bajo.
    """
    alerts = []
    
    # 1. Configuración de Máquinas Activas
    machines = MaquinaConfig.objects.filter(activa=True)
    if not machines.exists():
        return JsonResponse({'alerts': []})
        
    machine_map = {m.id_maquina: m.nombre for m in machines}
    
    # 2. Obtener última actividad de las últimas 24hs
    hours_lookback = 24
    start_check = timezone.now() - datetime.timedelta(hours=hours_lookback)
    
    # Agrupamos por id_maquina y buscamos la fecha maxima (fin)
    last_activities = VTMan.objects.filter(
        fecha__gte=start_check, 
        id_maquina__in=machine_map.keys()
    ).values('id_maquina').annotate(last_seen=Max('hora_fin'))
    
    activity_dict = {x['id_maquina']: x['last_seen'] for x in last_activities}
    
    now = timezone.now()
    
    # 3. Tickets de Mantenimiento Activos (ABIERTO o PROCESO)
    # Si hay ticket abierto, no alarmamos por "detención sin justificación"
    open_tickets = Mantenimiento.objects.filter(
        estado__in=['ABIERTO', 'PROCESO']
    ).values_list('maquina__id_maquina', flat=True)
    
    for m in machines.iterator():
        # Saltamos si está en mantenimiento
        if m.id_maquina in open_tickets:
            continue
            
        last_seen = activity_dict.get(m.id_maquina)
        
        if last_seen:
            # Manejo de timezone (por si last_seen viene naive de SQL)
            if timezone.is_naive(last_seen):
                last_seen = timezone.make_aware(last_seen)
            
            # Diferencia en minutos
            diff_mins = (now - last_seen).total_seconds() / 60.0
            
            # UMBRAL: 20 Minutos
            if diff_mins > 20:
                alerts.append({
                    'type': 'error',
                    'title': 'Detención Crítica',
                    'message': f"{m.nombre} lleva {int(diff_mins)} minutos detenida sin notificación."
                })
        else:
            # Opción: Si no hubo actividad en 24hs, ¿es alerta? 
            # Depende del caso de uso. Si es un Lunes a la mañana, no.
            # Por ahora lo ignoramos para evitar falsos positivos al inicio del día.
            pass

    return JsonResponse({'alerts': alerts})

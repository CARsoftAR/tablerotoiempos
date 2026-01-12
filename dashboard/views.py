from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Sum, Q, F
from django.utils import timezone
from datetime import timedelta
from .models import VTMan, Maquina, MaquinaConfig
from django.contrib import messages

def dashboard_produccion(request):
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

    fecha_param = request.GET.get('date') or request.GET.get('fecha')
    start_param = request.GET.get('start_date')
    end_param = request.GET.get('end_date')

    now_local = timezone.localtime(timezone.now())
    today_date = now_local.date()
    
    fecha_target_start = None
    fecha_target_end = None
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

    fecha_str = fecha_target_start.strftime('%Y-%m-%d')

    # Forzar comparación de FECHA como cadena o usando extra() para evitar el desplazamiento de zona horaria de Django
    # que estaba causando que el día 08/01 muestre registros del 09/01 (y pierda los del 08/01 temprano)
    registros_data = VTMan.objects.extra(
        where=["CONVERT(date, FECHA) = %s"],
        params=[fecha_str]
    ).order_by('id_maquina', '-fecha', '-hora_fin').values(
        'id_maquina', 'tiempo_minutos', 'tiempo_cotizado', 'cantidad_producida',
        'es_proceso', 'es_interrupcion', 'observaciones', 'fecha', 'id_orden', 'operacion',
        'articulod', 'id_operacion'
    )

    kpi_por_maquina = {}
    actual_online_ids = set()
    if is_viewing_today:
        online_qs = VTMan.objects.extra(
            where=["CONVERT(date, FECHA) = %s"],
            params=[fecha_str]
        ).filter(observaciones='ONLINE').values_list('id_maquina', flat=True)
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
                'latest_obs': None,
                'latest_date': None,
                'current_order': '---',
                'is_found_online': False # Se decidirá abajo
            }

    # Acumuladores Globales
    unassigned_time = 0.0
    unassigned_qty = 0.0
    unassigned_std = 0.0

    global_planned_time = 0.0 
    global_actual_time = 0.0 
    global_downtime = 0.0
    global_actual_qty = 0.0 # Piezas Buenas
    global_rejected_qty = 0.0 # Reprocesos/Scrap
    global_repro_time = 0.0 # Horas de reproceso

    machine_orders = {} 

    for reg in registros_data:
        mid = reg['id_maquina']
        duracion = reg['tiempo_minutos'] or 0.0
        qty = reg['cantidad_producida'] or 0.0
        std_mins = (reg['tiempo_cotizado'] or 0.0) * 60.0
        
        # Identificar Reproceso o tareas que no deben sumar a Cantidad Real
        raw_id_op = str(reg.get('id_operacion') or "").strip().upper()
        raw_art_d = str(reg.get('articulod') or "").upper()
        raw_op_d = str(reg.get('operacion') or "").strip().upper()
        raw_obs = str(reg.get('observaciones') or "").strip().upper()

        non_prod_keywords = ['REPROCESO', 'RETRABAJO']
        
        is_repro = (
            raw_id_op in non_prod_keywords or 
            raw_op_d in non_prod_keywords or
            any(k in raw_art_d for k in non_prod_keywords) or
            any(k in raw_obs for k in non_prod_keywords)
        )
        
        # El 'ONLINE' a veces trae cantidad 1 para marcar actividad, pero no es producción real terminada
        is_online_record = (raw_obs == 'ONLINE')

        # 1. Caso: Sin Asignar (Máquina vacía o inactiva)
        if not mid or mid in maquinas_inactivas_ids:
            unassigned_time += duracion
            if is_repro:
                global_rejected_qty += qty
                global_repro_time += duracion
            else:
                unassigned_qty += qty
                global_actual_qty += qty
                unassigned_std += std_mins
            continue

        # 2. Caso: Máquina Asignada
        if mid not in kpi_por_maquina:
             kpi_por_maquina[mid] = {
                'id_maquina': mid,
                'nombre_maquina': nombres_maquinas.get(mid, mid),
                'tiempo_operativo': 0.0, 
                'tiempo_paradas': 0.0,
                'tiempo_cotizado': 0.0, 
                'cantidad_producida': 0.0,
                'cantidad_rechazada': 0.0,
                'latest_obs': None,
                'latest_date': None,
                'current_order': '---',
                'is_found_online': False
            }

        data = kpi_por_maquina[mid]
        
        if data['latest_obs'] is None:
            data['latest_obs'] = str(reg['observaciones']).strip().upper() if reg['observaciones'] else ""
            data['latest_date'] = reg['fecha']
            data['current_order'] = reg['id_orden']

        if is_repro:
            data['cantidad_rechazada'] += qty
            global_rejected_qty += qty
            global_repro_time += duracion
            # El tiempo de reproceso cuenta como tiempo real de la máquina
        else:
            data['cantidad_producida'] += qty
            global_actual_qty += qty
            # El tiempo estándar solo suma para piezas de producción real
            data['tiempo_cotizado'] += std_mins
            global_planned_time += std_mins 
        
        if reg['es_proceso']:
            data['tiempo_operativo'] += duracion
            global_actual_time += duracion
        elif reg['es_interrupcion']:
            data['tiempo_paradas'] += duracion
            global_downtime += duracion

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
            return f"{h} hs {m} min" if h > 0 else f"{m} min"

        lista_kpis.append({
            'id_maquina': mid,
            'nombre_maquina': data['nombre_maquina'],
            'is_online': is_online,
            'oee': round(oee, 2),
            'availability': round(availability, 2),
            'performance': round(performance, 2),
            'quality': round(quality, 2),
            'id_orden': data['current_order'],
            'horas_std': t_std_hrs,
            'horas_prod': t_op_hrs,
            'qty': data['cantidad_producida'],
            'rejected_qty': data['cantidad_rechazada'],
            'std_formatted': format_time_display(t_std_hrs),
            'prod_formatted': format_time_display(t_op_hrs),
        })
        
        total_horas_std += t_std_hrs
        total_horas_prod += t_op_hrs
        total_horas_disp += t_disp_periodo 
        global_downtime += max(0, (t_disp_periodo - t_op_hrs) * 60)

    # 4. Globales
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

    for kpi in lista_kpis:
        kpi['is_active_production'] = kpi['horas_prod'] > 0.001
    
    lista_kpis.sort(key=lambda x: (not x['is_online'], not x['is_active_production'], x['id_maquina']))

    maquinas_activas = sum(1 for m in lista_kpis if m['is_online'])
    total_maquinas = len(lista_kpis)

    def fmt_mins_global(m_raw):
        # m_raw está en minutos
        if time_format == 'decimal':
            return f"{m_raw/60.0:.2f}"
        
        h, mins = divmod(int(round(m_raw)), 60)
        return f"{h} hs {mins} min" if h > 0 else f"{mins} min"

    context = {
        'kpis': lista_kpis,
        'fecha_target': fecha_target_start,
        'fecha_fin_target': fecha_target_end,
        'is_today': is_viewing_today,
        'is_range': (fecha_target_start != fecha_target_end),
        'time_format': time_format,
        'resumen': {
            'promedio_oee': round(promedio_oee, 2),
            'avg_availability': round(avg_availability, 2),
            'avg_performance': round(avg_performance, 2),
            'avg_quality': round(avg_quality, 2),
            'avg_rejected': round(100.0 - avg_quality, 2) if total_piezas_real > 0 else 0.0,
            'avg_downtime': round(res_avg_downtime, 2),
            'maquinas_activas': maquinas_activas,
            'total_maquinas': total_maquinas,
            'global_planned_formatted': fmt_mins_global(total_horas_disp * 60),
            'global_actual_formatted': fmt_mins_global(total_horas_prod * 60),
            'global_standard_formatted': fmt_mins_global(total_horas_std * 60),
            'global_downtime_formatted': fmt_mins_global(global_downtime),
            'global_planned_qty': round(global_actual_qty / (avg_performance/100)) if avg_performance > 0 else 0,
            'global_actual_qty': round(global_actual_qty, 1),
            'global_rejected_qty': round(global_rejected_qty, 1),
            'global_repro_time_formatted': fmt_mins_global(global_repro_time),
            # Tiempos Sin Asignar (para la tarjeta aparte)
            'unassigned_time_formatted': fmt_mins_global(unassigned_time),
            'unassigned_qty': round(unassigned_qty, 1),
            'unassigned_std_formatted': fmt_mins_global(unassigned_std),
        }
    }
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

            MaquinaConfig.objects.create(
                id_maquina=id_maquina,
                nombre=nombre,
                activa=request.POST.get('activa') == 'on',
                horario_inicio_sem=request.POST.get('horario_inicio_sem') or '07:00',
                horario_fin_sem=request.POST.get('horario_fin_sem') or '16:00',
                trabaja_sabado=request.POST.get('trabaja_sabado') == 'on',
                horario_inicio_sab=request.POST.get('horario_inicio_sab') or None,
                horario_fin_sab=request.POST.get('horario_fin_sab') or None,
                trabaja_domingo=request.POST.get('trabaja_domingo') == 'on',
                horario_inicio_dom=request.POST.get('horario_inicio_dom') or None,
                horario_fin_dom=request.POST.get('horario_fin_dom') or None,
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
            maquina.trabaja_domingo = request.POST.get('trabaja_domingo') == 'on'
            maquina.horario_inicio_dom = request.POST.get('horario_inicio_dom') or None
            maquina.horario_fin_dom = request.POST.get('horario_fin_dom') or None
            maquina.save()
            messages.success(request, 'Máquina actualizada.')
            
            # Redirigir a la misma página del listado
            return redirect(f"{reverse('gestion_maquinas')}?page={page}")
            
        except Exception as e:
            messages.error(request, f'Error al actualizar: {e}')
            
    return render(request, 'dashboard/form_maquina.html', {'maquina': maquina, 'page': page})

def eliminar_maquina(request, pk):
    maquina = get_object_or_404(MaquinaConfig, pk=pk)
    maquina.delete()
    messages.success(request, 'Máquina eliminada.')
    
    # Mantener en la misma pagina
    page = request.GET.get('page', 1)
    return redirect(f"{reverse('gestion_maquinas')}?page={page}")

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
    
    fecha_param = request.GET.get('date') or request.GET.get('fecha')
    
    found_date = None

    if fecha_param:
        if fecha_param == 'yesterday':
             found_date = timezone.now().date() - datetime.timedelta(days=1)
        elif fecha_param == 'today':
             found_date = timezone.now().date()
        else:
            try:
                found_date = parser.parse(fecha_param).date()
            except:
                found_date = timezone.now().date() - datetime.timedelta(days=1)
    else:
        # Buscar día activo hacia atrás
        check_date = timezone.now().date() - datetime.timedelta(days=1)
        for _ in range(15): # Buscar hasta 15 días atrás
            # Rango UTC para el chequeo
            c_start = datetime.datetime.combine(check_date, datetime.time.min).replace(tzinfo=datetime.timezone.utc)
            c_end = datetime.datetime.combine(check_date, datetime.time.max).replace(tzinfo=datetime.timezone.utc)
            
            # Verificar si hay datos (usando count para light query o exists)
            # Usamos filter directo. count() es rapido.
            if VTMan.objects.filter(fecha__range=(c_start, c_end)).exists():
                found_date = check_date
                break
            
            check_date -= datetime.timedelta(days=1)
        
        # Si no encontramos nada en 15 días, nos quedamos con AYER (aunque esté vacío)
        if not found_date:
            found_date = timezone.now().date() - datetime.timedelta(days=1)

    fecha_target = found_date
    
    # Construir rango definitivo
    start_utc = datetime.datetime.combine(fecha_target, datetime.time.min).replace(tzinfo=datetime.timezone.utc)
    end_utc = datetime.datetime.combine(fecha_target, datetime.time.max).replace(tzinfo=datetime.timezone.utc)
    
    fecha_inicio = start_utc
    fecha_fin = end_utc
    
    # 1. Obtener nombres reales de máquinas
    maquinas_db = Maquina.objects.all()
    nombres_maquinas = {m.id_maquina: m.descripcion for m in maquinas_db}
    
    # Intenta obtener configuraciones locales si existen para enriquecer nombres
    # Y filtrar las NO activas
    maquinas_inactivas_ids = set()
    maquinas_configs = {} # Guardar config para horarios
    try:
        configs_locales = MaquinaConfig.objects.all()
        for conf in configs_locales:
            nombres_maquinas[conf.id_maquina] = conf.nombre
            maquinas_configs[conf.id_maquina] = conf
            if not conf.activa:
                maquinas_inactivas_ids.add(conf.id_maquina)
    except Exception:
        pass # Si falla la tabla local, seguimos con los del ERP

    # 2. Consultar registros de producción (READ-ONLY SQL Server)
    # Usamos .values() para evitar problemas de duplicidad de PK si IDORDEN no es único en la vista
    registros_data = VTMan.objects.filter(
        fecha__range=(fecha_inicio, fecha_fin)
    ).order_by('id_maquina', '-fecha', '-hora_fin').values(
        'id_maquina', 'tiempo_minutos', 'tiempo_cotizado', 'cantidad_producida',
        'es_proceso', 'es_interrupcion', 'observaciones', 'fecha', 'id_orden'
    )

    kpi_por_maquina = {}

    kpi_por_maquina = {}

    # CONSULTA ESPECÍFICA PARA MAQUINAS ONLINE (Segun SQL usuario)
    # Obtenemos ID de Maquina y su OP (IDORDEN)
    online_qs = VTMan.objects.filter(observaciones='ONLINE').values('id_maquina', 'id_orden')
    # Creamos un mapa {id_maquina: id_orden}
    # Si hay duplicados, tomará el último procesado. Idealmente el orden de la query importa, 
    # pero para 'ONLINE' asumimos que es el estado actual.
    online_map = {item['id_maquina']: item['id_orden'] for item in online_qs}

    # Pre-inicializar TODAS las máquinas configuradas y activas (para que aparezcan aunque no tengan datos)
    for mid, conf in maquinas_configs.items():
        if conf.activa:
            is_in_online_map = mid in online_map
            initial_order = online_map[mid] if is_in_online_map else '---'
            
            kpi_por_maquina[mid] = {
                'id_maquina': mid,
                'nombre_maquina': conf.nombre,
                'tiempo_operativo': 0.0,
                'tiempo_paradas': 0.0,
                'tiempo_cotizado': 0.0,
                'cantidad_producida': 0.0,
                'latest_obs': None,
                'latest_date': None,
                'current_order': initial_order,
                'is_found_online': is_in_online_map
            }

    # Acumuladores Globales para el Panel Superior
    global_planned_time = 0.0 # Cotizado / Std
    global_actual_time = 0.0 # Operativo / Prod
    global_downtime = 0.0
    global_actual_qty = 0.0

    # Estructura auxiliar para procesar datos por Orden {mid: {oid: data}}
    machine_orders = {} 

    for reg in registros_data:
        mid = reg['id_maquina']
        if not mid or mid in maquinas_inactivas_ids: continue

        oid = reg['id_orden']
        
        # Inicializar estructura de máquina si no existe
        if mid not in kpi_por_maquina:
             kpi_por_maquina[mid] = {
                'id_maquina': mid,
                'nombre_maquina': nombres_maquinas.get(mid, mid),
                'tiempo_operativo': 0.0, 
                'tiempo_paradas': 0.0,
                'tiempo_cotizado': 0.0, 
                'cantidad_producida': 0.0,
                'latest_obs': None,
                'latest_date': None,
                'current_order': '---',
                'latest_is_process': False, # Status flag based on last record
                'is_found_online': False
            }
             machine_orders[mid] = {}

        data = kpi_por_maquina[mid]
        
        # Estado y Observaciones
        if data['latest_obs'] is None:
            data['latest_obs'] = reg['observaciones']
            data['latest_date'] = reg['fecha']
            if not data['is_found_online']:
                data['current_order'] = oid

        if reg['observaciones'] and str(reg['observaciones']).strip().upper() == 'ONLINE':
            data['is_found_online'] = True
            data['latest_obs'] = 'ONLINE'

        # Agregación por Orden
        if mid not in machine_orders: machine_orders[mid] = {}
        if oid not in machine_orders[mid]:
            machine_orders[mid][oid] = {'total_std_hrs': 0.0, 'qty': 0.0, 'prod_min': 0.0, 'stop_min': 0.0}
            
        order_stats = machine_orders[mid][oid]
        
        # Std y Qty son totales de la orden (repetidos en la vista), tomamos el valor (sobrescribimos)
        # CAMBIO LOGICA (09/01/2026): 'tiempo_cotizado' ES TOTAL HORAS ESTANDAR DEL REPORTE
        val_std_hrs = float(reg['tiempo_cotizado']) if reg['tiempo_cotizado'] else 0.0
        val_qty = float(reg['cantidad_producida']) if reg['cantidad_producida'] else 0.0
        
        order_stats['total_std_hrs'] += val_std_hrs
        order_stats['qty'] += val_qty
            
        duracion = reg['tiempo_minutos'] if reg['tiempo_minutos'] else 0.0
        
        if reg['es_proceso']:
            order_stats['prod_min'] += duracion
        elif reg['es_interrupcion']:
            order_stats['stop_min'] += duracion

    # 2da Pasada: Sumarizar totales por máquina desde los agregados por orden
    for mid, orders in machine_orders.items():
        data = kpi_por_maquina[mid]
        for oid, stats in orders.items():
            data['tiempo_operativo'] += stats['prod_min']
            data['tiempo_paradas'] += stats['stop_min']
            
            # CÁLCULO DE TIEMPO ESTÁNDAR TOTAL
            # RETORNO A LÓGICA USUARIO: 
            # 1. Valor DB es Standard TOTAL del registro en HORAS.
            # 2. Sumamos directo (ya viene multiplicado por qty y en horas)
            total_std_orden = stats['total_std_hrs'] * 60 # Convertir a minutos para sumar a tiempo_cotizado (que esperamos en minutos en data)
            
            data['tiempo_cotizado'] += total_std_orden
            data['cantidad_producida'] += stats['qty']
            
            # Sumar a globales
            global_actual_time += stats['prod_min']
            global_downtime += stats['stop_min']
            global_planned_time += total_std_orden # Sumar total calculado
            global_actual_qty += stats['qty']

    # 3. Calcular KPIs finales
    lista_kpis = []
    
    # --- CÁLCULO DE TIEMPO TRANSCURRIDO DE TURNO (SHIFT TIME) ---
    # --- CÁLCULO DE TIEMPO TRANSCURRIDO (DYNAMICO POR MAQUINA) ---
    weekday = fecha_target.weekday() # 0=Monday, 6=Sunday
    now = timezone.now() # Aware datetime

    # Acumuladores Globales (en Horas)
    total_horas_std = 0.0
    total_horas_prod = 0.0
    total_horas_disp = 0.0

    for mid, data in kpi_por_maquina.items():
        # Valores base en MINUTOS desde DB
        t_op_min = data['tiempo_operativo']
        t_std_min = data['tiempo_cotizado']
        qty = data['cantidad_producida']

        # Convertir a HORAS para igualar formato imagen (ej "4,10")
        t_op_hrs = t_op_min / 60.0
        
        # Tiempo Cotizado ahora son MINUTOS Totales (Std Unit * Qty). Convertir a horas.
        t_std_hrs = t_std_min / 60.0
        
        # Tiempo Disponible de esta máquina (Calculado según CONFIGURACIÓN de horario)
        
        # 1. Obtener Config y Horarios
        config = maquinas_configs.get(mid)
        
        # Defaults
        start_time = datetime.time(7, 0)
        end_time = datetime.time(16, 0)
        works_today = True
        
        if config:
            if weekday < 5: # Lun-Vie
                start_time = config.horario_inicio_sem
                end_time = config.horario_fin_sem
            elif weekday == 5: # Sabado
                if config.trabaja_sabado:
                    start_time = config.horario_inicio_sab or datetime.time(7,0)
                    end_time = config.horario_fin_sab or datetime.time(13,0)
                else:
                    works_today = False
            elif weekday == 6: # Domingo
                if config.trabaja_domingo:
                    start_time = config.horario_inicio_dom or datetime.time(7,0)
                    end_time = config.horario_fin_dom or datetime.time(13,0)
                else:
                    works_today = False
        
        # 2. Calcular Disponibilidad (Horas)
        t_disp_hrs = 0.0
        
        if works_today:
            # Combinar fecha target con horarios para tener datetimes
            # OJO: fecha_target es date. asumo local timezone o naive.
            # Para comparar con 'now' (que es aware UTC o local), mejor hacemos todo aware si es posible
            # O todo naive y comparamos.
            
            # Convertimos 'now' a local date si es necesario para comparar horas
            # Simplemente usaremos horas decimales para simplificar y evitar lios de timezone hoy
            
            def time_to_decimal(t):
                 return t.hour + t.minute/60.0
            
            start_dec = time_to_decimal(start_time)
            end_dec = time_to_decimal(end_time)
            
            if end_dec < start_dec: end_dec += 24.0 # Turno cruza medianoche
            
            full_shift_hrs = end_dec - start_dec
            
            if now.date() == fecha_target:
                # Calcular hora actual decimal
                now_dec = now.hour + now.minute/60.0  # Ojo: esto es hora del servidor (UTC o Local configurado)
                # Asumiendo TIME_ZONE 'America/Argentina/Buenos_Aires' en settings, now.hour será correcto localmente.
                # Si 'now' es UTC pura, podría fallar.
                # USAR 'timezone.localtime(now)' es más seguro
                now_local = timezone.localtime(now)
                now_dec_local = now_local.hour + now_local.minute/60.0

                if now_dec_local < start_dec:
                   t_disp_hrs = 0.0
                elif now_dec_local > end_dec:
                   t_disp_hrs = full_shift_hrs
                else:
                   t_disp_hrs = now_dec_local - start_dec
            else:
                # Dia pasado completo
                t_disp_hrs = full_shift_hrs
        
        # Fallback: Si no trabaja hoy pero hay produccion (horas extra), usar Tiempo Operativo como base
        # o poner minima disponibilidad
        if t_disp_hrs < 0.01:
             if t_op_hrs > 0: t_disp_hrs = t_op_hrs
             else: t_disp_hrs = 0.01
             
        # Fin Calculo Disponibilidad Personalizado
        
        # A. OCUPACION (Availability)
        # Ocupacion = Horas Producidas / Horas Disponibles
        ocupacion = (t_op_hrs / t_disp_hrs) * 100.0
        
        # B. EFICIENCIA (Performance)
        # Eficiencia = Horas STD / Horas Producidas
        # Si no hubo tiempo operativo, eficiencia es 0
        if t_op_hrs > 0:
            eficiencia = (t_std_hrs / t_op_hrs) * 100.0
        else:
            eficiencia = 0.0

        # C. CALIDAD
        # Si produjo algo, asumimos calidad 100%
        quality = 100.0 if qty > 0 else 0.0

        # D. OEE
        # OEE = Ocupacion * Eficiencia * Calidad
        oee = (ocupacion * eficiencia * quality) / 10000.0
        
        # E. ESTADO
        is_online = data['is_found_online']

        # Formateo de Tiempos (Minutos / Horas)
        def format_time_display(hours_val):
            total_minutes = hours_val * 60
            h = int(total_minutes // 60)
            m = int(total_minutes % 60)
            if h > 0:
                return f"{h} hs {m} min"
            return f"{m} min"

        t_std_str = format_time_display(t_std_hrs)
        t_op_str = format_time_display(t_op_hrs)

        lista_kpis.append({
            'id_maquina': mid,
            'nombre_maquina': data['nombre_maquina'],
            'is_online': is_online,
            'oee': round(oee, 2),
            'availability': round(ocupacion, 2),
            'performance': round(eficiencia, 2),
            'quality': round(quality, 2),
            'id_orden': data['current_order'],
            'horas_std': t_std_hrs,
            'horas_prod': t_op_hrs,
            'std_formatted': t_std_str,
            'prod_formatted': t_op_str,
        })
        
        # Sumar a Globales
        total_horas_std += t_std_hrs
        total_horas_prod += t_op_hrs
        total_horas_disp += t_disp_hrs 

    # 4. Calcular KPIs Globales (Promedios Ponderados / Totales)
    
    # OEE General = (Horas STD Globales / Horas Disponibles Globales) * 100 
    if total_horas_disp > 0:
        promedio_oee = (total_horas_std / total_horas_disp) * 100.0
        # Tasa Ocupacion Global
        avg_availability = (total_horas_prod / total_horas_disp) * 100.0 
    else:
        promedio_oee = 0.0
        avg_availability = 0.0
        
    # Eficiencia Global
    if total_horas_prod > 0:
        avg_performance = (total_horas_std / total_horas_prod) * 100.0
    else:
        avg_performance = 0.0
        
    # Calidad Global (Fijo 100 según imagen)
    avg_quality = 100.0
    # Ordenar: Online primero, luego por ID
    # NUEVA LÓGICA (09/01/2026):
    # Clasificar como "Activa" si tiene Tiempo de Producción > 0
    # Ignoramos la etiqueta 'ONLINE' de la DB por ahora.
    for kpi in lista_kpis:
        kpi['is_active_production'] = kpi['horas_prod'] > 0.001
    
    # Ordenar: Primero las que tienen Producción, luego por ID
    lista_kpis.sort(key=lambda x: (not x['is_active_production'], x['id_maquina']))

    maquinas_activas = sum(1 for m in lista_kpis if m['is_online'])
    total_maquinas = len(lista_kpis)

    # Formateo de Minutos Globales
    def fmt_mins_global(m):
        h = int(m // 60)
        mins = int(m % 60)
        if h > 0:
            return f"{h} hs {mins} min"
        return f"{mins} min"

    # Preparar valores formateados
    # global_planned_time viene en HORAS -> Convertir a min
    g_planned_str = fmt_mins_global(global_planned_time * 60)
    # global_actual_time viene en MINUTOS
    g_actual_str = fmt_mins_global(global_actual_time)
    # global_downtime viene en MINUTOS
    g_downtime_str = fmt_mins_global(global_downtime)

    context = {
        'kpis': lista_kpis,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'resumen': {
            'promedio_oee': round(promedio_oee, 2),
            
            'avg_availability': round(avg_availability, 2), # OCUPACION
            'avg_performance': round(avg_performance, 2),   # EFICIENCIA
            'avg_quality': round(avg_quality, 2),           # CALIDAD
            
            # Datos absolutos panel inferior
            'global_available_time': round(total_horas_disp, 2), # Horas Disponibles (Calculadas como turno transcurrido * maquinas)
            
            'maquinas_activas': maquinas_activas,
            'total_maquinas': total_maquinas,
            
            # Totales Globales para Tarjetas
            'global_planned_time': round(global_planned_time * 60, 0),
            'global_actual_time': round(global_actual_time, 0),
            'global_downtime': round(global_downtime, 0),
            
            # Valores Formateados
            'global_planned_formatted': g_planned_str,
            'global_actual_formatted': g_actual_str,
            'global_downtime_formatted': g_downtime_str,

            # Estimación de Cantidad Planificada basándonos en rendimiento promedio
            'global_planned_qty': round(global_actual_qty / (avg_performance/100)) if avg_performance > 0 else 0,
            'global_actual_qty': round(global_actual_qty, 0),
            'global_rejected_qty': 0, # Placeholder
        }
    }
    
    return render(request, 'dashboard/produccion.html', context)


# --- GESTIÓN DE MÁQUINAS (MySQL) ---

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

def gestion_maquinas(request):
    maquinas_list = MaquinaConfig.objects.all().order_by('id_maquina')
    
    # Paginación: 7 máquinas por página
    paginator = Paginator(maquinas_list, 7) 
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
    return redirect('gestion_maquinas')

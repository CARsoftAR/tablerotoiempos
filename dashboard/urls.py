from django.urls import path
from . import views

urlpatterns = [
    path('produccion/', views.dashboard_produccion, name='dashboard_produccion'),
    path('gestion-maquinas/', views.gestion_maquinas, name='gestion_maquinas'),
    path('gestion-maquinas/crear/', views.crear_maquina, name='crear_maquina'),
    path('gestion-maquinas/editar/<int:pk>/', views.editar_maquina, name='editar_maquina'),
    path('gestion-maquinas/eliminar/<int:pk>/', views.eliminar_maquina, name='eliminar_maquina'),
    
    # Gestión de Personal
    path('gestion-personal/', views.gestion_personal, name='gestion_personal'),
    path('gestion-personal/crear/', views.crear_operario, name='crear_operario'),
    path('gestion-personal/editar/<int:pk>/', views.editar_operario, name='editar_operario'),
    path('gestion-personal/eliminar/<int:pk>/', views.eliminar_operario, name='eliminar_operario'),
    
    # Mantenimiento
    path('gestion-mantenimiento/', views.lista_mantenimiento, name='lista_mantenimiento'),
    path('mantenimiento/crear/', views.crear_incidencia, name='crear_incidencia'),
    path('mantenimiento/gestionar/<int:pk>/', views.gestionar_incidencia, name='gestionar_incidencia'),
    path('mantenimiento/eliminar/<int:pk>/', views.eliminar_incidencia, name='eliminar_incidencia'),

    # API Auditoría
    path('obtener-auditoria/', views.obtener_auditoria, name='obtener_auditoria'),
    
    # Reportes y Auditoría General
    path('auditoria-cambios/', views.auditoria_cambios, name='auditoria_cambios'),
    path('generar-reporte-pdf/', views.generar_reporte_pdf, name='generar_reporte_pdf'),
    path('estadisticas/', views.estadisticas_avanzadas, name='estadisticas'),
    path('api/detalle-oee-dia/', views.detalle_oee_dia, name='detalle_oee_dia'),
    
    # API Alertas
    path('api/check-alerts/', views.check_alerts, name='check_alerts'),
    path('gestion-alertas/', views.gestionar_alertas, name='gestionar_alertas'),
    
    # Sistema de Backup
    path('gestion-backups/', views.gestion_backups, name='gestion_backups'),
    path('backup/crear/', views.crear_backup, name='crear_backup'),
    path('backup/restaurar/<int:pk>/', views.restaurar_backup, name='restaurar_backup'),
    path('backup/descargar/<int:pk>/', views.descargar_backup, name='descargar_backup'),
    path('backup/eliminar/<int:pk>/', views.eliminar_backup, name='eliminar_backup'),
    path('backup/sincronizar-github/', views.sincronizar_github, name='sincronizar_github'),
    
    # Mapa de Planta Premium (Geográfico)
    path('mapa-planta/', views.plant_map, name='plant_map'),
    path('api/update-position/', views.update_machine_position, name='update_machine_position'),
    
    # Trazabilidad
    path('trazabilidad/', views.trazabilidad_piezas, name='trazabilidad_piezas'),
    path('api/trace-flow/', views.get_trace_flow, name='get_trace_flow'),
    

    
    # Manual de Usuario
    path('manual/', views.manual_usuario, name='manual_usuario'),
    
    # AI Chat API
    path('api/chat-ia/', views.chat_ia_api, name='chat_ia_api'),
]


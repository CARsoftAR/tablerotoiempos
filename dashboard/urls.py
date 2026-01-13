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

    # API Auditoría
    path('obtener-auditoria/', views.obtener_auditoria, name='obtener_auditoria'),
]

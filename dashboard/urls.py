from django.urls import path
from . import views

urlpatterns = [
    path('produccion/', views.dashboard_produccion, name='dashboard_produccion'),
    path('gestion-maquinas/', views.gestion_maquinas, name='gestion_maquinas'),
    path('gestion-maquinas/crear/', views.crear_maquina, name='crear_maquina'),
    path('gestion-maquinas/editar/<int:pk>/', views.editar_maquina, name='editar_maquina'),
    path('gestion-maquinas/eliminar/<int:pk>/', views.eliminar_maquina, name='eliminar_maquina'),
]

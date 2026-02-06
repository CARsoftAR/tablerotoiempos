from django.contrib import admin
from .models import OperarioConfig

@admin.register(OperarioConfig)
class OperarioConfigAdmin(admin.ModelAdmin):
    list_display = ('legajo', 'nombre', 'sector', 'activo')
    search_fields = ('legajo', 'nombre')
    list_filter = ('sector', 'activo')

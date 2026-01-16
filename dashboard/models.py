from django.db import models
from django.utils import timezone

class VTMan(models.Model):
    use_db = 'sql_server'
    
    # Clave primaria Real de la vista (HAP_ROW_ID) para evitar que Django agrupe registros por IDORDEN
    row_id = models.CharField(db_column='HAP_ROW_ID', primary_key=True, max_length=255)
    id_orden = models.BigIntegerField(db_column='IDORDEN')
    
    id_concepto = models.CharField(db_column='IDCONCEPTO', max_length=50)
    hora_inicio = models.DateTimeField(db_column='HORA_D', null=True, blank=True)
    hora_fin = models.DateTimeField(db_column='HORA_H', null=True, blank=True)
    fecha = models.DateTimeField(db_column='FECHA', null=True, blank=True)
    
    id_maquina = models.CharField(db_column='IDMAQUINA', max_length=50, null=True, blank=True)
    observaciones = models.CharField(db_column='OBS', max_length=255, null=True, blank=True)
    id_operacion = models.CharField(db_column='IDOPERACION', max_length=50, null=True, blank=True)
    operacion = models.CharField(db_column='OPERACION', max_length=100, null=True, blank=True)
    
    tiempo_cotizado_individual = models.FloatField(db_column='Tiempo_cotizado_individual', null=True, blank=True)
    cantidad_producida = models.FloatField(db_column='Cantidad_producida', null=True, blank=True)
    tiempo_minutos = models.FloatField(db_column='Tiempo_minutos', null=True, blank=True)
    tiempo_cotizado = models.FloatField(db_column='Tiempo_cotizado', null=True, blank=True)
    
    es_programado = models.BooleanField(db_column='Es_programado', null=True, blank=True)
    es_no_programado = models.BooleanField(db_column='Es_No_Programado', null=True, blank=True)
    es_interrupcion = models.BooleanField(db_column='Es_interrupcion', null=True, blank=True)
    es_proceso = models.BooleanField(db_column='Es_proceso', null=True, blank=True)
    
    formula = models.CharField(db_column='Formula', max_length=100, null=True, blank=True)
    articulo = models.CharField(db_column='Articulo', max_length=100, null=True, blank=True)
    articulod = models.CharField(db_column='Articulod', max_length=255, null=True, blank=True)
    op_usuario = models.CharField(db_column='Op_usuario', max_length=100, null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'V_TMAN'
        verbose_name = 'Vista Tiempos Manufactura'
        verbose_name_plural = 'Vistas Tiempos Manufactura'

    def __str__(self):
        return f"Orden {self.id_orden} - {self.id_maquina}"

class Maquina(models.Model):
    use_db = 'sql_server'
    id_maquina = models.CharField(db_column='IdMaquina', primary_key=True, max_length=50)
    descripcion = models.CharField(db_column='MaquinaD', max_length=255)

    class Meta:
        managed = False
        db_table = 'TMAN010' # Asumimos nombre tabla o vista, ajustamos si necesario
        verbose_name = 'Maquina SQL Server'
        verbose_name_plural = 'Maquinas SQL Server'

# NUEVO MODELO PARA MYSQL (GESTIÓN DE MÁQUINAS)
class MaquinaConfig(models.Model):
    # Sin 'use_db', irá a 'default' que es MySQL
    id_maquina = models.CharField(max_length=50, unique=True, verbose_name="ID de Máquina (Código)")
    nombre = models.CharField(max_length=100, verbose_name="Nombre Descriptivo")
    activa = models.BooleanField(default=True, verbose_name="Activa en Tablero")
    
    # Horarios Lun-Vie
    horario_inicio_sem = models.TimeField(verbose_name="Inicio Lun-Vie", default="07:00")
    horario_fin_sem = models.TimeField(verbose_name="Fin Lun-Vie", default="16:00")
    
    # Horarios Sabado (Opcional)
    trabaja_sabado = models.BooleanField(default=False)
    horario_inicio_sab = models.TimeField(verbose_name="Inicio Sábado", null=True, blank=True)
    horario_fin_sab = models.TimeField(verbose_name="Fin Sábado", null=True, blank=True)
    
    horario_inicio_dom = models.TimeField(verbose_name="Inicio Domingo", null=True, blank=True)
    horario_fin_dom = models.TimeField(verbose_name="Fin Domingo", null=True, blank=True)

    # Mantenimiento Preventivo
    frecuencia_preventivo_horas = models.IntegerField(default=0, verbose_name="Frecuencia Service (Hs)", help_text="0 = Desactivado")
    fecha_ultimo_preventivo = models.DateTimeField(null=True, blank=True, verbose_name="Fecha Último Service")
    fecha_proximo_preventivo = models.DateField(null=True, blank=True, verbose_name="Fecha Próximo Service (Agenda)")

    class Meta:
        managed = True
        db_table = 'maquina_config'
        verbose_name = 'Configuración de Máquina'
        verbose_name_plural = 'Configuraciones de Máquinas'

    def __str__(self):
        return f"{self.nombre} ({self.id_maquina})"

class OperarioConfig(models.Model):
    # Sin 'use_db', irá a 'default' que es MySQL
    legajo = models.CharField(max_length=50, unique=True, verbose_name="Legajo")
    nombre = models.CharField(max_length=150, verbose_name="Nombre Completo")
    sector = models.CharField(max_length=100, default="PRODUCCION", verbose_name="Sector")
    activo = models.BooleanField(default=True, verbose_name="Activo")

    class Meta:
        managed = True
        db_table = 'operario_config'
        verbose_name = 'Configuración de Operario'
        verbose_name_plural = 'Configuraciones de Operarios'

    def __str__(self):
        return f"{self.nombre} ({self.legajo})"

class Mantenimiento(models.Model):
    TIPO_CHOICES = [
        ('CORRECTIVO', 'Correctivo (Rotura)'),
        ('PREVENTIVO', 'Preventivo (Programado)'),
        ('MEJORA', 'Mejora / Instalación'),
    ]
    ESTADO_CHOICES = [
        ('ABIERTO', 'Pendiente / Averiada'),
        ('PROCESO', 'En Reparación'),
        ('CERRADO', 'Reparada / Finalizada'),
    ]
    maquina = models.ForeignKey(MaquinaConfig, on_delete=models.CASCADE, related_name='mantenimientos')
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='CORRECTIVO')
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='ABIERTO')
    descripcion_falla = models.TextField(verbose_name="Descripción de la Falla")
    fecha_reporte = models.DateTimeField(default=timezone.now, verbose_name="Fecha del Reporte/Falla")
    fecha_inicio_reparacion = models.DateTimeField(null=True, blank=True)
    fecha_fin = models.DateTimeField(null=True, blank=True)
    tecnico_asignado = models.CharField(max_length=100, null=True, blank=True)
    observaciones_tecnicas = models.TextField(null=True, blank=True)

    class Meta:
        managed = True
        db_table = 'mantenimiento_incidencias'
        verbose_name = 'Incidencia de Mantenimiento'
        verbose_name_plural = 'Incidencias de Mantenimiento'

    def __str__(self):
        return f"{self.maquina.nombre} - {self.tipo} ({self.estado})"

    @property
    def duracion_minutos(self):
        if not self.fecha_fin:
            return 0
        diff = self.fecha_fin - self.fecha_reporte
        return int(diff.total_seconds() / 60)
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User

class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('CREATE', 'Creación'),
        ('UPDATE', 'Actualización'),
        ('DELETE', 'Eliminación'),
    ]
    
    usuario = models.CharField(max_length=100, null=True, blank=True, verbose_name="Usuario")
    modelo = models.CharField(max_length=50, verbose_name="Entidad Afectada") # Ej: MaquinaConfig, Incidencia
    referencia_id = models.CharField(max_length=100, verbose_name="ID Referencia") # ID del objeto
    accion = models.CharField(max_length=20, choices=ACTION_CHOICES)
    detalle = models.TextField(verbose_name="Detalle del Cambio") # JSON or Text description of what changed
    fecha = models.DateTimeField(default=timezone.now)

    class Meta:
        managed = True
        db_table = 'audit_log_cambios'
        verbose_name = 'Registro de Auditoría'
        verbose_name_plural = 'Registros de Auditoría'
        ordering = ['-fecha']

    def __str__(self):
        return f"{self.fecha} - {self.usuario} - {self.accion} {self.modelo}"

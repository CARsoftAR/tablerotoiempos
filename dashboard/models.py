from django.db import models
from django.utils import timezone
import datetime

class VTMan(models.Model):
    use_db = 'sql_server'
    
    row_id = models.CharField(db_column='HAP_ROW_ID', primary_key=True, max_length=255)
    id_orden = models.BigIntegerField(db_column='IDORDEN')
    
    id_concepto = models.CharField(db_column='IDCONCEPTO', max_length=50)
    concepto = models.CharField(db_column='CONCEPTO', max_length=150, null=True, blank=True)
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
        db_table = 'TMAN010'
        verbose_name = 'Maquina SQL Server'
        verbose_name_plural = 'Maquinas SQL Server'

class MaquinaConfig(models.Model):
    id_maquina = models.CharField(max_length=50, unique=True, verbose_name="ID de Máquina (Código)")
    nombre = models.CharField(max_length=100, verbose_name="Nombre Descriptivo")
    proceso_predeterminado = models.CharField(max_length=100, null=True, blank=True, verbose_name="Proceso Default")
    activa = models.BooleanField(default=True, verbose_name="Activa")

    TIPO_MAQUINA_CHOICES = [
        ('GENERICO', 'Genérico (Círculo)'),
        ('CNC', 'CNC (Cuadrado)'),
        ('TORNO', 'Torno (Rectángulo)'),
        ('AGUJEREADORA', 'Agujereadora (Rectángulo)'),
        ('ROBOT', 'Robot (Círculo)'),
        ('PRENSA', 'Prensa (Rectángulo)'),
    ]
    tipo_maquina = models.CharField(max_length=20, choices=TIPO_MAQUINA_CHOICES, default='GENERICO', verbose_name="Tipo de Máquina")
    
    pos_x = models.FloatField(default=0.0, verbose_name="Posición X (%)")
    pos_y = models.FloatField(default=0.0, verbose_name="Posición Y (%)")
    dim_width = models.FloatField(default=4.0, verbose_name="Ancho (%)")
    dim_height = models.FloatField(default=4.0, verbose_name="Alto (%)")
    rotacion = models.FloatField(default=0.0, verbose_name="Rotación (Grados)")
    label_size = models.FloatField(default=13.0, verbose_name="Tamaño Letra (px)")
    border_weight = models.FloatField(default=2.0, verbose_name="Grosor Línea (px)")
    visible_en_mapa = models.BooleanField(default=True, verbose_name="Visible en Mapa")
    
    horario_inicio_sem = models.TimeField(verbose_name="Inicio Lun-Vie", default="07:00")
    horario_fin_sem = models.TimeField(verbose_name="Fin Lun-Vie", default="16:00")
    trabaja_sabado = models.BooleanField(default=False)
    horario_inicio_sab = models.TimeField(verbose_name="Inicio Sábado", null=True, blank=True)
    horario_fin_sab = models.TimeField(verbose_name="Fin Sábado", null=True, blank=True)
    trabaja_domingo = models.BooleanField(default=False)
    horario_inicio_dom = models.TimeField(verbose_name="Inicio Domingo", null=True, blank=True)
    horario_fin_dom = models.TimeField(verbose_name="Fin Domingo", null=True, blank=True)

    frecuencia_preventivo_horas = models.IntegerField(default=0, verbose_name="Frecuencia Preventiva (Horas)")
    fecha_ultimo_preventivo = models.DateTimeField(null=True, blank=True, verbose_name="Último Preventivo")
    fecha_proximo_preventivo = models.DateField(null=True, blank=True, verbose_name="Próximo Preventivo")

    class Meta:
        db_table = 'maquina_config'
        verbose_name = 'Configuración de Máquina'
        verbose_name_plural = 'Configuraciones de Máquinas'

    def __str__(self):
        return f"{self.nombre} ({self.id_maquina})"

class NotificacionConfig(models.Model):
    telegram_token = models.CharField(max_length=255, blank=True, null=True, verbose_name="Token Bot Telegram")
    telegram_chat_id = models.CharField(max_length=100, blank=True, null=True, verbose_name="Chat ID Telegram")
    activar_telegram = models.BooleanField(default=False)
    
    whatsapp_phone = models.CharField(max_length=50, blank=True, null=True, verbose_name="Número Destino WhatsApp")
    whatsapp_apikey = models.CharField(max_length=255, blank=True, null=True, verbose_name="API Key WhatsApp", db_column='whatsapp_apikey')
    activar_whatsapp = models.BooleanField(default=False)
    
    minutos_detencion_critica = models.IntegerField(default=60, verbose_name="Mins para Alerta Detención Crítica")
    alertar_mantenimiento = models.BooleanField(default=True, verbose_name="Alertar Mantenimiento")
    ultima_modificacion = models.DateTimeField(auto_now=True, db_column='ultima_modificacion')

    class Meta:
        db_table = 'notificacion_config'
        verbose_name = 'Configuración de Notificaciones'

    def __str__(self):
        return "Configuración de Notificaciones"

    @classmethod
    def get_solo(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj

class AlertaHistorial(models.Model):
    tipo = models.CharField(max_length=50)
    mensaje = models.TextField()
    fecha_creacion = models.DateTimeField(auto_now_add=True, db_column='fecha_creacion')
    fecha_notificacion_ext = models.DateTimeField(null=True, blank=True, db_column='fecha_notificacion_ext')
    resuelta = models.BooleanField(default=False)
    maquina_id = models.BigIntegerField(null=True, blank=True)

    class Meta:
        db_table = 'alerta_historial'
        verbose_name = 'Historial de Alerta'

    def __str__(self):
        return f"{self.tipo} - {self.fecha_creacion.strftime('%d/%m %H:%M')}"

class Mantenimiento(models.Model):
    maquina = models.ForeignKey(MaquinaConfig, on_delete=models.CASCADE, related_name='mantenimientos')
    fecha_reporte = models.DateTimeField(auto_now_add=True)
    fecha_fin = models.DateTimeField(null=True, blank=True)
    estado = models.CharField(max_length=20, default='ABIERTO', choices=[
        ('ABIERTO', 'Abierto'),
        ('PROCESO', 'En Proceso'),
        ('CERRADO', 'Cerrado')
    ])
    tipo = models.CharField(max_length=50, default='CORRECTIVO')
    tecnico_asignado = models.CharField(max_length=100, null=True, blank=True)
    descripcion_falla = models.TextField()
    detalle_resolucion = models.TextField(null=True, blank=True, db_column='observaciones_tecnicas')
    fecha_inicio_reparacion = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'mantenimiento_incidencias'
        verbose_name = 'Incidencia de Mantenimiento'

    def __str__(self):
        return f"{self.maquina} - {self.fecha_reporte}"

class AuditLog(models.Model):
    usuario = models.CharField(max_length=100, null=True, blank=True, verbose_name="Usuario")
    modelo = models.CharField(max_length=50, verbose_name="Entidad Afectada", default='N/A')
    referencia_id = models.CharField(max_length=100, verbose_name="ID Referencia", default='0')
    accion = models.CharField(max_length=20, choices=[('CREATE', 'Creación'), ('UPDATE', 'Actualización'), ('DELETE', 'Eliminación')], default='UPDATE')
    detalle = models.TextField(verbose_name='Detalle del Cambio', null=True, blank=True)
    fecha = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'audit_log_cambios'
        verbose_name = 'Registro de Auditoría'
        verbose_name_plural = 'Registros de Auditoría'
        ordering = ['-fecha']

    def __str__(self):
        return f"{self.fecha} - {self.accion} - {self.modelo}"

class BackupHistorial(models.Model):
    fecha_creacion = models.DateTimeField(auto_now_add=True, db_column='fecha_creacion')
    tipo = models.CharField(max_length=20) # MYSQL, COMPLETO
    estado = models.CharField(max_length=20, default='EXITOSO')
    usuario = models.CharField(max_length=100, null=True, blank=True)
    notas = models.TextField(blank=True, null=True)
    
    archivo_db = models.CharField(max_length=255, null=True, blank=True)
    tamano_db_mb = models.FloatField(default=0.0)
    
    archivo_codigo = models.CharField(max_length=255, null=True, blank=True)
    tamano_codigo_mb = models.FloatField(default=0.0)
    
    class Meta:
        db_table = 'backup_historial'
        verbose_name = 'Historial de Backup'

    @property
    def tamano_total_mb(self):
        return (self.tamano_db_mb or 0) + (self.tamano_codigo_mb or 0)

    def __str__(self):
        return f"Backup {self.fecha_creacion.strftime('%d/%m/%Y %H:%M')}"


class OperarioConfig(models.Model):
    legajo = models.CharField(max_length=50, unique=True, verbose_name="Legajo (ID ERP)")
    nombre = models.CharField(max_length=150, verbose_name="Nombre Completo")
    activo = models.BooleanField(default=True)
    en_vacaciones = models.BooleanField(default=False, verbose_name="En Vacaciones")
    sector = models.CharField(max_length=50, default='PRODUCCION')

    class Meta:
        db_table = 'operario_config'
        verbose_name = 'Configuración de Operario'

    def __str__(self):
        return f"{self.nombre} ({self.legajo})"

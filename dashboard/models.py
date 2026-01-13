from django.db import models

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
    
    # Horarios Domingo (Opcional)
    trabaja_domingo = models.BooleanField(default=False)
    horario_inicio_dom = models.TimeField(verbose_name="Inicio Domingo", null=True, blank=True)
    horario_fin_dom = models.TimeField(verbose_name="Fin Domingo", null=True, blank=True)

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

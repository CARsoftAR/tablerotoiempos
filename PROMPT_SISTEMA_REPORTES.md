# PROMPT: Sistema de Reportes Crystal Reports - ABBAMAT

## 🎯 OBJETIVO DEL NUEVO PROYECTO
Crear un sistema separado e independiente para **abrir e imprimir reportes Crystal Reports existentes** basado en datos del ERP. 

### Flujo de Trabajo
1. Usuario ingresa un **Número de Orden de Producción (OP)**
2. Sistema consulta la base de datos del ERP para obtener el **código de Artículo** asociado a esa OP
3. Sistema localiza el archivo Crystal Reports en: **`C:\Reportes\{ARTICULO}.rpt`**
   - Ejemplo: Si el artículo es `PCVAC109001X1001`, busca `C:\Reportes\PCVAC109001X1001.rpt`
4. Sistema **abre/imprime** el reporte Crystal correspondiente

**IMPORTANTE:** Los reportes Crystal (.rpt) **YA EXISTEN** y están almacenados en `C:\Reportes\`. El nombre del archivo coincide exactamente con el código del artículo.

---

## 📋 CONTEXTO DEL SISTEMA ACTUAL (ABBAMAT - Tablero OT Tiempos)

### Ubicación del Proyecto Actual
**Path:** `c:\Sistemas ABBAMAT\tablerotoiempos\`

### Stack Tecnológico Actual
- **Framework:** Django 5.2
- **Python:** 3.13
- **Base de Datos Principal:** MySQL (Configuración, Personal, Auditoría)
- **Base de Datos ERP:** SQL Server (Datos de producción en tiempo real)
- **Frontend:** TailwindCSS + Vanilla JavaScript

---

## 🔌 CONEXIÓN A SQL SERVER (ERP)

### Configuración Existente
**Archivo:** `c:\Sistemas ABBAMAT\tablerotoiempos\core\settings.py`

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'tablero_produccion',
        'USER': 'root',
        'PASSWORD': '',
        'HOST': '127.0.0.1',
        'PORT': '3306',
    },
    'sql_server': {
        'ENGINE': 'mssql',
        'NAME': 'HAPAG',           # Nombre de la base de datos del ERP
        'USER': 'sa',
        'PASSWORD': 'hapag',
        'HOST': 'HAPAG\\HAPAG',    # Servidor SQL Server del ERP
        'PORT': '',
        'OPTIONS': {
            'driver': 'ODBC Driver 17 for SQL Server',
            'extra_params': 'TrustServerCertificate=yes'
        },
    }
}
```

### Cómo se Consulta SQL Server en Django
```python
from dashboard.models import VTMan

# Consulta a SQL Server (ERP)
datos_erp = VTMan.objects.using('sql_server').filter(
    id_orden=numero_op
).values('articulo', 'articulod', 'id_maquina', 'cantidad_producida')
```

---

## 📊 ESTRUCTURA DE LA VISTA PRINCIPAL DEL ERP

### Vista: `V_TMAN` (SQL Server - Base de datos HAPAG)
Esta vista contiene TODOS los registros de tiempos de manufactura del ERP.

**Modelo Django:** `dashboard/models.py` → Clase `VTMan`

**Campos Principales:**
```python
class VTMan(models.Model):
    use_db = 'sql_server'  # ← Indica que consulta SQL Server
    
    row_id = models.CharField(db_column='HAP_ROW_ID', primary_key=True)
    id_orden = models.BigIntegerField(db_column='IDORDEN')          # ← NÚMERO DE OP
    
    # DATOS DEL ARTÍCULO (LO QUE NECESITÁS PARA EL REPORTE)
    articulo = models.CharField(db_column='Articulo', max_length=100)
    articulod = models.CharField(db_column='Articulod', max_length=255)  # Descripción
    
    # OTROS DATOS ÚTILES
    id_concepto = models.CharField(db_column='IDCONCEPTO', max_length=50)
    concepto = models.CharField(db_column='CONCEPTO', max_length=150)
    hora_inicio = models.DateTimeField(db_column='HORA_D')
    hora_fin = models.DateTimeField(db_column='HORA_H')
    fecha = models.DateTimeField(db_column='FECHA')
    id_maquina = models.CharField(db_column='IDMAQUINA', max_length=50)
    id_operacion = models.CharField(db_column='IDOPERACION', max_length=50)
    operacion = models.CharField(db_column='OPERACION', max_length=100)
    tiempo_cotizado_individual = models.FloatField(db_column='Tiempo_cotizado_individual')
    cantidad_producida = models.FloatField(db_column='Cantidad_producida')
    tiempo_minutos = models.FloatField(db_column='Tiempo_minutos')
    formula = models.CharField(db_column='Formula', max_length=100)
    op_usuario = models.CharField(db_column='Op_usuario', max_length=100)  # Legajo operario

    class Meta:
        managed = False
        db_table = 'V_TMAN'  # ← Nombre de la vista en SQL Server
```

---

## 🔍 EJEMPLO DE CONSULTA: Obtener Artículo por Número de OP

```python
from django.db import models
from dashboard.models import VTMan

def obtener_articulo_por_op(numero_op):
    """
    Dado un número de OP, retorna el artículo y descripción.
    
    Args:
        numero_op (int): Número de Orden de Producción
        
    Returns:
        dict: {'articulo': 'ART001', 'articulod': 'Descripción del artículo'}
    """
    registro = VTMan.objects.using('sql_server').filter(
        id_orden=numero_op
    ).values('articulo', 'articulod').first()
    
    return registro
```

**Resultado Ejemplo:**
```python
{
    'articulo': '0001-3008', 
    'articulod': 'TAPA CILINDRO NEUMÁTICO 40MM'
}
```

---

## 📦 DATOS ADICIONALES DISPONIBLES EN EL ERP

Si necesitás más datos para el reporte Crystal, todo está disponible en `V_TMAN`:

### Por Orden de Producción
```python
VTMan.objects.using('sql_server').filter(id_orden=12345)
```

### Agrupado por Máquina
```python
VTMan.objects.using('sql_server').values('id_maquina').annotate(
    total_piezas=models.Sum('cantidad_producida')
)
```

### Filtrado por Fechas
```python
from django.utils import timezone
import datetime

hoy = timezone.localtime(timezone.now()).date()
VTMan.objects.using('sql_server').filter(
    fecha__gte=hoy,
    id_orden=12345
)
```

---

## 🎨 REQUISITOS DEL NUEVO SISTEMA DE REPORTES

### Funcionalidades Requeridas
1. **Interfaz Web Simple:**
   - Input para ingresar Número de OP
   - Botón "Buscar y Abrir Reporte"
   
2. **Lógica Backend:**
   - Consultar `V_TMAN` en SQL Server con el número de OP
   - Obtener el campo `articulo` (código del artículo)
   - Construir ruta del archivo: `C:\Reportes\{articulo}.rpt`
   - Verificar si el archivo existe
   - Si existe: Abrir/Imprimir el reporte Crystal
   - Si NO existe: Mostrar mensaje de error
   
3. **Integración con Crystal Reports:**
   - Abrir archivos .rpt existentes desde Python
   - Opciones:
     - **Método 1 (Recomendado):** Usar `pywin32` para invocar Crystal Reports via COM
     - **Método 2:** Ejecutar Crystal Reports desde línea de comandos
     - **Método 3:** Usar subprocess para llamar a `crw32.exe` (Crystal Reports Viewer)

### Ejemplo de Lógica Python

```python
import os
from dashboard.models import VTMan

def abrir_reporte_por_op(numero_op):
    """
    Busca y abre el reporte Crystal correspondiente a una OP.
    
    Args:
        numero_op (int): Número de Orden de Producción
        
    Returns:
        dict: {'success': bool, 'message': str, 'ruta_reporte': str}
    """
    # 1. Obtener artículo desde ERP
    registro = VTMan.objects.using('sql_server').filter(
        id_orden=numero_op
    ).values('articulo').first()
    
    if not registro:
        return {'success': False, 'message': 'OP no encontrada en el sistema'}
    
    articulo = registro['articulo']
    
    # 2. Construir ruta del reporte
    ruta_reporte = f"C:\\Reportes\\{articulo}.rpt"
    
    # 3. Verificar existencia
    if not os.path.exists(ruta_reporte):
        return {
            'success': False, 
            'message': f'Reporte no encontrado: {articulo}.rpt'
        }
    
    # 4. Abrir Crystal Reports
    try:
        # Opción A: Usando Windows COM
        import win32com.client
        crapp = win32com.client.Dispatch("CrystalRuntime.Application")
        report = crapp.OpenReport(ruta_reporte)
        report.PrintOut()
        
        return {
            'success': True, 
            'message': f'Reporte {articulo}.rpt enviado a impresora',
            'ruta_reporte': ruta_reporte
        }
        
    except Exception as e:
        return {'success': False, 'message': f'Error al abrir reporte: {str(e)}'}
```

---

## 🗂️ ESTRUCTURA SUGERIDA PARA EL NUEVO PROYECTO

```
c:\Sistemas ABBAMAT\reportes_crystal\
├── core/                   # Configuración Django
│   ├── settings.py         # ← Copiar configuración DB de 'tablerotoiempos'
│   └── urls.py
├── reportes/               # App principal
│   ├── models.py           # ← Importar/copiar modelo VTMan
│   ├── views.py            # ← Lógica de reportes
│   ├── templates/
│   │   └── buscar_op.html  # Formulario de búsqueda
│   └── crystal_reports/    # Archivos .rpt
│       └── orden_produccion.rpt
├── manage.py
└── requirements.txt
```

---

## 🔧 DEPENDENCIAS A INSTALAR

```txt
Django==5.2
mssql-django==1.4
pyodbc
pywin32                # Para invocar Crystal Reports via COM
python-dotenv          # Para variables de entorno
```

### Software Requerido en el Sistema
- **ODBC Driver 17 for SQL Server** (ya instalado)
- **Crystal Reports Runtime** o **Crystal Reports Viewer** (para abrir/imprimir archivos .rpt)

---

## 📝 NOTAS IMPORTANTES

1. **Ubicación de Reportes:** Todos los archivos .rpt deben estar en `C:\Reportes\`

2. **Nomenclatura de Archivos:** El nombre del archivo .rpt debe coincidir **EXACTAMENTE** con el código de artículo retornado por la consulta SQL.
   - Si el artículo es `PCVAC109001X1001`, el archivo debe ser `PCVAC109001X1001.rpt`
   - **No usar espacios ni caracteres especiales** en los nombres de archivo

3. **Múltiples Registros por OP:** Una OP puede tener múltiples registros en `V_TMAN` (diferentes operaciones). El sistema tomará el primer registro encontrado para obtener el código de artículo.

4. **Manejo de Errores:**
   - OP no existe en el ERP → Mensaje: "Orden no encontrada"
   - Archivo .rpt no existe → Mensaje: "Reporte no disponible para el artículo {ARTICULO}"
   - Error al abrir Crystal → Mensaje técnico del error

5. **Zona Horaria:** El ERP guarda timestamps en UTC. El sistema actual usa `America/Argentina/Buenos_Aires`.

6. **IDs de Concepto:** En `V_TMAN`, `id_concepto='10'` = Tiempo de Producción (proceso).

---

## 🚀 PRÓXIMOS PASOS SUGERIDOS

1. **Crear proyecto Django nuevo** (`django-admin startproject reportes_crystal`)
2. **Copiar configuración de BD** desde `tablerotoiempos/core/settings.py`
3. **Copiar modelo `VTMan`** desde `tablerotoiempos/dashboard/models.py`
4. **Crear vista de búsqueda** que reciba número de OP y localice el archivo .rpt
5. **Implementar invocación de Crystal Reports** (usar pywin32 o subprocess)
6. **Agregar manejo de errores robusto** (OP inexistente, archivo faltante, error de impresión)
7. **Desplegar en servidor local** (misma máquina que el tablero actual)

---

## 🖨️ MÉTODOS ALTERNATIVOS PARA ABRIR CRYSTAL REPORTS

### Método 1: COM (Recomendado)
```python
import win32com.client
crapp = win32com.client.Dispatch("CrystalRuntime.Application")
report = crapp.OpenReport(ruta_reporte)
report.PrintOut()  # Imprimir directo
# o
report.Export()    # Exportar a PDF
```

### Método 2: Subprocess (Viewer)
```python
import subprocess
subprocess.Popen([
    r"C:\Program Files\Business Objects\Crystal Reports Viewer\crw32.exe",
    ruta_reporte
])
```

### Método 3: Abrir con aplicación predeterminada
```python
import os
os.startfile(ruta_reporte)  # Abre con la aplicación asociada a .rpt
```

---

## ❓ INFORMACIÓN ADICIONAL QUE PUEDO NECESITAR

Cuando arranquemos, necesitaré saber:
- ¿Qué versión de Crystal Reports está instalada en el sistema?
- ¿El sistema debe imprimir directamente o mostrar preview al usuario?
- ¿Hay una impresora predeterminada configurada?
- ¿Qué hacer si un artículo no tiene su .rpt correspondiente?
- ¿El sistema debe correr en la misma PC que el tablero actual?
- ¿Se necesita autenticación/control de acceso?

---

**CREADO POR:** Sistema ABBAMAT - Tablero OT Tiempos  
**FECHA:** 2026-02-03  
**VERSIÓN:** 2.0 (Actualizado - Sistema de Localización de Reportes)


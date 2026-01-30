# 🔒 Sistema de Backup ABBAMAT

Sistema completo de respaldo y recuperación para el Tablero de Tiempos.

## 📋 Archivos Incluidos

### 1. `crear_Backup.bat` - Crear Backup Manual
Crea un backup completo del sistema incluyendo:
- ✅ Base de datos MySQL (configuración de máquinas, operarios, mantenimiento)
- ✅ Código fuente completo del sistema
- ✅ Limpieza automática (mantiene últimos 10 backups)

**Uso:**
```
Doble clic en crear_Backup.bat
```

**Archivos generados:**
- `backups/DB_MySQL_YYYYMMDD_HHMMSS.sql` - Backup de base de datos
- `backups/Sistema_Completo_YYYYMMDD_HHMMSS.zip` - Backup del código

---

### 2. `restaurar_Backup.bat` - Restaurar Backup
Restaura la base de datos desde un backup anterior.

**Uso:**
```
1. Doble clic en restaurar_Backup.bat
2. Selecciona el backup a restaurar
3. Confirma la operación (escribe "SI")
```

⚠️ **ADVERTENCIA:** Esta operación sobrescribirá la base de datos actual.

---

### 3. `configurar_Backup_Automatico.bat` - Backup Automático
Configura backups automáticos programados usando Windows Task Scheduler.

**Uso:**
```
1. Clic derecho → "Ejecutar como administrador"
2. Selecciona el horario deseado:
   - Diario a las 23:00
   - Diario a las 02:00 (madrugada)
   - Cada 12 horas
   - Personalizado
```

**Para eliminar:**
- Ejecuta el script y selecciona opción [5]

---

## 📁 Estructura de Backups

```
tablerotoiempos/
├── backups/
│   ├── DB_MySQL_20260130_143000.sql
│   ├── DB_MySQL_20260129_230000.sql
│   ├── Sistema_Completo_20260130_143000.zip
│   └── Sistema_Completo_20260129_230000.zip
├── crear_Backup.bat
├── restaurar_Backup.bat
└── configurar_Backup_Automatico.bat
```

---

## 🔧 Requisitos

### Para Backup de Base de Datos:
- MySQL instalado con `mysqldump` y `mysql` en el PATH del sistema
- Archivo `.env` configurado con credenciales de MySQL

### Para Backup del Código:
- PowerShell (incluido en Windows 7+)

### Para Backup Automático:
- Permisos de Administrador
- Windows Task Scheduler habilitado

---

## 📝 Configuración de Variables

El sistema lee automáticamente las credenciales desde el archivo `.env`:

```env
MYSQL_DB_NAME=tablerotiempos
MYSQL_USER=root
MYSQL_PASSWORD=tu_password
MYSQL_HOST=localhost
MYSQL_PORT=3306
```

---

## 🚀 Mejores Prácticas

### 1. Backup Regular
- Configura backups automáticos diarios
- Recomendado: 23:00 o 02:00 (fuera de horario laboral)

### 2. Verificación
- Verifica periódicamente que los backups se estén creando
- Revisa la carpeta `backups/` semanalmente

### 3. Backup Externo
- Copia periódicamente la carpeta `backups/` a:
  - Disco externo
  - Servidor de red
  - Nube (Google Drive, OneDrive, etc.)

### 4. Antes de Actualizaciones
- Siempre crea un backup manual antes de:
  - Actualizar el sistema
  - Modificar la base de datos
  - Instalar nuevas dependencias

### 5. Prueba de Restauración
- Realiza pruebas de restauración periódicas
- Verifica que los backups sean funcionales

---

## 🔍 Solución de Problemas

### Error: "mysqldump no se reconoce como comando"
**Solución:** Agrega MySQL al PATH del sistema
```
1. Panel de Control → Sistema → Configuración avanzada
2. Variables de entorno
3. Editar PATH
4. Agregar: C:\Program Files\MySQL\MySQL Server X.X\bin
```

### Error: "Acceso denegado" al configurar backup automático
**Solución:** Ejecuta el script como Administrador
```
Clic derecho → "Ejecutar como administrador"
```

### Los backups ocupan mucho espacio
**Solución:** El sistema mantiene automáticamente solo los últimos 10 backups.
Para cambiar este límite, edita `crear_Backup.bat` y modifica:
```batch
if %COUNT% gtr 10 (
```
Cambia `10` por el número deseado.

---

## 📊 Monitoreo

### Ver tareas programadas:
```
1. Win + R
2. Escribe: taskschd.msc
3. Busca: ABBAMAT_Backup
```

### Ver logs de backups:
Los backups se ejecutan silenciosamente. Para ver logs:
```
1. Abre el Programador de tareas
2. Busca la tarea ABBAMAT_Backup
3. Pestaña "Historial"
```

---

## 🆘 Soporte

Para problemas o consultas:
- Revisa este README
- Verifica el archivo `.env`
- Contacta al administrador del sistema

---

## 📜 Licencia

Sistema desarrollado para ABBAMAT - Tablero de Tiempos
© 2026 - Todos los derechos reservados

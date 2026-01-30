@echo off
REM ========================================
REM  ABBAMAT - Configurar Backup Automatico
REM  Programa backups diarios usando Windows Task Scheduler
REM ========================================

echo.
echo ========================================
echo  CONFIGURAR BACKUP AUTOMATICO
echo ========================================
echo.

REM Verificar permisos de administrador
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Este script requiere permisos de Administrador
    echo.
    echo Haz clic derecho en el archivo y selecciona
    echo "Ejecutar como administrador"
    echo.
    pause
    exit /b 1
)

REM Obtener ruta completa del script de backup
set SCRIPT_PATH=%~dp0crear_Backup.bat

echo Configurando tarea programada...
echo.
echo Opciones:
echo   [1] Backup diario a las 23:00
echo   [2] Backup diario a las 02:00 (madrugada)
echo   [3] Backup cada 12 horas
echo   [4] Personalizar horario
echo   [5] Eliminar tarea programada
echo.

set /p OPCION="Selecciona una opcion (1-5): "

if "%OPCION%"=="5" goto ELIMINAR

REM Configurar horario según opción
if "%OPCION%"=="1" (
    set HORA=23:00
    set INTERVALO=DAILY
    set NOMBRE_TAREA=ABBAMAT_Backup_Diario_23h
)
if "%OPCION%"=="2" (
    set HORA=02:00
    set INTERVALO=DAILY
    set NOMBRE_TAREA=ABBAMAT_Backup_Diario_02h
)
if "%OPCION%"=="3" (
    set HORA=00:00
    set INTERVALO=HOURLY
    set MODIFIER=/MO 12
    set NOMBRE_TAREA=ABBAMAT_Backup_Cada12h
)
if "%OPCION%"=="4" (
    set /p HORA="Ingresa la hora (formato HH:MM, ej: 18:30): "
    set INTERVALO=DAILY
    set NOMBRE_TAREA=ABBAMAT_Backup_Personalizado
)

if not defined HORA (
    echo [ERROR] Opcion invalida
    pause
    exit /b 1
)

echo.
echo Creando tarea programada...
echo   Nombre: %NOMBRE_TAREA%
echo   Horario: %HORA%
echo   Script: %SCRIPT_PATH%
echo.

REM Eliminar tarea si ya existe
schtasks /Delete /TN "%NOMBRE_TAREA%" /F >nul 2>&1

REM Crear nueva tarea
if defined MODIFIER (
    schtasks /Create /TN "%NOMBRE_TAREA%" /TR "\"%SCRIPT_PATH%\"" /SC %INTERVALO% %MODIFIER% /ST %HORA% /F
) else (
    schtasks /Create /TN "%NOMBRE_TAREA%" /TR "\"%SCRIPT_PATH%\"" /SC %INTERVALO% /ST %HORA% /F
)

if %errorlevel% equ 0 (
    echo.
    echo ========================================
    echo  TAREA CREADA EXITOSAMENTE
    echo ========================================
    echo.
    echo El backup se ejecutara automaticamente
    echo segun el horario configurado.
    echo.
    echo Para ver la tarea:
    echo   - Abre "Programador de tareas"
    echo   - Busca: %NOMBRE_TAREA%
    echo.
) else (
    echo.
    echo [ERROR] No se pudo crear la tarea
    echo.
)

goto FIN

:ELIMINAR
echo.
echo Tareas de backup encontradas:
echo.
schtasks /Query /TN "ABBAMAT_Backup*" /FO LIST 2>nul

echo.
set /p CONFIRMAR="Eliminar todas las tareas de backup? (SI/NO): "

if /i "%CONFIRMAR%"=="SI" (
    schtasks /Delete /TN "ABBAMAT_Backup_Diario_23h" /F >nul 2>&1
    schtasks /Delete /TN "ABBAMAT_Backup_Diario_02h" /F >nul 2>&1
    schtasks /Delete /TN "ABBAMAT_Backup_Cada12h" /F >nul 2>&1
    schtasks /Delete /TN "ABBAMAT_Backup_Personalizado" /F >nul 2>&1
    echo.
    echo [OK] Tareas eliminadas
    echo.
) else (
    echo.
    echo Operacion cancelada
    echo.
)

:FIN
pause

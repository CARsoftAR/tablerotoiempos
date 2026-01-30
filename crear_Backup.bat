@echo off
REM ========================================
REM  ABBAMAT - Sistema de Backup Completo
REM  Respalda Base de Datos y Código Fuente
REM ========================================

setlocal enabledelayedexpansion

echo.
echo ========================================
echo  SISTEMA DE BACKUP ABBAMAT
echo ========================================
echo.

REM Cambiar al directorio del proyecto
cd /d "%~dp0"

REM Crear carpeta de backups si no existe
if not exist "backups" mkdir backups

REM Obtener fecha y hora actual (formato: YYYYMMDD_HHMMSS)
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set datetime=%%I
set FECHA=%datetime:~0,8%
set HORA=%datetime:~8,6%
set TIMESTAMP=%FECHA%_%HORA%

echo Timestamp: %TIMESTAMP%
echo.

REM ========================================
REM  1. BACKUP DE BASE DE DATOS MYSQL
REM ========================================

echo [1/3] Creando backup de Base de Datos MySQL...

REM Cargar variables de entorno desde .env
for /f "tokens=1,2 delims==" %%a in (.env) do (
    if "%%a"=="MYSQL_DB_NAME" set DB_NAME=%%b
    if "%%a"=="MYSQL_USER" set DB_USER=%%b
    if "%%a"=="MYSQL_PASSWORD" set DB_PASS=%%b
    if "%%a"=="MYSQL_HOST" set DB_HOST=%%b
    if "%%a"=="MYSQL_PORT" set DB_PORT=%%b
)

REM Valores por defecto si no están en .env
if not defined DB_NAME set DB_NAME=tablerotiempos
if not defined DB_USER set DB_USER=root
if not defined DB_HOST set DB_HOST=localhost
if not defined DB_PORT set DB_PORT=3306

REM Crear nombre del archivo de backup
set DB_BACKUP_FILE=backups\DB_MySQL_%TIMESTAMP%.sql

REM Ejecutar mysqldump (asegúrate de que MySQL esté en el PATH)
echo Exportando base de datos: %DB_NAME%
echo Archivo: %DB_BACKUP_FILE%

if defined DB_PASS (
    mysqldump -h %DB_HOST% -P %DB_PORT% -u %DB_USER% -p%DB_PASS% %DB_NAME% > "%DB_BACKUP_FILE%" 2>nul
) else (
    mysqldump -h %DB_HOST% -P %DB_PORT% -u %DB_USER% %DB_NAME% > "%DB_BACKUP_FILE%" 2>nul
)

if %errorlevel% equ 0 (
    echo [OK] Backup de MySQL completado
    echo.
) else (
    echo [ERROR] No se pudo crear el backup de MySQL
    echo Verifica que mysqldump este en el PATH del sistema
    echo.
)

REM ========================================
REM  2. BACKUP DEL CODIGO FUENTE
REM ========================================

echo [2/3] Creando backup del codigo fuente...

set CODE_BACKUP_FILE=backups\Sistema_Completo_%TIMESTAMP%.zip

REM Usar PowerShell para crear el ZIP (disponible en Windows 7+)
echo Comprimiendo archivos del sistema...
powershell -Command "Compress-Archive -Path '.\*' -DestinationPath '%CODE_BACKUP_FILE%' -Force -CompressionLevel Optimal" -ExcludeProperty @('backups\*', 'venv\*', '__pycache__\*', '*.pyc', '.git\*')

if %errorlevel% equ 0 (
    echo [OK] Backup del codigo fuente completado
    echo.
) else (
    echo [ERROR] No se pudo crear el backup del codigo
    echo.
)

REM ========================================
REM  3. RESUMEN Y LIMPIEZA
REM ========================================

echo [3/3] Limpiando backups antiguos (mantener ultimos 10)...

REM Contar archivos de backup
set /a COUNT=0
for %%f in (backups\DB_MySQL_*.sql) do set /a COUNT+=1

REM Si hay más de 10 backups de DB, eliminar los más antiguos
if %COUNT% gtr 10 (
    echo Eliminando backups antiguos de MySQL...
    for /f "skip=10" %%f in ('dir /b /o-d backups\DB_MySQL_*.sql') do (
        del "backups\%%f"
        echo   - Eliminado: %%f
    )
)

REM Contar archivos de backup de código
set /a COUNT=0
for %%f in (backups\Sistema_Completo_*.zip) do set /a COUNT+=1

REM Si hay más de 10 backups de código, eliminar los más antiguos
if %COUNT% gtr 10 (
    echo Eliminando backups antiguos del sistema...
    for /f "skip=10" %%f in ('dir /b /o-d backups\Sistema_Completo_*.zip') do (
        del "backups\%%f"
        echo   - Eliminado: %%f
    )
)

echo.
echo ========================================
echo  BACKUP COMPLETADO
echo ========================================
echo.
echo Archivos creados:
if exist "%DB_BACKUP_FILE%" (
    for %%A in ("%DB_BACKUP_FILE%") do echo   - MySQL DB: %%~nxA (%%~zA bytes)
)
if exist "%CODE_BACKUP_FILE%" (
    for %%A in ("%CODE_BACKUP_FILE%") do echo   - Codigo: %%~nxA (%%~zA bytes)
)
echo.
echo Ubicacion: %CD%\backups\
echo.

pause

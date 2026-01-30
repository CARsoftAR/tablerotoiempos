@echo off
REM ========================================
REM  ABBAMAT - Restaurar Backup
REM  Restaura Base de Datos desde backup
REM ========================================

setlocal enabledelayedexpansion

echo.
echo ========================================
echo  RESTAURAR BACKUP DE BASE DE DATOS
echo ========================================
echo.

REM Cambiar al directorio del proyecto
cd /d "%~dp0"

REM Verificar que existe la carpeta de backups
if not exist "backups" (
    echo [ERROR] No se encontro la carpeta de backups
    echo.
    pause
    exit /b 1
)

REM Listar backups disponibles
echo Backups disponibles:
echo.
set /a INDEX=0
for /f "tokens=*" %%f in ('dir /b /o-d backups\DB_MySQL_*.sql 2^>nul') do (
    set /a INDEX+=1
    set "BACKUP[!INDEX!]=%%f"
    echo   [!INDEX!] %%f
)

if %INDEX% equ 0 (
    echo [ERROR] No se encontraron backups de base de datos
    echo.
    pause
    exit /b 1
)

echo.
set /p CHOICE="Selecciona el numero del backup a restaurar (1-%INDEX%): "

REM Validar selección
if not defined BACKUP[%CHOICE%] (
    echo [ERROR] Seleccion invalida
    pause
    exit /b 1
)

set SELECTED_BACKUP=!BACKUP[%CHOICE%]!
echo.
echo Backup seleccionado: %SELECTED_BACKUP%
echo.

REM Advertencia
echo ========================================
echo  ADVERTENCIA
echo ========================================
echo.
echo Esta operacion SOBRESCRIBIRA la base de
echo datos actual con el backup seleccionado.
echo.
echo Todos los datos actuales se PERDERAN.
echo.
set /p CONFIRM="Estas seguro? (SI/NO): "

if /i not "%CONFIRM%"=="SI" (
    echo.
    echo Operacion cancelada por el usuario.
    echo.
    pause
    exit /b 0
)

REM Cargar variables de entorno desde .env
for /f "tokens=1,2 delims==" %%a in (.env) do (
    if "%%a"=="MYSQL_DB_NAME" set DB_NAME=%%b
    if "%%a"=="MYSQL_USER" set DB_USER=%%b
    if "%%a"=="MYSQL_PASSWORD" set DB_PASS=%%b
    if "%%a"=="MYSQL_HOST" set DB_HOST=%%b
    if "%%a"=="MYSQL_PORT" set DB_PORT=%%b
)

REM Valores por defecto
if not defined DB_NAME set DB_NAME=tablerotiempos
if not defined DB_USER set DB_USER=root
if not defined DB_HOST set DB_HOST=localhost
if not defined DB_PORT set DB_PORT=3306

echo.
echo Restaurando base de datos...
echo.

REM Ejecutar mysql para restaurar
if defined DB_PASS (
    mysql -h %DB_HOST% -P %DB_PORT% -u %DB_USER% -p%DB_PASS% %DB_NAME% < "backups\%SELECTED_BACKUP%" 2>nul
) else (
    mysql -h %DB_HOST% -P %DB_PORT% -u %DB_USER% %DB_NAME% < "backups\%SELECTED_BACKUP%" 2>nul
)

if %errorlevel% equ 0 (
    echo.
    echo ========================================
    echo  RESTAURACION COMPLETADA
    echo ========================================
    echo.
    echo La base de datos ha sido restaurada
    echo exitosamente desde el backup:
    echo   %SELECTED_BACKUP%
    echo.
) else (
    echo.
    echo [ERROR] No se pudo restaurar el backup
    echo Verifica que mysql este en el PATH
    echo.
)

pause

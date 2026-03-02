@echo off
REM ========================================
REM  ABBAMAT - Tablero de Tiempos
REM  Script de inicio del servidor Django
REM ========================================

echo.
echo ========================================
echo  Iniciando Servidor Django...
echo ========================================
echo.

REM Cambiar al directorio del proyecto
cd /d "%~dp0"

REM Activar el entorno virtual si existe
if exist "venv\Scripts\activate.bat" (
    echo Activando entorno virtual...
    call venv\Scripts\activate.bat
) else (
    echo No se encontro entorno virtual, usando Python del sistema...
)

echo.
echo Verificando migraciones pendientes...
python manage.py migrate --noinput

echo.
echo ========================================
echo  Servidor corriendo en:
echo  http://localhost:8000
echo  http://0.0.0.0:8000
echo.
echo  Accesible desde la red local
echo  Presiona Ctrl+C para detener
echo ========================================
echo.

REM Ejecutar el servidor en 0.0.0.0:1000 para acceso desde red local
python manage.py runserver 0.0.0.0:1000

pause

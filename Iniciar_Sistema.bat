@echo off
title Servidor Django ABBAMAT - Puerto 8005
color 0b

:: 1. Definir la ruta del proyecto
set RUTA="C:\Sistemas ABBAMAT\planificacionProcesosProductivos EN DESARROLLO"

:: 2. Entrar a la carpeta del proyecto
cd /d %RUTA%

echo =====================================================
echo    INICIANDO SERVIDOR Y CARGANDO SISTEMA
echo =====================================================
echo.

:: 3. Activar Entorno Virtual
if exist "venv\Scripts\activate.bat" (
    echo [OK] Activando entorno virtual...
    call venv\Scripts\activate.bat
)

:: 4. Abrir el navegador en segundo plano (esperamos 5 segundos por seguridad)
echo [OK] Preparando apertura en http://192.168.88.47:8005...
start /b cmd /c "timeout /t 5 >nul && start http://192.168.88.47:8005"

:: 5. Ejecutar el servidor de Django 
echo [OK] Lanzando servidor en MODO RED (0.0.0.0)...
echo Presiona Ctrl+C para detener el servidor.
echo.

:: 🛑 CAMBIO CLAVE: Agregamos 0.0.0.0: para permitir conexiones por IP de red 🛑
python manage.py runserver 0.0.0.0:8005
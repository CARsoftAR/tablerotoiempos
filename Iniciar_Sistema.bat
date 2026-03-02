@echo off
setlocal
:: ============================================================
::      ABBAMAT - TABLERO DE PRODUCCION (8000)
:: ============================================================
:: Este archivo inicia el Tablero de Produccion en el puerto 8000
:: ============================================================

:: RUTA DEL PROYECTO
set "PROJECT_DIR=C:\Sistemas ABBAMAT\tablerotoiempos"

title TABLERO PRODUCCION - ABBAMAT
mode con: cols=100 lines=30
color 0E

echo.
echo  ============================================================
echo      SISTEMA TABLERO DE PRODUCCION - INICIO RAPIDO
echo  ============================================================
echo.

:: Verificar si el directorio existe
if not exist "%PROJECT_DIR%" (
    echo  [!] ERROR: No se encontro la carpeta en:
    echo      "%PROJECT_DIR%"
    echo.
    echo  Presiona una tecla para salir...
    pause >nul
    exit /b
)

:: Cambiar al directorio
cd /d "%PROJECT_DIR%"

:: 1. Intentar cerrar cualquier proceso previo en el puerto 8000
echo  [1/3] Limpiando puerto 8000...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :1000 ^| findstr LISTENING') do taskkill /f /pid %%a >nul 2>&1

:: 2. Preparar el navegador (esperar 5 segundos antes de abrir)
echo  [2/3] El navegador se abrira en 5 segundos...
start /b cmd /c "timeout /t 5 /nobreak >nul && start http://localhost:8000"

:: 3. Iniciar el servidor
echo  [3/3] Iniciando servidor Django...
echo.
echo  ------------------------------------------------------------
echo   IMPORTANTE: 
echo   - Si ves otra ventana de "Control de Vacaciones" abierta, cierrala.
echo   - Este sistema usa el puerto 8000.
echo   - No cierres esta ventana.
echo  ------------------------------------------------------------
echo.

:: Verificar entorno virtual
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

:: Ejecutar
python manage.py runserver 0.0.0.0:8000

if %ERRORLEVEL% neq 0 (
    echo.
    echo  [!] ERROR CRITICO: No se pudo iniciar el servidor.
    echo      Verifica que Python este instalado y las librerias cargadas.
    pause
)

pause

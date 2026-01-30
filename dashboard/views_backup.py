# ========================================
# MÓDULO DE BACKUP Y RESTAURACIÓN
# ========================================

import os
import subprocess
import zipfile
from datetime import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse, FileResponse
from django.contrib import messages
from django.conf import settings
from .models import BackupHistorial

def gestion_backups(request):
    """
    Vista principal del módulo de backup
    Muestra el historial de backups y permite crear nuevos
    """
    backups = BackupHistorial.objects.all().order_by('-fecha_creacion')
    
    # Calcular espacio total usado
    espacio_total_mb = sum(b.tamano_total_mb for b in backups)
    
    context = {
        'backups': backups,
        'total_backups': backups.count(),
        'espacio_total_mb': espacio_total_mb,
        'espacio_total_gb': espacio_total_mb / 1024,
    }
    
    return render(request, 'dashboard/gestion_backups.html', context)

def crear_backup(request):
    """
    Crea un nuevo backup de la base de datos MySQL y/o código fuente
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Método no permitido'}, status=405)
    
    tipo = request.POST.get('tipo', 'COMPLETO')  # MYSQL o COMPLETO
    notas = request.POST.get('notas', '')
    
    # Crear carpeta de backups si no existe
    backup_dir = os.path.join(settings.BASE_DIR, 'backups')
    os.makedirs(backup_dir, exist_ok=True)
    
    # Timestamp para nombres de archivo
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    backup_record = BackupHistorial.objects.create(
        tipo=tipo,
        estado='EXITOSO',
        usuario=request.user.username if request.user.is_authenticated else 'Sistema',
        notas=notas
    )
    
    try:
        # 1. BACKUP DE BASE DE DATOS MYSQL
        if tipo in ['MYSQL', 'COMPLETO']:
            db_filename = f'DB_MySQL_{timestamp}.sql'
            db_filepath = os.path.join(backup_dir, db_filename)
            
            # Obtener credenciales de la base de datos
            db_name = os.getenv('MYSQL_DB_NAME', 'tablerotiempos')
            db_user = os.getenv('MYSQL_USER', 'root')
            db_pass = os.getenv('MYSQL_PASSWORD', '')
            db_host = os.getenv('MYSQL_HOST', 'localhost')
            db_port = os.getenv('MYSQL_PORT', '3306')
            
            # Función para encontrar mysqldump
            def find_mysqldump():
                """Busca mysqldump en rutas comunes de Windows"""
                # Primero intentar desde PATH
                try:
                    subprocess.run(['mysqldump', '--version'], capture_output=True, check=True)
                    return 'mysqldump'
                except (subprocess.CalledProcessError, FileNotFoundError):
                    pass
                
                # Buscar en rutas comunes de MySQL en Windows
                common_paths = [
                    r'C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqldump.exe',
                    r'C:\Program Files\MySQL\MySQL Server 8.4\bin\mysqldump.exe',
                    r'C:\Program Files\MySQL\MySQL Server 5.7\bin\mysqldump.exe',
                    r'C:\Program Files (x86)\MySQL\MySQL Server 8.0\bin\mysqldump.exe',
                    r'C:\Program Files (x86)\MySQL\MySQL Server 5.7\bin\mysqldump.exe',
                    r'C:\xampp\mysql\bin\mysqldump.exe',
                    r'C:\wamp64\bin\mysql\mysql8.0.27\bin\mysqldump.exe',
                ]
                
                for path in common_paths:
                    if os.path.exists(path):
                        return path
                
                return None
            
            mysqldump_cmd = find_mysqldump()
            
            if not mysqldump_cmd:
                raise Exception(
                    "mysqldump no está disponible en el sistema. "
                    "Por favor, instala MySQL o agrega la carpeta bin de MySQL al PATH del sistema. "
                    "Ejemplo: C:\\Program Files\\MySQL\\MySQL Server 8.0\\bin"
                )
            
            # Construir comando mysqldump
            cmd = [
                mysqldump_cmd,  # Usar la ruta encontrada
                f'-h{db_host}',
                f'-P{db_port}',
                f'-u{db_user}',
            ]
            
            if db_pass:
                cmd.append(f'-p{db_pass}')
            
            cmd.append(db_name)
            
            # Ejecutar mysqldump
            try:
                with open(db_filepath, 'w', encoding='utf-8') as f:
                    result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, text=True)
                
                if result.returncode != 0:
                    error_msg = result.stderr.strip()
                    # Limpiar mensaje de error
                    if 'Access denied' in error_msg:
                        raise Exception("Error de autenticación: Usuario o contraseña incorrectos en MySQL")
                    elif 'Unknown database' in error_msg:
                        raise Exception(f"Base de datos '{db_name}' no encontrada")
                    else:
                        raise Exception(f"Error en mysqldump: {error_msg}")
            except FileNotFoundError:
                raise Exception("No se pudo ejecutar mysqldump. Verifica que MySQL esté instalado correctamente.")
            
            # Calcular tamaño del archivo
            if os.path.exists(db_filepath):
                db_size_mb = os.path.getsize(db_filepath) / (1024 * 1024)
                backup_record.archivo_db = db_filename
                backup_record.tamano_db_mb = db_size_mb
            else:
                raise Exception("El archivo de backup no se creó correctamente")
        
        # 2. BACKUP DEL CÓDIGO FUENTE
        if tipo == 'COMPLETO':
            code_filename = f'Sistema_Completo_{timestamp}.zip'
            code_filepath = os.path.join(backup_dir, code_filename)
            
            # Crear ZIP del código fuente
            with zipfile.ZipFile(code_filepath, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Excluir carpetas innecesarias
                exclude_dirs = {'backups', 'venv', '.venv', '__pycache__', '.git', 'staticfiles'}
                exclude_extensions = {'.pyc', '.pyo', '.log'}
                
                for root, dirs, files in os.walk(settings.BASE_DIR):
                    # Filtrar directorios a excluir
                    dirs[:] = [d for d in dirs if d not in exclude_dirs]
                    
                    for file in files:
                        # Filtrar archivos a excluir
                        if any(file.endswith(ext) for ext in exclude_extensions):
                            continue
                        
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, settings.BASE_DIR)
                        try:
                            zipf.write(file_path, arcname)
                        except Exception as e:
                            # Ignorar archivos que no se pueden leer
                            print(f"Advertencia: No se pudo incluir {file_path}: {e}")
            
            # Calcular tamaño del archivo
            code_size_mb = os.path.getsize(code_filepath) / (1024 * 1024)
            backup_record.archivo_codigo = code_filename
            backup_record.tamano_codigo_mb = code_size_mb
        
        backup_record.save()
        
        messages.success(request, f'✅ Backup creado exitosamente: {backup_record.tamano_total_mb:.2f} MB')
        return JsonResponse({
            'status': 'success',
            'message': 'Backup creado exitosamente',
            'backup_id': backup_record.id,
            'tamano_mb': backup_record.tamano_total_mb
        })
        
    except Exception as e:
        backup_record.estado = 'ERROR'
        backup_record.notas = f"Error: {str(e)}"
        backup_record.save()
        
        # Log del error para depuración
        import traceback
        print(f"Error al crear backup: {str(e)}")
        print(traceback.format_exc())
        
        messages.error(request, f'❌ Error al crear backup: {str(e)}')
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

def restaurar_backup(request, pk):
    """
    Restaura la base de datos desde un backup
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Método no permitido'}, status=405)
    
    backup = get_object_or_404(BackupHistorial, pk=pk)
    
    if not backup.archivo_db:
        return JsonResponse({'status': 'error', 'message': 'Este backup no contiene base de datos'}, status=400)
    
    backup_dir = os.path.join(settings.BASE_DIR, 'backups')
    db_filepath = os.path.join(backup_dir, backup.archivo_db)
    
    if not os.path.exists(db_filepath):
        return JsonResponse({'status': 'error', 'message': 'Archivo de backup no encontrado'}, status=404)
    
    try:
        # Obtener credenciales de la base de datos
        db_name = os.getenv('MYSQL_DB_NAME', 'tablerotiempos')
        db_user = os.getenv('MYSQL_USER', 'root')
        db_pass = os.getenv('MYSQL_PASSWORD', '')
        db_host = os.getenv('MYSQL_HOST', 'localhost')
        db_port = os.getenv('MYSQL_PORT', '3306')
        
        # Construir comando mysql
        cmd = [
            'mysql',
            f'-h{db_host}',
            f'-P{db_port}',
            f'-u{db_user}',
        ]
        
        if db_pass:
            cmd.append(f'-p{db_pass}')
        
        cmd.append(db_name)
        
        # Ejecutar mysql para restaurar
        with open(db_filepath, 'r', encoding='utf-8') as f:
            result = subprocess.run(cmd, stdin=f, stderr=subprocess.PIPE, text=True)
        
        if result.returncode != 0:
            raise Exception(f"Error en mysql: {result.stderr}")
        
        # Actualizar estado del backup
        backup.estado = 'RESTAURADO'
        backup.save()
        
        messages.success(request, f'✅ Base de datos restaurada exitosamente desde {backup.archivo_db}')
        return JsonResponse({
            'status': 'success',
            'message': 'Base de datos restaurada exitosamente'
        })
        
    except Exception as e:
        messages.error(request, f'❌ Error al restaurar backup: {str(e)}')
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

def descargar_backup(request, pk):
    """
    Descarga un archivo de backup
    """
    backup = get_object_or_404(BackupHistorial, pk=pk)
    backup_dir = os.path.join(settings.BASE_DIR, 'backups')
    
    # Determinar qué archivo descargar
    tipo_descarga = request.GET.get('tipo', 'db')  # 'db' o 'codigo'
    
    if tipo_descarga == 'db' and backup.archivo_db:
        filepath = os.path.join(backup_dir, backup.archivo_db)
        filename = backup.archivo_db
    elif tipo_descarga == 'codigo' and backup.archivo_codigo:
        filepath = os.path.join(backup_dir, backup.archivo_codigo)
        filename = backup.archivo_codigo
    else:
        messages.error(request, 'Archivo no disponible')
        return redirect('gestion_backups')
    
    if not os.path.exists(filepath):
        messages.error(request, 'Archivo no encontrado')
        return redirect('gestion_backups')
    
    # Servir el archivo para descarga
    response = FileResponse(open(filepath, 'rb'))
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response

def eliminar_backup(request, pk):
    """
    Elimina un backup del sistema
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Método no permitido'}, status=405)
    
    backup = get_object_or_404(BackupHistorial, pk=pk)
    backup_dir = os.path.join(settings.BASE_DIR, 'backups')
    
    try:
        # Eliminar archivos físicos
        if backup.archivo_db:
            db_path = os.path.join(backup_dir, backup.archivo_db)
            if os.path.exists(db_path):
                os.remove(db_path)
        
        if backup.archivo_codigo:
            code_path = os.path.join(backup_dir, backup.archivo_codigo)
            if os.path.exists(code_path):
                os.remove(code_path)
        
        # Eliminar registro de la base de datos
        backup.delete()
        
        messages.success(request, '✅ Backup eliminado exitosamente')
        return JsonResponse({'status': 'success', 'message': 'Backup eliminado'})
        
    except Exception as e:
        messages.error(request, f'❌ Error al eliminar backup: {str(e)}')
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

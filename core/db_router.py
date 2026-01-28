class DatabaseRouter:
    """
    Controla las operaciones de base de datos para múltiples bases de datos.
    Impone la restricción de SÓLO LECTURA para SQL Server.
    """
    def db_for_read(self, model, **hints):
        if model._meta.app_label == 'sql_server_data' or getattr(model, 'use_db', '') == 'sql_server':
            return 'sql_server'
        return 'default'

    def db_for_write(self, model, **hints):
        if model._meta.app_label == 'sql_server_data' or getattr(model, 'use_db', '') == 'sql_server':
            # Evita escrituras en SQL Server a nivel de Django
            return None
        return 'default'

    def allow_relation(self, obj1, obj2, **hints):
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if db == 'sql_server':
            return False  # Nunca migrar SQL Server
        return True

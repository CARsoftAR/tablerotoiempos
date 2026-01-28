import os
import django
import sys
from datetime import timedelta
from django.utils import timezone

# Add project root to path
sys.path.append(os.getcwd())

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from dashboard.models import VTMan, MaquinaConfig

def fetch_machines_from_production():
    print("--- Fetching Machines from Production Records (V_TMAN) ---")
    
    # Get all unique machine IDs from the last 30 days (or all time if fast enough)
    # Using a safe window just in case
    cutoff = timezone.now() - timedelta(days=90)
    
    # Get distinct machine IDs from production records
    # Note: SQLite/MySQL/SQLServer 'distinct' behavior might vary, but Django handles it.
    try:
        # We only need the ID
        machine_ids = VTMan.objects.filter(fecha__gte=cutoff).values_list('id_maquina', flat=True).distinct()
        
        # Convert to list and filter None/Empty
        unique_ids = [mid for mid in machine_ids if mid]
        unique_ids = sorted(list(set(unique_ids))) # Deduplicate in python just to be safe
        
        print(f"Found {len(unique_ids)} potential machines in production history.")
        
        machines_to_add = []
        for mid in unique_ids:
            # Check if it already exists in MaquinaConfig
            if not MaquinaConfig.objects.filter(id_maquina=mid).exists():
                machines_to_add.append(mid)
                
        print(f"Machines to add to Local DB: {len(machines_to_add)}")
        for mid in machines_to_add:
            print(f" -> {mid}")
            
    except Exception as e:
        print(f"Error checking V_TMAN: {e}")

if __name__ == "__main__":
    fetch_machines_from_production()

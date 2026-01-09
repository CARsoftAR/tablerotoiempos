import os
import django
import datetime

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from dashboard.models import VTMan, MaquinaConfig

def check_ids():
    # 1. Get raw IDs from DB for yesterday
    target_date = datetime.date(2026, 1, 8)
    start_utc = datetime.datetime.combine(target_date, datetime.time.min).replace(tzinfo=datetime.timezone.utc)
    end_utc = datetime.datetime.combine(target_date, datetime.time.max).replace(tzinfo=datetime.timezone.utc)
    
    raw_ids = VTMan.objects.filter(fecha__range=(start_utc, end_utc)).values_list('id_maquina', flat=True).distinct()
    
    # 2. Get Config IDs
    config_ids = MaquinaConfig.objects.values_list('id_maquina', flat=True)
    
    print("--- ID COMPARISON ---")
    print(f"Configured IDs: {list(config_ids)}")
    print("-" * 20)
    print("Raw Used IDs in VTMan (Yesterday):")
    
    for rid in raw_ids:
        if not rid: continue
        # repr() shows quotes and potential whitespace
        match_status = "MATCH" if rid in config_ids else "NO MATCH"
        
        # Check stripped
        rid_stripped = rid.strip()
        if match_status == "NO MATCH" and rid_stripped in config_ids:
            match_status = "MATCH (If Stripped)"
            
        print(f"'{rid}' : {match_status}")

if __name__ == '__main__':
    check_ids()

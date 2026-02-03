import requests
import os
import logging
from .models import NotificacionConfig

logger = logging.getLogger(__name__)

def send_external_notification(message):
    """
    Despacha notificaciones a WhatsApp o Telegram según configuración en Base de Datos.
    """
    # 0. Cargar Configuración desde DB
    config = NotificacionConfig.get_solo()
    
    # 1. TELEGRAM INTEGRATION
    tg_token = config.telegram_token
    tg_chat_id = config.telegram_chat_id
    
    if config.activar_telegram and tg_token and tg_chat_id:
        try:
            url = f"https://api.telegram.org/bot{tg_token}/sendMessage"
            payload = {
                'chat_id': tg_chat_id,
                'text': f"🔔 *ABBAMAT GOLD ALERT*\n\n{message}",
                'parse_mode': 'Markdown'
            }
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                logger.info("Notificación de Telegram enviada con éxito.")
            else:
                logger.error(f"Error en Telegram: {response.text}")
        except Exception as e:
            logger.error(f"Falla crítica enviando a Telegram: {e}")

    # 2. WHATSAPP INTEGRATION (CallMeBot)
    wa_phone = config.whatsapp_phone
    wa_apikey = config.whatsapp_apikey
    
    if config.activar_whatsapp and wa_phone and wa_apikey:
        try:
            # CallMeBot API
            url = f"https://api.callmebot.com/whatsapp.php?phone={wa_phone}&text={message}&apikey={wa_apikey}"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                logger.info("Notificación de WhatsApp enviada con éxito.")
        except Exception as e:
            logger.error(f"Falla enviando a WhatsApp: {e}")

    return True # Retorna True si procesó el flujo (aunque falle el envío intentado)

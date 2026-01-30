import requests
import os
import logging

logger = logging.getLogger(__name__)

def send_external_notification(message):
    """
    Despacha notificaciones a WhatsApp o Telegram según configuración en .env.
    Prioriza Telegram por ser más simple de implementar via API directa.
    """
    
    # 1. TELEGRAM INTEGRATION
    tg_token = os.getenv('TELEGRAM_BOT_TOKEN')
    tg_chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    if tg_token and tg_chat_id:
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
                return True
            else:
                logger.error(f"Error en Telegram: {response.text}")
        except Exception as e:
            logger.error(f"Falla crítica enviando a Telegram: {e}")

    # 2. WHATSAPP INTEGRATION (Placeholder via CallMeBot or similar simple API)
    # CallMeBot is a free/easy way to send WA messages for testing/personal use
    wa_phone = os.getenv('WHATSAPP_PHONE')
    wa_apikey = os.getenv('WHATSAPP_APIKEY')
    
    if wa_phone and wa_apikey:
        try:
            # Ejemplo simplificado usando CallMeBot
            url = f"https://api.callmebot.com/whatsapp.php?phone={wa_phone}&text={message}&apikey={wa_apikey}"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                logger.info("Notificación de WhatsApp enviada con éxito.")
                return True
        except Exception as e:
            logger.error(f"Falla enviando a WhatsApp: {e}")

    logger.warning("No se pudo enviar notificación externa: Faltan credenciales en .env")
    return False

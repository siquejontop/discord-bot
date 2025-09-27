import os
from dotenv import load_dotenv

# Cargar variables desde archivo .env (para cuando lo corras local o en el server)
load_dotenv()

# 🔑 El TOKEN siempre viene de las variables de entorno
TOKEN = os.getenv("DISCORD_TOKEN")

# ⚙️ Configuración de roles y logs
LOG_CHANNEL_ID = 1421331172969156660  
REQUIRED_ROLE_ID = 1421330888192561152  
MAX_ROLE_ID = 1415860211318521966  
JOIN_ROLE_ID = 1421330898569269409
LIMIT_ROLE_ID = 1415860211318521966
MUTE_ROLE_ID = 1415860201554448506

def get_log_channel(guild):
    """Devuelve el canal de logs de un servidor"""
    return guild.get_channel(LOG_CHANNEL_ID)

# handlers/basic_commands.py

from oled_display import actualizar_pantalla
from utils import obtener_ip, llamadaSistema
import logging
from logger import log_action

def log_action(user, action):
    logging.info("User=%s Action=%s", user, action)
    
def _user(message):
    return message.from_user.username or str(message.from_user.id)

def start(bot, message):
    mensaje = """
    ¡Bienvenido al Bot de Patana que administra esta Raspberry Pi!

    PatanaBot está diseñado para ayudarte con el servidor de Minecraft directamente desde la Raspberry Pi. Aquí puedes controlar el estado del servidor y consultar el estado del server.

    *Comandos disponibles*:
    - /minecraft - Enciende/Apaga o revisa el estado del servidor de Minecraft.
    - /logs - Muestra los últimos registros del servidor.
    - /usuarios_activos - Consulta los usuarios activos en el server
    - /tp <nombre_usuario> <x> <y> <z>

    Para ver todos los comandos usa /comandos.

    *Conéctate a nuestra red privada (ZeroTier)*:
    1. Descarga e instala ZeroTier One en tu dispositivo.
    2. Abre la aplicación y busca "Join New Network".
    3. Ingresa el ID de la red: `0cccb752f7b9181f`
    4. Avísame cuando te hayas unido y te aceptaré en la red.
    5. Conéctate al server de Minecraft: 172.24.9.41:25565
    """
    bot.reply_to(message, mensaje)  # Respondemos al comando con el mensaje
    logging.info("start")
    log_action(_user(message), "/start")
    actualizar_pantalla("Bot iniciado")

def ping(bot, message):
    bot.reply_to(message, "Still alive and kicking!")
    logging.info("ping")
    log_action(_user(message), "/ping")
    actualizar_pantalla("Ping recibido")

def fecha(bot, message):
    fecha = llamadaSistema("date")  # Llamada al sistema
    bot.reply_to(message, fecha)  # Respondemos al comando con el mensaje
    logging.info("fecha")
    log_action(_user(message), "/fecha")
    actualizar_pantalla("Fecha mostrada")
    
def comandos(bot, message):
    respuuesta = (
        "*Comandos disponibles*\n\n"
        "*Sistema*\n"
        "/status — CPU, RAM, disco y temperatura\n"
        "/ip — IP local de la Raspberry\n"
        "/fecha — Fecha y hora del sistema\n"
        "/ping — Comprueba que el bot está vivo\n\n"
        "*Servicios*\n"
        "/plex — Estado de Plex (`on`/`off` solo admins)\n"
        "/zerotier — Estado de ZeroTier (`on`/`off` solo admins)\n\n"
        "*Minecraft*\n"
        "/minecraft — Panel: arrancar, parar, ver estado\n"
        "/online — Jugadores conectados ahora\n"
        "/last — Última actividad\n\n"
        "*Torrents*\n"
        "/torrents — Gestión de Transmission\n\n"
        "*Solo admins*\n"
        "/admin — Panel de administración\n"
        "/apagar — Apaga la Raspberry Pi"
    )
    bot.reply_to(message, respuuesta, parse_mode="Markdown")
    logging.info("comandos")
    log_action(_user(message), "/comandos")
    actualizar_pantalla("comandos")


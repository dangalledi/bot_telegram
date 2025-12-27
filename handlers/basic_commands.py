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
    ¡Bienvenido al Bot de Patana que administra esta Raspberry Pi! 🎮🖥️

    PatanaBot está diseñado para ayudarte con el servidor de Minecraft directamente desde la Raspberry Pi. Aquí puedes controlar el estado del servidor y consultar el estado del server.

    🔹 **Comandos disponibles**:
    - /minecraft - Enciande/Apaga o revisa el estado del servidor de Minecraft.
    - /logs - Muestra los últimos registros del servidor.
    - /usuarios_activos - Consulta los usuarios activos en el server  
    - /tp <nombre_usuario <x> <y> <z> ó /tp <nombre_usuario> -> te lleva a la casa de la Ale y Dani

    Para ver todos los comandos y sus descripciones, usa el comando /comandos.

    Si necesitas ayuda o tienes alguna pregunta, no dudes en usar el comando /comandos.

    🔹 **Conéctate a nuestra red privada**:
    Para conectarte a nuestra red privada de ZeroTier, sigue estos pasos:
    1. Descarga e instala ZeroTier One en tu dispositivo. -> https://download.zerotier.com/dist/ZeroTier%20One.msi
    2. Abre la aplicación y busca la opción "Join New Network".
    3. Ingresa el ID de la red: `0cccb752f7b9181f`.
    4. Avísame cuando te hayas unido y te aceptaré en nuestra red. 😊
    5. Luego de agregarte a la red, ingresa al server de Minecraft 172.24.9.41:25565 y ¡Listo!
    
    ¡Comienza a jugar Minecraft ahora y asegúrate de que todo funcione!
    
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
    respuuesta = ("Lista de comandos implementados:" 
                    "\n/inicio\n/comandos\n\n"
                    # "/apagar\n/reiniciar\n\n"
                    # "/red_conectada\n/ip\n"
                    "/ping\n"
                    "/fecha\n/status\n\n"
                    # "/pwd\n/cd\n/ls\n/documento\n\n"
                    "/minecraft")
    bot.reply_to(message, respuuesta) # Respondemos al comando con el mensaje
    logging.info("comandos")
    log_action(_user(message), "/comandos")
    actualizar_pantalla("comandos")


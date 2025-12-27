# handlers/minecraft_handler.py

from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils import llamadaSistema
from oled_display import actualizar_pantalla
from logger import setup_logging 

def minecraft(bot, call):
    print('minecraft')
    container_name = "mc-server"
    try:
        status_output = llamadaSistema("docker ps -f name=mc-server --format '{{.Status}}'")
        message = ("¿Qué deseas hacer? /logs\n\n"
                   f"el estado del contenedor {container_name} es: {(status_output,'esta apagado')[status_output=='']}")
        setup_logging(call.from_user.username, '/minecraft')
        actualizar_pantalla("Minecraft: " + ("Encendido" if status_output else "Apagado"))
    except Exception as e:
        # Manejar cualquier error
        message = ("¿Qué deseas hacer?\n\n"
                   f"error al obtener el estado del contenedor: {str(e)}")
        setup_logging(call.from_user.username, f'/minecraft - Error: {str(e)}')
        actualizar_pantalla("Error Minecraft")
    finally:
        bot.send_message(call.chat.id, message, reply_markup=gen_markup_mc())

def gen_markup_mc():
    markup = InlineKeyboardMarkup(row_width=3)
    markup.add(
        InlineKeyboardButton("Apagar", callback_data="stop"),
        InlineKeyboardButton("Encender", callback_data="start"),
        InlineKeyboardButton("Detalle", callback_data="detalle")
    )
    return markup

def handle_docker_commands(bot, call):
    respuesta = call.data
    # Verificar el estado actual del contenedor antes de intentar apagarlo
    status_output = llamadaSistema("docker-compose -f /home/patana/minecraft-server/docker-compose.yml ps")
    if respuesta == "stop":
        if "Exit" in status_output:
            mensaje_accion = "El servidor ya está apagado."
        else:
            accion = llamadaSistema("docker-compose -f /home/patana/minecraft-server/docker-compose.yml stop")
            mensaje_accion = "Apagando el servidor..."
    elif respuesta == "start":
        if "Up" in status_output:
            mensaje_accion = "El servidor ya está encendido."
        else:
            accion = llamadaSistema("docker-compose -f /home/patana/minecraft-server/docker-compose.yml start")
            mensaje_accion = "Encendiendo el servidor..."
    elif respuesta == "detalle":
        mensaje_accion = llamadaSistema("docker-compose -f /home/patana/minecraft-server/docker-compose.yml ps")
    else:
        mensaje_accion = "Comando desconocido"
    bot.send_message(call.from_user.id, mensaje_accion)
    setup_logging(call.from_user.username, f'/minecraft - {respuesta}')

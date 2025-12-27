# bot.py

import os
import time
import threading
import logging
import telebot
from utils import llamadaSistema, obtener_ip
from oled_display import render_status, start_auto_update
from handlers.admin_handler import admin
from handlers.basic_commands import start, ping, fecha, comandos
from handlers.system_commands import status, ip
from handlers.minecraft_handler import minecraft, handle_minecraft_callback, mc_players_online, mc_last_activity
from handlers.transmission_handler import agregar_torrent, estado_descargas, eliminar_torrent, listar_torrents
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from logger import setup_logging

setup_logging()

TOKEN = os.getenv("TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

if not TOKEN:
    raise RuntimeError("Falta TOKEN en variables de entorno (archivo .env o export).")

bot = telebot.TeleBot(token=TOKEN)

@bot.message_handler(commands=['apagar'])
def handle_apagar(message):
    # Solo el administrador puede apagar el sistema
    if message.from_user.id == ADMIN_ID:
        bot.reply_to(message, "Apagando la Raspberry Pi...")
        os.system("sudo shutdown now")
    else:
        bot.reply_to(message, "No tienes permiso para apagar el sistema.")

display_state = {
    "last_text": "",
    "last_ts": 0.0,
}
_state_lock = threading.Lock()

def note_display(text: str):
    with _state_lock:
        display_state["last_text"] = text
        display_state["last_ts"] = time.time()
    
# Registrar los manejadores de comandos
@bot.message_handler(commands=['start', 'inicio'])
def handle_start(message):
    start(bot, message)
    note_display(f"/start @{message.from_user.username or message.from_user.id}")

@bot.message_handler(commands=['admin'])
def handle_admin(message):
    admin(bot, message)

@bot.message_handler(commands=['ping'])
def handle_ping(message):
    ping(bot, message)
    note_display(f"/ping @{message.from_user.username or message.from_user.id}")
    
@bot.message_handler(commands=['comandos'])
def handler_comandos(message):
    comandos(bot, message)

@bot.message_handler(commands=['fecha'])
def handle_fecha(message):
    fecha(bot, message)

@bot.message_handler(commands=['status'])
def handle_status(message):
    status(bot, message)

@bot.message_handler(commands=['ip'])
def handle_ip(message):
    ip(bot, message)

@bot.message_handler(commands=['minecraft', 'mc'])
def handle_minecraft(message):
    minecraft(bot, message)

@bot.callback_query_handler(func=lambda call: call.data.startswith("mc:"))
def on_mc_callback(call):
    handle_minecraft_callback(bot, call)

@bot.message_handler(commands=['mc_online', 'online'])
def handle_mc_online(message):
    text, count, names = mc_players_online()
    if count == 0:
        bot.reply_to(message, "No hay jugadores conectados الآن.\n" + text)
    else:
        bot.reply_to(message, f"Jugadores conectados ({count}):\n- " + "\n- ".join(names))
        
@bot.message_handler(commands=['mc_last', 'last'])
def handle_mc_last(message):
    last = mc_last_activity()
    bot.reply_to(message, f"Última actividad:\n{last}")

@bot.callback_query_handler(func=lambda call: call.data in ["ip", "status", "pwd", "ls"])
def handle_system_commands(call):
    print(f"Comando del sistema recibido: {call.data}")
    logging.info("Comando del sistema recibido: %s", call.data)
    
    if call.data == "ip":
        # Mostrar la IP
        ip_address = obtener_ip()
        bot.send_message(call.message.chat.id, f"IP del sistema: {ip_address}")
    
    elif call.data == "status":
        # Mostrar estado del sistema (puedes mover tu función status aquí)
        status_info = llamadaSistema("top -bn1 | grep 'Cpu(s)'")
        bot.send_message(call.message.chat.id, f"Estado del sistema: {status_info}")
    
    elif call.data == "pwd":
        # Mostrar el directorio actual
        current_dir = llamadaSistema("pwd")
        bot.send_message(call.message.chat.id, f"Directorio actual: {current_dir}")
    
    elif call.data == "ls":
        # Mostrar los archivos en el directorio actual
        files = llamadaSistema("ls")
        bot.send_message(call.message.chat.id, f"Archivos:\n{files}")
    
# Función para mostrar el menú principal de torrents
def mostrar_menu_torrents(message):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("Agregar Torrent", callback_data="agregar_torrent"),
        InlineKeyboardButton("Ver Estado Descargas", callback_data="estado_descargas"),
        InlineKeyboardButton("Listar Torrents", callback_data="listar_torrents"),
        InlineKeyboardButton("Eliminar Torrent", callback_data="eliminar_torrent")
    )
    bot.send_message(message.chat.id, "Elige una opción:", reply_markup=markup)

# Manejador para el comando /torrents
@bot.message_handler(commands=['torrents'])
def handle_torrents(message):
    mostrar_menu_torrents(message)

# Manejador de callbacks para torrents
@bot.callback_query_handler(func=lambda call: call.data in ["agregar_torrent", "estado_descargas", "listar_torrents", "eliminar_torrent"])
def handle_torrent_callback(call):
    if call.data == "agregar_torrent":
        bot.send_message(call.message.chat.id, "Envía el enlace del torrent (magnet o archivo):")
        bot.register_next_step_handler(call.message, agregar_torrent_step)

    elif call.data == "estado_descargas":
        respuesta = estado_descargas()
        bot.send_message(call.message.chat.id, respuesta)

    elif call.data == "listar_torrents":
        respuesta = listar_torrents()
        bot.send_message(call.message.chat.id, respuesta)

    elif call.data == "eliminar_torrent":
        bot.send_message(call.message.chat.id, "Envía el ID del torrent que deseas eliminar:")
        bot.register_next_step_handler(call.message, eliminar_torrent_step)

# Función para manejar el agregar torrent después de recibir el enlace
def agregar_torrent_step(message):
    print(f"Mensaje recibido en agregar_torrent_step: {message.text}")  # Depuración
    url = message.text  # Obtener el URL enviado por el usuario
    logging.info("Torrent recibido: %s (user=%s)", url, message.from_user.username or message.from_user.id)
    respuesta = agregar_torrent(url)
    bot.send_message(message.chat.id, respuesta)

# Función para manejar la eliminación de torrent después de recibir el ID
def eliminar_torrent_step(message):
    print(f"Mensaje recibido en eliminar_torrent_step: {message.text}")  # Depuración
    logging.info("Solicitud eliminar torrent: %s (user=%s)", message.text, message.from_user.username or message.from_user.id)
    try:
        torrent_id = int(message.text)  # Obtener el ID enviado por el usuario
        respuesta = eliminar_torrent(torrent_id)
        bot.send_message(message.chat.id, respuesta)
    except ValueError:
        bot.send_message(message.chat.id, "El ID del torrent debe ser un número.")

def _read_temp_c():
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            return float(f.read().strip()) / 1000.0
    except Exception:
        return None

def _read_mem_percent():
    try:
        meminfo = {}
        with open("/proc/meminfo", "r") as f:
            for line in f:
                k, v = line.split(":")
                meminfo[k] = int(v.strip().split()[0])
        total = meminfo.get("MemTotal", 0)
        avail = meminfo.get("MemAvailable", 0)
        if total:
            used = total - avail
            return int(used * 100 / total)
    except Exception:
        pass
    return None

def _get_display_payload():
    now = time.time()

    with _state_lock:
        last_text = display_state["last_text"]
        last_ts = display_state["last_ts"]

    # 1) Si hubo actividad en los últimos 30s, muéstrala
    if now - last_ts < 30 and last_text:
        return {
            "title": "PatanaBot",
            "right": time.strftime("%H:%M"),
            "line1": f"IP {obtener_ip()}",
            "line2": "Último comando:",
            "line3": last_text[:20],
        }

    # 2) Si no, rota pantallas cada 6s
    page = int(now / 6) % 3

    if page == 0:
        return {
            "title": "PatanaBot",
            "right": time.strftime("%H:%M"),
            "line1": "Modo idle",
            "line2": f"IP {obtener_ip()}",
            "line3": "",
        }

    if page == 1:
        temp = _read_temp_c()
        mem = _read_mem_percent()
        t = f"{temp:.1f}C" if temp is not None else "N/A"
        m = f"{mem}%" if mem is not None else "N/A"
        return {
            "title": "Sistema",
            "right": time.strftime("%H:%M"),
            "line1": f"TEMP {t}",
            "line2": f"RAM {m}",
            "line3": "",
        }

    # page == 2
    return {
        "title": "Torrents/Minecraft",
        "right": time.strftime("%H:%M"),
        "line1": "Listo",
        "line2": "Usa /torrents",
        "line3": "o /mc",
    }


if __name__ == "__main__":
    # Mensaje solo al arrancar (si reinicia el servicio, lo mandará de nuevo)
    try:
        if ADMIN_ID:
            bot.send_message(ADMIN_ID, "¡Desperté!", disable_notification=True)
    except Exception as e:
        logging.exception("No pude enviar mensaje de arranque: %s", e)

    try:
        bot.remove_webhook()
    except Exception:
        pass

    start_auto_update(_get_display_payload, interval=2)
    # Infinity polling = bucle interno con reconexión
    bot.infinity_polling(timeout=20, long_polling_timeout=20, skip_pending=True)
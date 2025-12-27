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
from handlers.minecraft_handler import minecraft, handle_minecraft_callback, mc_players_online, mc_last_activity, _mc_players_cached, _mc_state_cached
from handlers.transmission_handler import register_transmission_handlers, get_oled_torrent_status
from logger import setup_logging

setup_logging()

TOKEN = os.getenv("TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

if not TOKEN:
    raise RuntimeError("Falta TOKEN en variables de entorno (archivo .env o export).")

bot = telebot.TeleBot(token=TOKEN)

display_state = {"last_text": "","last_ts": 0.0,}
_state_lock = threading.Lock()

def note_display(text: str):
    with _state_lock:
        display_state["last_text"] = text
        display_state["last_ts"] = time.time()
        
register_transmission_handlers(bot, on_activity=note_display)

ALERT_TEMP_C = float(os.getenv("ALERT_TEMP_C", "70"))
ALERT_RAM_PCT = int(os.getenv("ALERT_RAM_PCT", "85"))
ALERT_COOLDOWN_S = int(os.getenv("ALERT_COOLDOWN_S", "1800"))  # 30 min

_last_alert_sent = 0.0
_last_alert_key = ""

def _bar(pct: int, width: int = 10) -> str:
    pct = max(0, min(100, pct))
    filled = int(pct * width / 100)
    return "█" * filled + "░" * (width - filled)

def _maybe_notify_admin(alert_key: str, text: str):
    global _last_alert_sent, _last_alert_key
    if not ADMIN_ID:
        return
    now = time.time()
    if alert_key == _last_alert_key and (now - _last_alert_sent) < ALERT_COOLDOWN_S:
        return
    _last_alert_key = alert_key
    _last_alert_sent = now
    try:
        bot.send_message(ADMIN_ID, text, disable_notification=True)
    except Exception:
        pass

@bot.message_handler(commands=['apagar'])
def handle_apagar(message):
    # Solo el administrador puede apagar el sistema
    if message.from_user.id == ADMIN_ID:
        bot.reply_to(message, "Apagando la Raspberry Pi...")
        os.system("sudo shutdown now")
    else:
        bot.reply_to(message, "No tienes permiso para apagar el sistema.")
    
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

    # Lecturas sistema
    temp = _read_temp_c()
    mem = _read_mem_percent()

    temp_alert = (temp is not None and temp >= ALERT_TEMP_C)
    mem_alert = (mem is not None and mem >= ALERT_RAM_PCT)

    # Estado torrents + MC
    tr = get_oled_torrent_status(cache_seconds=5)  # None si no hay actividad
    mc_state, mc_status = _mc_state_cached(cache_seconds=5)

    # 1) ALERTAS: prioridad máxima
    if temp_alert or mem_alert:
        parts = []
        if temp_alert:
            parts.append(f"TEMP {temp:.1f}C")
        if mem_alert:
            parts.append(f"RAM {mem}%")
        key = " & ".join(parts)

        # OLED
        payload = {
            "title": "⚠ ALERTA",
            "right": time.strftime("%H:%M"),
            "line1": parts[0] if parts else "ALERTA",
            "line2": parts[1] if len(parts) > 1 else "",
            "line3": f"IP {obtener_ip()}",
        }

        # Telegram (opcional, con cooldown)
        _maybe_notify_admin(key, f"⚠️ PatanaBot alerta: {key}")

        return payload

    # 2) Actividad reciente del bot: se muestra un ratito
    if now - last_ts < 20 and last_text:
        return {
            "title": "PatanaBot",
            "right": time.strftime("%H:%M"),
            "line1": f"IP {obtener_ip()}",
            "line2": "Último comando:",
            "line3": last_text[:20],
        }

    # 3) Construir lista de pantallas (con prioridad)
    screens = []

    # 3a) Minecraft arrancando: MUY prioritario
    if mc_state == "starting":
        screens.append({
            "title": "Minecraft",
            "right": time.strftime("%H:%M"),
            "line1": "Arrancando...",
            "line2": "Espera ~15-60s",
            "line3": "Puerto 25565",
        })

    # 3b) Torrents activos: prioridad alta (y los repetimos para que salga más)
    if tr:
        name = tr["name"]
        short = (name[:16] + "…") if len(name) > 17 else name
        dl_kb = tr["dl"] // 1024
        ul_kb = tr["ul"] // 1024
        bar = _bar(tr["progress"], 10)

        torrent_screen = {
            "title": f"Torrents ({tr['count']})",
            "right": time.strftime("%H:%M"),
            "line1": short,
            "line2": f"{bar} {tr['progress']}%",
            "line3": f"DL {dl_kb} UL {ul_kb} KB/s",
        }
        screens.append(torrent_screen)
        screens.append(torrent_screen)  # <- “peso” extra: aparece el doble

    # 3c) Minecraft ON: mostrar players (cacheado)
    if mc_state == "on":
        count, names = _mc_players_cached(cache_seconds=10)
        who = (names[0][:16] + "…") if names else "nadie"
        screens.append({
            "title": "Minecraft",
            "right": time.strftime("%H:%M"),
            "line1": "Online ✅",
            "line2": f"Jugadores: {count}",
            "line3": f"Top: {who}" if count else "Sin jugadores",
        })

    # 3d) Pantalla sistema siempre
    t = f"{temp:.1f}C" if temp is not None else "N/A"
    m = f"{mem}%" if mem is not None else "N/A"
    screens.append({
        "title": "Sistema",
        "right": time.strftime("%H:%M"),
        "line1": f"IP {obtener_ip()}",
        "line2": f"TEMP {t}",
        "line3": f"RAM {m}",
    })

    # 3e) Pantalla tips siempre
    screens.append({
        "title": "Atajos",
        "right": time.strftime("%H:%M"),
        "line1": "/mc  /torrents",
        "line2": "/status  /ip",
        "line3": "",
    })

    # 4) Rotación (cada 6s)
    idx = int(now / 6) % len(screens)
    return screens[idx]

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
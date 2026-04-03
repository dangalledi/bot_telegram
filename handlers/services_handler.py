# handlers/services_handler.py

import subprocess
import logging

from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from logger import log_action

SERVICES = {
    "plex": "plexmediaserver",
    "zerotier": "zerotier-one",
}

def _service_status(service_name: str) -> str:
    result = subprocess.run(
        ["systemctl", "is-active", service_name],
        capture_output=True, text=True
    )
    return result.stdout.strip()  # "active" | "inactive" | "failed"

def _service_action(action: str, service_name: str) -> int:
    result = subprocess.run(
        ["sudo", "systemctl", action, service_name],
        capture_output=True, text=True
    )
    return result.returncode

def _user(message):
    return message.from_user.username or str(message.from_user.id)

def _gen_markup(cmd: str) -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup(row_width=3)
    markup.add(
        InlineKeyboardButton("Estado",   callback_data=f"svc:{cmd}:status"),
        InlineKeyboardButton("Encender", callback_data=f"svc:{cmd}:start"),
        InlineKeyboardButton("Apagar",   callback_data=f"svc:{cmd}:stop"),
    )
    return markup

def services(bot, message, ADMIN_IDS):
    parts = message.text.strip().split()
    cmd = parts[0].lstrip("/").lower()  # "plex" o "zerotier"
    action = parts[1].lower() if len(parts) > 1 else None

    if cmd not in SERVICES:
        bot.reply_to(message, f"Servicio desconocido: {cmd}")
        return

    service_name = SERVICES[cmd]

    if action in ("on", "off", "start", "stop") and message.from_user.id not in ADMIN_IDS:
        logging.warning("action user=%s cmd=/%s action=%s DENIED (not admin)", _user(message), cmd, action)
        bot.reply_to(message, "No tienes permiso para hacer eso.")
        return

    if action in ("on", "start"):
        rc = _service_action("start", service_name)
        if rc == 0:
            log_action(_user(message), f"/{cmd}", "start OK")
            bot.reply_to(message, f"{cmd} arrancado.", reply_markup=_gen_markup(cmd))
        else:
            log_action(_user(message), f"/{cmd}", f"start FAILED rc={rc}")
            bot.reply_to(message, f"Error al arrancar {cmd}.", reply_markup=_gen_markup(cmd))

    elif action in ("off", "stop"):
        rc = _service_action("stop", service_name)
        if rc == 0:
            log_action(_user(message), f"/{cmd}", "stop OK")
            bot.reply_to(message, f"{cmd} parado.", reply_markup=_gen_markup(cmd))
        else:
            log_action(_user(message), f"/{cmd}", f"stop FAILED rc={rc}")
            bot.reply_to(message, f"Error al parar {cmd}.", reply_markup=_gen_markup(cmd))

    else:
        # Sin argumento: mostrar estado + botones
        status = _service_status(service_name)
        estado = "activo" if status == "active" else status
        log_action(_user(message), f"/{cmd}", f"status={status}")
        bot.reply_to(message, f"{cmd}: {estado}", reply_markup=_gen_markup(cmd))


def handle_service_callback(bot, call, ADMIN_IDS):
    try:
        bot.answer_callback_query(call.id)
    except Exception:
        pass

    # call.data formato: "svc:plex:start" | "svc:zerotier:stop" | "svc:plex:status"
    parts = call.data.split(":")
    if len(parts) != 3:
        return

    _, cmd, action = parts

    if cmd not in SERVICES:
        bot.send_message(call.message.chat.id, f"Servicio desconocido: {cmd}")
        return

    service_name = SERVICES[cmd]

    if action in ("start", "stop") and call.from_user.id not in ADMIN_IDS:
        logging.warning("action user=%s svc:%s:%s DENIED (not admin)", _user(call), cmd, action)
        bot.answer_callback_query(call.id, "No autorizado", show_alert=True)
        return

    if action == "start":
        rc = _service_action("start", service_name)
        if rc == 0:
            log_action(_user(call), f"svc:{cmd}", "start OK")
            bot.send_message(call.message.chat.id, f"{cmd} arrancado.", reply_markup=_gen_markup(cmd))
        else:
            log_action(_user(call), f"svc:{cmd}", f"start FAILED rc={rc}")
            bot.send_message(call.message.chat.id, f"Error al arrancar {cmd}.", reply_markup=_gen_markup(cmd))

    elif action == "stop":
        rc = _service_action("stop", service_name)
        if rc == 0:
            log_action(_user(call), f"svc:{cmd}", "stop OK")
            bot.send_message(call.message.chat.id, f"{cmd} parado.", reply_markup=_gen_markup(cmd))
        else:
            log_action(_user(call), f"svc:{cmd}", f"stop FAILED rc={rc}")
            bot.send_message(call.message.chat.id, f"Error al parar {cmd}.", reply_markup=_gen_markup(cmd))

    elif action == "status":
        status = _service_status(service_name)
        estado = "activo" if status == "active" else status
        log_action(_user(call), f"svc:{cmd}", f"status={status}")
        bot.send_message(call.message.chat.id, f"{cmd}: {estado}", reply_markup=_gen_markup(cmd))

# handlers/services_handler.py

import subprocess
import logging

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

def _service_action(action: str, service_name: str) -> str:
    result = subprocess.run(
        ["sudo", "systemctl", action, service_name],
        capture_output=True, text=True
    )
    return result.returncode

def _user(message):
    return message.from_user.username or str(message.from_user.id)

def services(bot, message, ADMIN_IDS):
    parts = message.text.strip().split()
    # /plex | /plex on | /plex off
    # parts[0] = "/plex", parts[1] = "on"/"off" (opcional)

    cmd = parts[0].lstrip("/").lower()  # "plex" o "zerotier"
    action = parts[1].lower() if len(parts) > 1 else None

    if cmd not in SERVICES:
        bot.reply_to(message, f"Servicio desconocido: {cmd}")
        return

    service_name = SERVICES[cmd]

    # Solo admins pueden cambiar estado
    if action in ("on", "off") and message.from_user.id not in ADMIN_IDS:
        logging.warning("action user=%s cmd=/%s action=%s DENIED (not admin)", _user(message), cmd, action)
        bot.reply_to(message, "No tienes permiso para hacer eso.")
        return

    if action == "on":
        rc = _service_action("start", service_name)
        if rc == 0:
            log_action(_user(message), f"/{cmd}", "start OK")
            bot.reply_to(message, f"{cmd} arrancado.")
        else:
            log_action(_user(message), f"/{cmd}", f"start FAILED rc={rc}")
            bot.reply_to(message, f"Error al arrancar {cmd}.")

    elif action == "off":
        rc = _service_action("stop", service_name)
        if rc == 0:
            log_action(_user(message), f"/{cmd}", "stop OK")
            bot.reply_to(message, f"{cmd} parado.")
        else:
            log_action(_user(message), f"/{cmd}", f"stop FAILED rc={rc}")
            bot.reply_to(message, f"Error al parar {cmd}.")

    else:
        # Solo status
        status = _service_status(service_name)
        estado = "activo" if status == "active" else status
        log_action(_user(message), f"/{cmd}", f"status={status}")
        bot.reply_to(message, f"{cmd}: {estado}")
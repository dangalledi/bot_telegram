# handlers/system_commands.py

import os
import re
from utils import llamadaSistema, obtener_ip
from oled_display import actualizar_pantalla
from logger import log_action
import logging
import subprocess
import threading
import time
from datetime import datetime
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

def _user(message):
    return message.from_user.username or str(message.from_user.id)

def _bar(pct: int, width: int = 10) -> str:
    pct = max(0, min(100, pct))
    filled = int(pct * width / 100)
    return "█" * filled + "░" * (width - filled)

def status(bot, message):
    try:
        cpu_line = llamadaSistema("top -bn1 | grep 'Cpu(s)'")
        memory_usage = llamadaSistema("free -m")
        disk_usage = llamadaSistema("df -h /")
        temp = llamadaSistema("vcgencmd measure_temp")

        # CPU %
        cpu_pct = None
        for part in cpu_line.split(","):
            if "id" in part:
                try:
                    idle = float(part.strip().split()[0])
                    cpu_pct = int(100 - idle)
                except ValueError:
                    pass

        # RAM
        memoria_datos = memory_usage.splitlines()[1].split()
        mem_total = int(memoria_datos[1])
        mem_usada = int(memoria_datos[2])
        mem_libre  = int(memoria_datos[3])
        mem_pct = int(mem_usada * 100 / mem_total) if mem_total else 0

        # Disco /
        disk_line = disk_usage.splitlines()[-1].split()
        disk_size  = disk_line[1]
        disk_used  = disk_line[2]
        disk_avail = disk_line[3]
        disk_pct   = int(disk_line[4].replace("%", ""))

        # Disco /media/disco
        disk2_raw = llamadaSistema("df -h /media/disco")
        disk2_line = disk2_raw.splitlines()[-1].split()
        disk2_size  = disk2_line[1]
        disk2_used  = disk2_line[2]
        disk2_avail = disk2_line[3]
        disk2_pct   = int(disk2_line[4].replace("%", ""))

        # Temp
        temp_val = temp.replace("temp=", "").replace("'C", " °C")

        cpu_bar   = _bar(cpu_pct) if cpu_pct is not None else "N/A"
        mem_bar   = _bar(mem_pct)
        disk_bar  = _bar(disk_pct)
        disk2_bar = _bar(disk2_pct)

        cpu_str = f"{cpu_bar} {cpu_pct}%" if cpu_pct is not None else "N/A"

        respuesta = (
            "*Estado del sistema*\n\n"
            f"*Temperatura:* `{temp_val}`\n\n"
            f"*CPU:*\n`{cpu_str}`\n\n"
            f"*RAM:*\n`{mem_bar} {mem_pct}%`\n"
            f"  Usada: {mem_usada} MB / {mem_total} MB  •  Libre: {mem_libre} MB\n\n"
            f"*Disco (/):*\n`{disk_bar} {disk_pct}%`\n"
            f"  Usado: {disk_used} / {disk_size}  •  Libre: {disk_avail}\n\n"
            f"*Disco (/media/disco):*\n`{disk2_bar} {disk2_pct}%`\n"
            f"  Usado: {disk2_used} / {disk2_size}  •  Libre: {disk2_avail}"
        )

        bot.reply_to(message, respuesta, parse_mode="Markdown")
        log_action(_user(message), "/status")
        actualizar_pantalla("Estado del sistema mostrado")
    except Exception as e:
        logging.exception("Error en /status: %s", e)
        bot.reply_to(message, f"Error al obtener el estado del sistema: {e}")
        actualizar_pantalla("Error en estado")

_IFACE_LABELS = {
    "eth0":        "Ethernet",
    "wlan0":       "WiFi",
    "tailscale0":  "Tailscale",
    "ztXXXXXXXX":  "ZeroTier",  # patrón genérico; se sobreescribe abajo
}

def _get_labeled_ips() -> list[tuple[str, str]]:
    """
    Devuelve lista de (label, ip) para interfaces conocidas.
    Usa `ip -o -4 addr` para obtener interfaz + IP.
    """
    raw = llamadaSistema("ip -o -4 addr")
    result = []
    seen = set()
    for line in raw.splitlines():
        # formato: "2: eth0    inet 192.168.1.10/24 ..."
        m = re.match(r"\d+:\s+(\S+)\s+inet\s+([\d.]+)", line)
        if not m:
            continue
        iface, addr = m.group(1), m.group(2)
        if addr in seen or addr.startswith("127."):
            continue
        seen.add(addr)
        # Detectar ZeroTier (interfaz tipo zt...)
        if iface.startswith("zt"):
            label = "ZeroTier"
        else:
            label = _IFACE_LABELS.get(iface, iface)
        result.append((label, addr))
    return result


def ip(bot, message):
    entries = _get_labeled_ips()
    if not entries:
        texto = "*IP de la Raspberry:*\nNo se encontraron interfaces activas."
    else:
        lineas = "\n".join(f"  {label}: `{addr}`" for label, addr in entries)
        texto = f"*IPs de la Raspberry:*\n{lineas}"

    bot.reply_to(message, texto, parse_mode="Markdown")
    log_action(_user(message), "/ip")
    first_ip = entries[0][1] if entries else "?"
    actualizar_pantalla(f"IP: {first_ip}")


def logs(bot, message, log_path: str = "log/bot.log", n: int = 20):
    """Muestra las últimas n líneas del log de auditoría."""
    # Soporte para /logs 30
    parts = (message.text or "").strip().split()
    if len(parts) > 1:
        try:
            n = max(1, min(int(parts[1]), 50))
        except ValueError:
            pass

    try:
        if not os.path.exists(log_path):
            bot.reply_to(message, "No se encontró el archivo de log.")
            return
        with open(log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        chunk = lines[-n:] if len(lines) >= n else lines
        text = "".join(chunk).strip()
        if not text:
            bot.reply_to(message, "El log está vacío.")
            return
        if len(text) > 3800:
            text = text[-3800:]
        bot.reply_to(message, f"Ultimas {len(chunk)} lineas:\n```\n{text}\n```", parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"Error al leer el log: {e}")
        
# =======================================
# =========== backup image pi ===========
# =======================================

_backup_state = {"running": False, "session": "", "filename": "", "started": ""}

def backup(bot, message, ADMIN_IDS):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "No tienes permiso para hacer un backup.")
        return

    if _backup_state["running"]:
        bot.reply_to(message, 
            f"Ya hay un backup en curso:\n"
            f"Sesión: `{_backup_state['session']}`\n"
            f"Iniciado: {_backup_state['started']}\n"
            f"Archivo: `{_backup_state['filename']}`",
            parse_mode="Markdown")
        return

    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("Sí, hacer backup", callback_data="backup:confirm"),
        InlineKeyboardButton("Cancelar", callback_data="backup:cancel"),
    )
    bot.reply_to(message, " Esto puede tardar 15-20 min y cargará la Pi. ¿Confirmas?", reply_markup=markup)


def backup_status(bot, message):
    if _backup_state["running"]:
        bot.reply_to(message,
            f"Backup en curso:\n"
            f"Sesión tmux: `{_backup_state['session']}`\n"
            f"Iniciado: {_backup_state['started']}\n"
            f"Archivo: `{_backup_state['filename']}`\n\n"
            f"Para verlo en vivo:\n`tmux attach -t {_backup_state['session']}`",
            parse_mode="Markdown")
    else:
        bot.reply_to(message, "No hay ningún backup en curso.")


def run_backup_thread(bot, chat_id, ADMIN_IDS):
    def _run():
        filename = f"/media/disco/backup_raspberry_{datetime.now().strftime('%Y%m%d')}.img.gz"
        session = f"backup_{datetime.now().strftime('%Y%m%d_%H%M')}"
        started = datetime.now().strftime('%Y-%m-%d %H:%M')

        _backup_state["running"]  = True
        _backup_state["session"]  = session
        _backup_state["filename"] = filename
        _backup_state["started"]  = started

        status_file = f"/tmp/backup_done_{session}"

        cmd = (
            f"tmux new-session -d -s {session} "
            f"'sudo dd if=/dev/mmcblk0 bs=4M status=progress | gzip > {filename} "
            f"&& echo OK > {status_file} || echo FAIL > {status_file}'"
        )
        subprocess.run(cmd, shell=True)

        bot.send_message(chat_id,
            f"Backup iniciado en tmux session `{session}`\n"
            f"Archivo: `{filename}`\n\n"
            f"Ver en vivo:\n`ssh pi@patana.local`\n`tmux attach -t {session}`",
            parse_mode="Markdown")

        # Esperar a que termine
        while True:
            time.sleep(30)
            r = subprocess.run(f"tmux has-session -t {session}", shell=True)
            if r.returncode != 0:
                # Sesión terminada — leer resultado
                success = False
                if os.path.exists(status_file):
                    with open(status_file) as f:
                        success = f.read().strip() == "OK"
                    os.remove(status_file)

                _backup_state["running"]  = False
                _backup_state["session"]  = ""
                _backup_state["filename"] = ""
                _backup_state["started"]  = ""

                msg = (
                    f"Backup completado:\n`{filename}`"
                    if success else
                    f"Backup falló. Revisa la sesión tmux o los logs."
                )
                for admin_id in ADMIN_IDS:
                    try:
                        bot.send_message(admin_id, msg, parse_mode="Markdown")
                    except Exception:
                        pass
                break

    threading.Thread(target=_run, daemon=True).start()
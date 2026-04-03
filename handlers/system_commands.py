# handlers/system_commands.py

import re
from utils import llamadaSistema, obtener_ip
from oled_display import actualizar_pantalla
from logger import log_action
import logging

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

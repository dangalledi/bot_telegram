# handlers/system_commands.py

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

def ip(bot, message):
    ips = obtener_ip().split()
    if len(ips) == 1:
        texto = f"*IP de la Raspberry:*\n`{ips[0]}`"
    else:
        lineas = "\n".join(f"`{ip}`" for ip in ips)
        texto = f"*IPs de la Raspberry:*\n{lineas}"

    bot.reply_to(message, texto, parse_mode="Markdown")
    log_action(_user(message), "/ip")
    actualizar_pantalla(f"IP: {ips[0] if ips else '?'}")

# handlers/minecraft_handler.py
import os
import time
import logging
from typing import Optional, Tuple
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import re

from utils import llamadaSistema
from logger import log_action

_MC_CACHE = {"ts": 0.0, "state": "off", "status": ""}
_MC_PLAYERS_CACHE = {"ts": 0.0, "count": 0, "names": []}

def _user(obj):
    u = getattr(obj, "from_user", None)
    if not u:
        return "unknown"
    return u.username or str(u.id)

def _container_name():
    return os.getenv("MC_CONTAINER", "minecraft").strip()

def _compose_file():
    cf = os.getenv("MC_COMPOSE_FILE", "").strip()
    return cf if cf else None

def _has_docker_compose_v2():
    out = llamadaSistema("docker compose version 2>/dev/null").strip()
    return bool(out)

def _compose_cmd():
    cf = _compose_file()
    if not cf:
        return None
    # prefer v2
    if _has_docker_compose_v2():
        return f"docker compose -f {cf}"
    # fallback v1
    return f"docker-compose -f {cf}"

def mc_status_text():
    name = _container_name()
    status = llamadaSistema(
        f"docker ps -a --filter name={name} --format '{{{{.Status}}}}'"
    ).strip()

    if not status:
        return f"Contenedor `{name}` no encontrado.", False

    running = status.lower().startswith("up")
    return f"{name}: {status}", running

def mc_start():
    comp = _compose_cmd()
    if comp:
        return llamadaSistema(f"{comp} up -d").strip() or "OK"
    return llamadaSistema(f"docker start {_container_name()}").strip() or "OK"

def mc_stop():
    name = _container_name()
    if _is_running():
        llamadaSistema(f"docker exec {name} rcon-cli save-all 2>/dev/null")
        llamadaSistema(f"docker exec {name} rcon-cli stop 2>/dev/null")
        time.sleep(2)
        return "Envié stop por RCON (apaga guardando)."
    return "Servidor ya estaba apagado."

def mc_detail():
    name = _container_name()
    comp = _compose_cmd()

    if comp:
        ps = llamadaSistema(f"{comp} ps").strip()
    else:
        ps = llamadaSistema(f"docker ps -a --filter name={name}").strip()

    logs = llamadaSistema(f"docker logs --tail 30 {name}").strip()
    out = f"{ps}\n\n--- logs (tail 30) ---\n{logs}"
    return out

def gen_markup_mc():
    markup = InlineKeyboardMarkup(row_width=3)
    markup.add(
        InlineKeyboardButton("Apagar", callback_data="mc:stop"),
        InlineKeyboardButton("Encender", callback_data="mc:start"),
        InlineKeyboardButton("Detalle", callback_data="mc:detalle"),
    )
    markup.add(
        InlineKeyboardButton("Online", callback_data="mc:online"),
        InlineKeyboardButton("Último", callback_data="mc:last"),
    )
    return markup

def minecraft(bot, message):
    text, running = mc_status_text()
    extra = ""
    if running:
        _, count, names = mc_players_online()
        if count > 0:
            extra = f"\n\n👥 Online ({count}): " + ", ".join(names)
        else:
            extra = "\n\n👥 Online: 0"
    bot.send_message(message.chat.id, f"Estado Minecraft:\n{text}{extra}", reply_markup=gen_markup_mc())

def handle_minecraft_callback(bot, call):
    # call.data: mc:stop | mc:start | mc:detalle
    try:
        bot.answer_callback_query(call.id)
    except Exception:
        pass

    action = call.data

    if action == "mc:stop":
        out = mc_stop()
        msg = f"🛑 Stop:\n{out}"
    elif action == "mc:start":
        out = mc_start()
        msg = f"▶️ Start:\n{out}"
    elif action == "mc:detalle":
        out = mc_detail()
        # Telegram limita longitud; recortamos por seguridad
        if len(out) > 3500:
            out = out[-3500:]
        msg = f"ℹ️ Detalle:\n{out}"
    elif action == "mc:online":
        text, count, names = mc_players_online()
        if count == 0:
            msg = f"👥 {text}"  # "Servidor apagado." o "No pude leer jugadores..."
        else:
            msg = "👥 Online:\n- " + "\n- ".join(names)
    elif action == "mc:last":
        msg = "🕒 Última actividad:\n" + mc_last_activity()
    else:
        msg = "Comando desconocido."

    logging.info("minecraft action=%s", action)
    log_action(_user(call), action)
    bot.send_message(call.message.chat.id, msg)
    
def _is_running():
    name = _container_name()
    out = llamadaSistema(f"docker inspect -f '{{{{.State.Running}}}}' {name} 2>/dev/null").strip()
    return out == "true"
    
def mc_players_online():
    if not _is_running():
        return "Servidor apagado.", 0, []
    name = _container_name()
    # "There are 0 of a max of 20 players online: "
    out = llamadaSistema(f"docker exec {name} rcon-cli list 2>/dev/null").strip()
    m = re.search(r"There are (\d+) of a max of \d+ players online(?:: (.*))?", out)
    if not m:
        return "No pude leer jugadores (RCON).", 0, []
    count = int(m.group(1))
    names = []
    if m.group(2):
        names = [x.strip() for x in m.group(2).split(",") if x.strip()]
    return out, count, names

def mc_last_activity():
    name = _container_name()
    lines = llamadaSistema(f"docker logs --tail 500 {name} 2>/dev/null").splitlines()
    if not lines:
        return "Sin logs."

    patterns = [
        re.compile(r".*\bjoined the game\b.*", re.IGNORECASE),
        re.compile(r".*\bleft the game\b.*", re.IGNORECASE),
        re.compile(r".*\blogged in with entity id\b.*", re.IGNORECASE),
        re.compile(r".*\blost connection\b.*", re.IGNORECASE),
    ]

    # Ignorar errores ruidosos de log4j
    ignore = re.compile(r"Unable to locate appender|TerminalConsole", re.IGNORECASE)

    for line in reversed(lines):
        if ignore.search(line):
            continue
        for rx in patterns:
            if rx.search(line):
                return line

    # fallback: última línea no ignorada
    for line in reversed(lines):
        if not ignore.search(line):
            return line

    return lines[-1]

def _mc_state_cached(cache_seconds: int = 5) -> Tuple[str, str]:
    """
    state: off | starting | on
    status: texto (docker ps status)
    """
    now = time.time()
    if now - _MC_CACHE["ts"] < cache_seconds:
        return _MC_CACHE["state"], _MC_CACHE["status"]

    name = os.getenv("MC_CONTAINER", "minecraft").strip()
    status = llamadaSistema(f"docker ps -a --filter name={name} --format '{{{{.Status}}}}'").strip()

    if not status:
        state = "off"
    else:
        s = status.lower()
        if s.startswith("up"):
            # ejemplos: "Up 2 minutes (healthy)" / "Up 30 seconds (health: starting)"
            if "health: starting" in s or "starting" in s and "healthy" not in s:
                state = "starting"
            else:
                state = "on"
        else:
            state = "off"

    _MC_CACHE.update({"ts": now, "state": state, "status": status})
    return state, status

def _mc_players_cached(cache_seconds: int = 10):
    now = time.time()
    if now - _MC_PLAYERS_CACHE["ts"] < cache_seconds:
        return _MC_PLAYERS_CACHE["count"], _MC_PLAYERS_CACHE["names"]
    try:
        text, count, names = mc_players_online()  # tu función (usa rcon-cli)
        _MC_PLAYERS_CACHE.update({"ts": now, "count": count, "names": names})
        return count, names
    except Exception:
        _MC_PLAYERS_CACHE.update({"ts": now, "count": 0, "names": []})
        return 0, []


# handlers/transmission_handler.py
import os
import logging
from typing import Optional, Callable, Tuple, List, Dict, Any

import transmission_rpc
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

import time
_last_oled = None
_last_oled_ts = 0.0

from logger import log_action

# Opcional: restringir acciones al admin
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

_client: Optional[transmission_rpc.Client] = None


def _user(obj) -> str:
    u = getattr(obj, "from_user", None)
    if not u:
        return "unknown"
    return u.username or str(u.id)


def _is_admin(obj) -> bool:
    if not ADMIN_ID:
        return True
    u = getattr(obj, "from_user", None)
    return bool(u and u.id == ADMIN_ID)


def _get_client() -> transmission_rpc.Client:
    """
    Lazy init: evita fallos al importar si env vars no existen,
    y permite que systemd cargue .env antes.
    """
    global _client
    if _client is not None:
        return _client

    host = os.getenv("TRANSMISSION_HOST", "localhost")
    port = int(os.getenv("TRANSMISSION_PORT", "9091"))
    username = os.getenv("TRANSMISSION_USER") or None
    password = os.getenv("TRANSMISSION_PASSWORD") or None

    _client = transmission_rpc.Client(host=host, port=port, username=username, password=password)
    return _client


def _menu_markup() -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("➕ Agregar", callback_data="tr:add"),
        InlineKeyboardButton("📊 Estado", callback_data="tr:status"),
        InlineKeyboardButton("📋 Listar", callback_data="tr:list:0"),
        InlineKeyboardButton("🗑️ Eliminar", callback_data="tr:delete"),
    )
    return markup


def _fmt_size(bytes_val: Optional[int]) -> str:
    if bytes_val is None:
        return "N/A"
    size = float(bytes_val)
    units = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size >= 1024 and i < len(units) - 1:
        size /= 1024
        i += 1
    return f"{size:.2f} {units[i]}"


def _fmt_rate(bytes_per_s: Optional[float]) -> str:
    if bytes_per_s is None:
        return "0 KB/s"
    return _fmt_size(int(bytes_per_s)) + "/s"


def _fmt_torrent_line(t) -> str:
    # transmission-rpc expone varios campos; usamos los más comunes
    tid = getattr(t, "id", "?")
    name = getattr(t, "name", "Sin nombre")
    # progress suele venir 0..100 en transmission-rpc; percent_done 0..1
    progress = getattr(t, "progress", None)
    if progress is None:
        pd = getattr(t, "percent_done", None)
        progress = int(pd * 100) if isinstance(pd, (int, float)) else 0

    status = getattr(t, "status", "")
    eta = getattr(t, "eta", None)  # puede ser int (segundos) o str
    rate_dl = getattr(t, "rateDownload", None)
    rate_ul = getattr(t, "rateUpload", None)

    # Compacto para telegram
    short = (name[:40] + "…") if len(name) > 41 else name
    eta_txt = "N/A"
    try:
        if isinstance(eta, int) and eta >= 0:
            mins = eta // 60
            eta_txt = f"{mins}m" if mins < 240 else f"{mins//60}h"
        elif isinstance(eta, str) and eta:
            eta_txt = eta
    except Exception:
        pass

    return f"{tid:>3} | {progress:>3}% | DL {_fmt_rate(rate_dl)} UL {_fmt_rate(rate_ul)} | ETA {eta_txt} | {short}"


def _safe_send(bot, chat_id: int, text: str, reply_markup=None):
    # Telegram ~4096 chars; recortamos
    if len(text) > 3800:
        text = text[:3800] + "\n…(recortado)"
    bot.send_message(chat_id, text, reply_markup=reply_markup)


def register_transmission_handlers(bot, on_activity: Optional[Callable[[str], None]] = None):
    """
    Registra /torrents y callbacks tr:* dentro del módulo para limpiar bot.py.
    on_activity: callback opcional para actualizar OLED (note_display).
    """

    def activity(obj, text: str):
        if on_activity:
            on_activity(text)
        log_action(_user(obj), text)

    @bot.message_handler(commands=["torrents", "tr"])
    def _cmd_torrents(message):
        if not _is_admin(message):
            bot.reply_to(message, "No tienes permiso para usar torrents.")
            return
        activity(message, "/torrents")
        _safe_send(bot, message.chat.id, "📦 Torrents: elige una opción", reply_markup=_menu_markup())

    @bot.callback_query_handler(func=lambda c: isinstance(c.data, str) and c.data.startswith("tr:"))
    def _cb_transmission(call):
        if not _is_admin(call):
            try:
                bot.answer_callback_query(call.id, "No autorizado", show_alert=True)
            except Exception:
                pass
            return

        try:
            bot.answer_callback_query(call.id)
        except Exception:
            pass

        data = call.data

        # ---- ADD ----
        if data == "tr:add":
            activity(call, "tr:add")
            _safe_send(bot, call.message.chat.id, "Envíame el magnet/link del torrent:")
            bot.register_next_step_handler(call.message, _step_add)
            return

        # ---- STATUS ----
        if data == "tr:status":
            activity(call, "tr:status")
            _handle_status(call.message.chat.id)
            return

        # ---- LIST ----
        if data.startswith("tr:list:"):
            activity(call, "tr:list")
            try:
                page = int(data.split(":")[2])
            except Exception:
                page = 0
            _handle_list(call.message.chat.id, page=page)
            return

        # ---- DELETE (menu) ----
        if data == "tr:delete":
            activity(call, "tr:delete")
            _handle_delete_menu(call.message.chat.id)
            return
        
        # ---- DELETE (pick -> confirm) ----
        if data.startswith("tr:pickdel:"):
            try:
                tid = int(data.split(":")[2])
            except Exception:
                _safe_send(bot, call.message.chat.id, "ID inválido.")
                return
            activity(call, f"tr:pickdel:{tid}")
            _handle_delete_confirm(call.message.chat.id, tid)
            return

        # ---- DELETE keep data ----
        if data.startswith("tr:delkeep:"):
            try:
                tid = int(data.split(":")[2])
            except Exception:
                _safe_send(bot, call.message.chat.id, "ID inválido.")
                return
            activity(call, f"tr:delkeep:{tid}")
            _handle_delete_id(call.message.chat.id, tid, delete_data=False)
            return

        # ---- DELETE with data ----
        if data.startswith("tr:deldata:"):
            try:
                tid = int(data.split(":")[2])
            except Exception:
                _safe_send(bot, call.message.chat.id, "ID inválido.")
                return
            activity(call, f"tr:deldata:{tid}")
            _handle_delete_id(call.message.chat.id, tid, delete_data=True)
            return


        # fallback
        _safe_send(bot, call.message.chat.id, "Acción desconocida.")

    def _step_add(message):
        if not _is_admin(message):
            bot.reply_to(message, "No autorizado.")
            return

        url = (message.text or "").strip()
        activity(message, "tr:add_step")

        if not url:
            bot.reply_to(message, "No recibí ningún enlace. Usa /torrents otra vez.")
            return

        try:
            tc = _get_client()
            t = tc.add_torrent(url)
            bot.reply_to(message, f"✅ Torrent agregado: {t.name}")
        except Exception as e:
            logging.exception("Error add_torrent")
            bot.reply_to(message, f"❌ Error al agregar torrent: {e}")

        _safe_send(bot, message.chat.id, "📦 Menú torrents:", reply_markup=_menu_markup())

    def _handle_status(chat_id: int):
        try:
            tc = _get_client()
            stats = tc.session_stats()
            # Campos típicos:
            down = getattr(stats, "downloadSpeed", None)
            up = getattr(stats, "uploadSpeed", None)
            active = getattr(stats, "activeTorrentCount", None)
            paused = getattr(stats, "pausedTorrentCount", None)
            total = getattr(stats, "torrentCount", None)

            msg = (
                "📊 Transmission\n"
                f"- Torrents: {total} (activos {active}, pausados {paused})\n"
                f"- Velocidad: DL {_fmt_rate(down)} | UL {_fmt_rate(up)}\n"
            )
            _safe_send(bot, chat_id, msg, reply_markup=_menu_markup())
        except Exception as e:
            logging.exception("Error status")
            _safe_send(bot, chat_id, f"❌ Error al obtener estado: {e}", reply_markup=_menu_markup())

    def _handle_list(chat_id: int, page: int = 0, page_size: int = 10):
        try:
            tc = _get_client()
            torrents = tc.get_torrents()
            if not torrents:
                _safe_send(bot, chat_id, "No hay torrents en cola.", reply_markup=_menu_markup())
                return

            start = max(0, page * page_size)
            end = min(len(torrents), start + page_size)
            chunk = torrents[start:end]

            lines = ["📋 Lista de torrents (ID | % | DL/UL | ETA | nombre)"]
            for t in chunk:
                lines.append(_fmt_torrent_line(t))

            nav = InlineKeyboardMarkup(row_width=3)
            prev_btn = InlineKeyboardButton("⬅️", callback_data=f"tr:list:{max(0, page-1)}")
            next_btn = InlineKeyboardButton("➡️", callback_data=f"tr:list:{page+1}")
            menu_btn = InlineKeyboardButton("🏠 Menú", callback_data="tr:status")

            # Solo mostrar next si hay más
            btns = []
            if page > 0:
                btns.append(prev_btn)
            if end < len(torrents):
                btns.append(next_btn)
            btns.append(menu_btn)
            nav.add(*btns)

            _safe_send(bot, chat_id, "\n".join(lines), reply_markup=nav)
        except Exception as e:
            logging.exception("Error list")
            _safe_send(bot, chat_id, f"❌ Error al listar torrents: {e}", reply_markup=_menu_markup())

    def _handle_delete_menu(chat_id: int):
        try:
            tc = _get_client()
            torrents = tc.get_torrents()
            if not torrents:
                _safe_send(bot, chat_id, "No hay torrents para eliminar.", reply_markup=_menu_markup())
                return

            markup = InlineKeyboardMarkup(row_width=1)

            # Mostramos hasta 8 para no saturar; el resto usa /list para ver IDs
            for t in torrents[:8]:
                tid = getattr(t, "id", None)
                name = getattr(t, "name", "torrent")
                label = f"🗑️ {tid} - {(name[:35] + '…') if len(name) > 36 else name}"
                markup.add(InlineKeyboardButton(label, callback_data=f"tr:pickdel:{tid}"))

            _safe_send(
                bot,
                chat_id,
                "Selecciona un torrent para eliminar (si no aparece, usa 📋 Listar para ver el ID):",
                reply_markup=markup,
            )
        except Exception as e:
            logging.exception("Error delete menu")
            _safe_send(bot, chat_id, f"❌ Error mostrando menú eliminar: {e}", reply_markup=_menu_markup())

    def _handle_delete_id(chat_id: int, tid: int, delete_data: bool):
        try:
            tc = _get_client()
            tc.remove_torrent(tid, delete_data=delete_data)
            if delete_data:
                _safe_send(bot, chat_id, f"✅ Torrent {tid} eliminado + datos borrados.", reply_markup=_menu_markup())
            else:
                _safe_send(bot, chat_id, f"✅ Torrent {tid} eliminado (archivos conservados).", reply_markup=_menu_markup())
        except Exception as e:
            logging.exception("Error delete id")
            _safe_send(bot, chat_id, f"❌ Error al eliminar torrent {tid}: {e}", reply_markup=_menu_markup())

            
    def _handle_delete_confirm(chat_id: int, tid: int):
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("✅ Solo torrent", callback_data=f"tr:delkeep:{tid}"),
            InlineKeyboardButton("🧨 Torrent + datos", callback_data=f"tr:deldata:{tid}"),
        )
        markup.add(
            InlineKeyboardButton("↩️ Cancelar", callback_data="tr:delete"),
            InlineKeyboardButton("🏠 Menú", callback_data="tr:status"),
        )
        _safe_send(
            bot,
            chat_id,
            f"¿Cómo quieres eliminar el torrent ID {tid}?\n\n"
            "✅ Solo torrent: lo quita de la lista, mantiene archivos.\n"
            "🧨 Torrent + datos: borra también lo descargado en disco.",
            reply_markup=markup,
        )


def get_oled_torrent_status(cache_seconds: int = 5) -> Optional[dict]:
    """
    Devuelve un resumen pequeño para OLED.
    - Usa cache para no consultar Transmission en cada refresh.
    - Retorna None si no hay actividad o Transmission no está disponible.
    """
    global _last_oled, _last_oled_ts

    now = time.time()

    # 1) Si tenemos cache reciente, devolverlo
    if (now - _last_oled_ts) < cache_seconds:
        return _last_oled

    # 2) Si no hay cache reciente, consultamos Transmission
    try:
        tc = _get_client()
        torrents = tc.get_torrents()
        if not torrents:
            _last_oled = None
            _last_oled_ts = now
            return None

        # "activos": descargando o subiendo
        active = [t for t in torrents if getattr(t, "status", "") in ("downloading", "seeding")]
        if not active:
            _last_oled = None
            _last_oled_ts = now
            return None

        # elegir el "principal" para mostrar (prioriza downloading)
        active.sort(
            key=lambda t: (
                0 if getattr(t, "status", "") == "downloading" else 1,
                -float(getattr(t, "progress", 0) or 0),
            )
        )
        t = active[0]

        name = getattr(t, "name", "torrent")

        progress = getattr(t, "progress", None)
        if progress is None:
            pd = getattr(t, "percent_done", None)
            progress = int(pd * 100) if isinstance(pd, (int, float)) else 0

        rate_dl = int(getattr(t, "rateDownload", 0) or 0)
        rate_ul = int(getattr(t, "rateUpload", 0) or 0)

        result = {
            "count": len(active),
            "name": name,
            "progress": int(progress),
            "dl": rate_dl,
            "ul": rate_ul,
            "status": getattr(t, "status", ""),
        }

        # 3) Guardar cache
        _last_oled = result
        _last_oled_ts = now
        return result

    except Exception:
        # si falla, cacheamos "None" para no spamear errores cada 2s
        _last_oled = None
        _last_oled_ts = now
        return None
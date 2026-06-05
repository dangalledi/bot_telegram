import os
import logging
import requests
import telebot

HA_URL   = os.getenv("HA_URL", "http://localhost:8123")
HA_TOKEN = os.getenv("HA_TOKEN")

# Entity ID de la automatización en Home Assistant
ROUTER_AUTOMATION_ID = os.getenv("HA_ROUTER_AUTOMATION", "automation.reboot_router")


# ---------------------------------------------------------------------------
# Cliente HA
# ---------------------------------------------------------------------------

def _ha_headers() -> dict:
    return {
        "Authorization": f"Bearer {HA_TOKEN}",
        "Content-Type":  "application/json",
    }


def ha_run_automation(automation_id: str) -> bool:
    """Dispara una automatización de HA por su entity_id."""
    try:
        r = requests.post(
            f"{HA_URL}/api/services/automation/trigger",
            headers=_ha_headers(),
            json={"entity_id": automation_id},
            timeout=5,
        )
        return r.status_code == 200
    except Exception as e:
        logging.error("ha_run_automation error: %s", e)
        return False


def ha_get_state(entity_id: str) -> str | None:
    """Devuelve el estado actual de una entidad ('on', 'off', ...) o None si falla."""
    try:
        r = requests.get(
            f"{HA_URL}/api/states/{entity_id}",
            headers=_ha_headers(),
            timeout=5,
        )
        if r.status_code == 200:
            return r.json().get("state")
    except Exception as e:
        logging.error("ha_get_state error: %s", e)
    return None


# ---------------------------------------------------------------------------
# Handlers del bot
# ---------------------------------------------------------------------------

def register_ha_handlers(bot: telebot.TeleBot, admin_ids: list[int]):

    @bot.message_handler(commands=["reboot_router", "router"])
    def handle_reboot_router(message):
        if message.from_user.id not in admin_ids:
            bot.reply_to(message, "No tienes permiso para reiniciar el router.")
            return

        state = ha_get_state(ROUTER_AUTOMATION_ID.replace("automation.", "switch."))
        state_txt = ""
        if state:
            state_txt = f"\nEstado actual del router: {state}"

        markup = telebot.types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            telebot.types.InlineKeyboardButton("Si, reiniciar", callback_data="router:confirm"),
            telebot.types.InlineKeyboardButton("Cancelar",      callback_data="router:cancel"),
        )
        bot.reply_to(
            message,
            f"Vas a reiniciar el router.\n"
            f"Se apagara y volvera solo automaticamente.{state_txt}\n\n"
            f"Confirmas?",
            reply_markup=markup,
        )

    @bot.callback_query_handler(func=lambda c: c.data in ("router:confirm", "router:cancel"))
    def handle_router_callback(call):
        try:
            bot.answer_callback_query(call.id)
        except Exception:
            pass

        if call.from_user.id not in admin_ids:
            bot.send_message(call.message.chat.id, "No autorizado.")
            return

        if call.data == "router:cancel":
            bot.send_message(call.message.chat.id, "Reinicio del router cancelado.")
            return

        logging.warning(
            "action user=%s cmd=reboot_router CONFIRMED",
            call.from_user.username or call.from_user.id,
        )

        ok = ha_run_automation(ROUTER_AUTOMATION_ID)

        if ok:
            for admin_id in admin_ids:
                if admin_id != call.from_user.id:
                    bot.send_message(
                        admin_id,
                        f"[HA] @{call.from_user.username or call.from_user.id} reinicio el router.",
                    )
            bot.send_message(call.message.chat.id, "Reiniciando router... vuelve solo en unos segundos.")
        else:
            bot.send_message(call.message.chat.id, "Error contactando Home Assistant. Esta encendido?")
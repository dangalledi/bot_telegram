# handlers/admin_handler.py

from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from oled_display import actualizar_pantalla
from logger import log_action
import logging

def admin(bot, message, ADMIN_IDS):
    username = message.from_user.username or str(message.from_user.id)
    if message.from_user.id in ADMIN_IDS:
        log_action(username, "/admin", "acceso OK")
        bot.send_message(message.chat.id, "Elige un comando para ejecutar:", reply_markup=gen_markup_admin())
        actualizar_pantalla("Acceso admin")
    else:
        logging.warning("action user=%s cmd=/admin DENIED (not admin)", username)
        bot.reply_to(message, f"Oye {username}, tú no eres admin! ¬¬")
        actualizar_pantalla("Acceso denegado")

def gen_markup_admin():
    markup = InlineKeyboardMarkup(row_width=3)
    markup.add(
        InlineKeyboardButton("reiniciar", callback_data="reiniciar"),
        InlineKeyboardButton("red_conectada", callback_data="red_conectada"),
        InlineKeyboardButton("ip", callback_data="ip"),
        InlineKeyboardButton("status", callback_data="status"),
        InlineKeyboardButton("pwd", callback_data="pwd"),
        InlineKeyboardButton("ls", callback_data="ls")
    )
    return markup
# handlers/admin_handler.py

from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from oled_display import actualizar_pantalla
from logger import setup_logging
import os

def admin(bot, message):
    username = message.from_user.username
    setup_logging(username, '/admin')  # Registrar la acción
    print(f"admin -> El mensaje fue enviado por el usuario con nombre de usuario: {username}")
    print(f"User ID: {message.from_user.id}, Admin ID: {os.getenv('ADMIN_ID')}")  # Depuración para verificar IDs
    if message.from_user.id == os.getenv('ADMIN_ID'):
        bot.send_message(message.chat.id, "Elige un comando para ejecutar:", reply_markup=gen_markup_admin())
        actualizar_pantalla("Acceso admin")
    else:
        mensaje = (f"Oye {username} tu no eres admin ! ¬¬")
        bot.reply_to(message, mensaje)
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
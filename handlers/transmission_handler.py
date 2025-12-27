# Conexión al servidor Transmission
import transmission_rpc
import os
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# Conexión al servidor Transmission
tc = transmission_rpc.Client(
    host='localhost',  # Cambia por la dirección IP de tu Raspberry Pi si es necesario
    port=9091,  # Puerto por defecto del RPC de Transmission
    username=os.getenv('TRANSMISSION_USER'),
    password=os.getenv('TRANSMISSION_PASSWORD'),
)

# Función para mostrar el menú principal de torrents
def mostrar_menu_torrents(bot, message):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("Agregar Torrent", callback_data="agregar_torrent"),
        InlineKeyboardButton("Ver Estado Descargas", callback_data="estado_descargas"),
        InlineKeyboardButton("Listar Torrents", callback_data="listar_torrents"),
        InlineKeyboardButton("Eliminar Torrent", callback_data="eliminar_torrent")
    )
    bot.send_message(message.chat.id, "Elige una opción:", reply_markup=markup)

def agregar_torrent(url):
    try:
        torrent = tc.add_torrent(url)
        return f"Torrent agregado: {torrent.name}"
    except Exception as e:
        return f"Error al agregar torrent: {e}"

def estado_descargas():
    try:
        torrents = tc.get_torrents()
        if not torrents:
            return "No hay torrents en cola."
        else:
            respuesta = "Estado de las descargas:\n"
            for torrent in torrents:
                respuesta += (f"{torrent.name}: {torrent.progress}% descargado\n"
                              f"Tamaño total: {torrent.total_size / (1024 ** 2):.2f} MB\n"
                              f"Descargado: {torrent.have_valid / (1024 ** 2):.2f} MB\n\n")
            return respuesta
    except Exception as e:
        return f"Error al obtener estado de descargas: {e}"

def eliminar_torrent(torrent_id):
    try:
        tc.remove_torrent(torrent_id, delete_data=True)
        return f"Torrent {torrent_id} eliminado."
    except Exception as e:
        return f"Error al eliminar torrent: {e}"

def listar_torrents():
    try:
        torrents = tc.get_torrents()
        if not torrents:
            return "No hay torrents en cola."
        else:
            respuesta = "Lista de torrents:\n"
            for torrent in torrents:
                respuesta += f"ID: {torrent.id} - {torrent.name} ({torrent.progress}%)\n"
            return respuesta
    except Exception as e:
        return f"Error al listar torrents: {e}"
      
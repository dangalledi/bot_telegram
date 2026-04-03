# handlers/system_commands.py

from utils import llamadaSistema, obtener_ip
from oled_display import actualizar_pantalla
from logger import setup_logging 

def status(bot, message):
    try:
        print('status')
        cpu_usage = llamadaSistema("top -bn1 | grep 'Cpu(s)'")
        memory_usage = llamadaSistema("free -m")  # Obtiene la información de la memoria
        disk_usage = llamadaSistema("df -h")
        temp = llamadaSistema("vcgencmd measure_temp")
        
        # Extraer datos específicos de la memoria (Libre, Usada, Buffers)
        memoria_lineas = memory_usage.splitlines()
        memoria_header = memoria_lineas[0]
        memoria_datos = memoria_lineas[1].split()

        memoria_total = memoria_datos[1]
        memoria_usada = memoria_datos[2]
        memoria_libre = memoria_datos[3]
        memoria_buffers = memoria_datos[5]

        # Construir el mensaje de respuesta
        respuesta = (f"Uso de CPU:\n{cpu_usage}\n\n"
                     f"Uso de Memoria (en MB):\n"
                     f"Total: {memoria_total} MB\n"
                     f"Usada: {memoria_usada} MB\n"
                     f"Libre: {memoria_libre} MB\n"
                     f"Buffers/Cached: {memoria_buffers} MB\n\n"
                     f"Uso de Disco:\n{disk_usage}\n\n"
                     f"Temperatura de la CPU:\n{temp}")
        
        bot.reply_to(message, respuesta)
        actualizar_pantalla("Estado del sistema mostrado")
    except Exception as e:
        bot.reply_to(message, f"Error al obtener el estado del sistema: {str(e)}")
        setup_logging(message.from_user.username, '/status')
        actualizar_pantalla("Error en estado")

def ip(bot, message):
    ip_address = obtener_ip()
    bot.reply_to(message, ip_address)
    print('ip')
    setup_logging(message.from_user.username, '/ip')
    actualizar_pantalla(f"IP: {ip_address}")

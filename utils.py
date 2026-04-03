# utils.py

import os

def llamadaSistema(entrada):
    salida = ""  # Creamos variable vacía
    f = os.popen(entrada)  # Llamada al sistema
    for i in f.readlines():  # Leemos caracter a caracter sobre la línea devuelta por la llamada al sistema
        salida += i  # Insertamos cada uno de los caracteres en nuestra variable
    salida = salida[:-1]  # Truncamos el caracter fin de línea '\n'
    return salida  # Devolvemos la respuesta al comando ejecutado

def obtener_ip():
    return llamadaSistema("hostname -I").strip()

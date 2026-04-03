# oled_display.py
import time
import threading
import board
import busio
from adafruit_ssd1306 import SSD1306_I2C
from PIL import Image, ImageDraw, ImageFont

_auto_thread = None
_stop_event = threading.Event()
_LOCK = threading.Lock()
_LAST_RENDER = None
_LAST_TS = 0.0
_MIN_INTERVAL = 0.2  # no más de 5 fps

def _load_font(size: int):
    # Fuente del sistema (más fiable que Pillow/Tests)
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    return ImageFont.load_default()

FONT_HEADER = _load_font(12)
FONT_BODY = _load_font(11)

# Configurar OLED
i2c = busio.I2C(board.SCL, board.SDA)
oled = SSD1306_I2C(128, 64, i2c, addr=0x3c)

width = oled.width
height = oled.height
image = Image.new("1", (width, height))
draw = ImageDraw.Draw(image)

def _wrap_text(text: str, font, max_width: int):
    # Wrap simple por palabras
    words = text.split()
    lines = []
    line = ""
    for w in words:
        test = f"{line} {w}".strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] <= max_width:
            line = test
        else:
            if line:
                lines.append(line)
            line = w
    if line:
        lines.append(line)
    return lines

def render_status(
    title: str = "PatanaBot",
    line1: str = "",
    line2: str = "",
    line3: str = "",
    right: str = "",
):
    """
    Renderiza un layout fijo:
    [title            right]
    line1
    line2
    line3
    """
    global _LAST_RENDER, _LAST_TS

    now = time.time()
    if now - _LAST_TS < _MIN_INTERVAL:
        return  # throttle

    # Prepara contenido "canónico" para detectar cambios
    payload = (title, line1, line2, line3, right)
    if payload == _LAST_RENDER:
        return

    with _LOCK:
        try:
            draw.rectangle((0, 0, width, height), outline=0, fill=0)

            # Header
            draw.text((0, 0), title[:10], font=FONT_HEADER, fill=255)
            if right:
                bbox = draw.textbbox((0, 0), right, font=FONT_HEADER)
                rw = bbox[2] - bbox[0]
                draw.text((width - rw, 0), right, font=FONT_HEADER, fill=255)

            y = 16  # debajo del header

            # Body (3 líneas)
            body_lines = [line1, line2, line3]
            for text in body_lines:
                if not text:
                    y += 16
                    continue
                # wrap por si se pasa
                wrapped = _wrap_text(text, FONT_BODY, width)
                for wline in wrapped[:1]:  # 1 línea por bloque (compacto)
                    draw.text((0, y), wline, font=FONT_BODY, fill=255)
                    y += 16

            oled.image(image)
            oled.show()

            _LAST_RENDER = payload
            _LAST_TS = now

        except Exception:
            # Si OLED falla, no queremos tumbar el bot.
            # Aquí podrías hacer logging.exception(...) si ya tienes logging configurado.
            pass

# Compatibilidad: tu bot usa actualizar_pantalla(texto)
def actualizar_pantalla(texto: str):
    # Lo muestra como línea central simple (pero usando render estable)
    render_status(title="PatanaBot", line2=texto, right=time.strftime("%H:%M"))

def start_auto_update(get_payload_fn, interval=2):
    """
    get_payload_fn() debe devolver un dict con:
      {
        "title": str,
        "right": str,
        "line1": str,
        "line2": str,
        "line3": str
      }
    """
    global _auto_thread
    if _auto_thread and _auto_thread.is_alive():
        return

    _stop_event.clear()

    def _loop():
        while not _stop_event.is_set():
            try:
                p = get_payload_fn() or {}
                # Si tienes render_status (recomendado)
                render_status(
                    title=p.get("title", "PatanaBot"),
                    right=p.get("right", time.strftime("%H:%M")),
                    line1=p.get("line1", ""),
                    line2=p.get("line2", ""),
                    line3=p.get("line3", ""),
                )
                # Si NO tienes render_status, usa actualizar_pantalla(p.get("line2",""))
            except Exception:
                pass
            time.sleep(interval)

    _auto_thread = threading.Thread(target=_loop, daemon=True)
    _auto_thread.start()

def stop_auto_update():
    _stop_event.set()
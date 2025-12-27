# Bot de Telegram con Pantalla OLED (Raspberry Pi)

Bot de Telegram en Python para administrar una Raspberry Pi y mostrar información en una pantalla OLED (SSD1306 vía I2C).  
Incluye comandos básicos, comandos de sistema, control de Minecraft (Docker) y gestión de torrents.

---

## Características

- Bot de Telegram (pyTelegramBotAPI)
- Pantalla OLED SSD1306 (I2C)
- Comandos de administración y sistema: IP, status, etc.
- Menú interactivo con botones (InlineKeyboard)
- Logs:
  - **Archivo con rotación diaria** en `./log/bot.log`
  - **Journal (systemd)** para ver logs en vivo y errores de arranque
- Ejecución estable en producción con **systemd** (reinicios automáticos)

---

## Requisitos

### Hardware
- Raspberry Pi (compatible con I2C)
- Pantalla OLED SSD1306 (típicamente `0x3c`)
- Conexión I2C: SDA/SCL + GND + VCC

### Software
- Raspberry Pi OS / Debian-based
- Python 3
- Entorno virtual (venv)
- Paquetes: `pyTelegramBotAPI`, `Pillow`, `adafruit-circuitpython-ssd1306` (o el driver que uses)

---

## Instalación

### 1) Clonar repositorio
```bash
git clone https://github.com/tu-usuario/bot_telegram.git
cd bot_telegram
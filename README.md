# PatanaBot — Bot de Telegram para Raspberry Pi

Bot de Telegram en Python para administrar una Raspberry Pi y mostrar información en una pantalla OLED (SSD1306 vía I2C).  
Incluye comandos de sistema, control de Minecraft (Docker), gestión de torrents y control de servicios (Plex, ZeroTier).

---

## Características

- Bot de Telegram (pyTelegramBotAPI) con menús interactivos (InlineKeyboard)
- Pantalla OLED SSD1306 (I2C) con rotación automática de pantallas
- Alertas automáticas al admin por temperatura y RAM
- Control de servicios systemd: Plex, ZeroTier
- Gestión de servidor Minecraft vía Docker
- Gestión de torrents vía Transmission
- Logs con rotación diaria (`log/bot.log`) y salida a journald

---

## Requisitos

### Hardware
- Raspberry Pi (compatible con I2C)
- Pantalla OLED SSD1306 (típicamente dirección `0x3c`)
- Conexión I2C: SDA/SCL + GND + VCC

### Software
- Raspberry Pi OS / Debian-based
- Python 3.11+
- `pyTelegramBotAPI`, `Pillow`, `transmission-rpc`, `adafruit-circuitpython-ssd1306`

---

## Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/tu-usuario/bot_telegram.git
cd bot_telegram
```

### 2. Crear entorno virtual e instalar dependencias

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Dependencias del sistema

```bash
sudo apt-get update
sudo apt-get install python3-dev python3-smbus i2c-tools
```

### 4. Habilitar I2C

```bash
sudo raspi-config
# Interfacing Options > I2C > Enable
```

Verificar que la pantalla esté detectada:

```bash
sudo i2cdetect -y 1
# Debe aparecer 0x3c
```

### 5. Configurar variables de entorno

Copia `.env.example` a `.env` y rellena los valores:

```bash
cp .env.example .env
```

| Variable | Descripción | Por defecto |
|---|---|---|
| `TOKEN` | Token del bot (BotFather) | — |
| `ADMIN_IDS` | IDs de admin separados por coma | `0` |
| `TRANSMISSION_HOST` | Host de Transmission | `localhost` |
| `TRANSMISSION_PORT` | Puerto de Transmission | `9091` |
| `TRANSMISSION_USER` | Usuario de Transmission | — |
| `TRANSMISSION_PASSWORD` | Contraseña de Transmission | — |
| `MC_CONTAINER` | Nombre del contenedor Docker de Minecraft | `minecraft` |
| `MC_COMPOSE_FILE` | Ruta al `docker-compose.yml` de Minecraft | — |
| `ALERT_TEMP_C` | Temperatura (°C) que dispara alerta al admin | `70` |
| `ALERT_RAM_PCT` | % de RAM que dispara alerta al admin | `85` |
| `ALERT_COOLDOWN_S` | Segundos mínimos entre alertas repetidas | `1800` |

### 6. Ejecutar en desarrollo

```bash
source venv/bin/activate
python3 bot.py
```

---

## Despliegue con systemd

```ini
# /etc/systemd/system/bot_telegram.service
[Unit]
Description=PatanaBot Telegram
After=network.target

[Service]
User=pi
WorkingDirectory=/home/pi/code/bot_telegram
EnvironmentFile=/home/pi/code/bot_telegram/.env
ExecStart=/home/pi/code/bot_telegram/venv/bin/python bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable bot_telegram
sudo systemctl start bot_telegram
```

---

## Comandos

### Generales (cualquier usuario)

| Comando | Descripción |
|---|---|
| `/start`, `/inicio` | Mensaje de bienvenida e instrucciones |
| `/ping` | Comprueba que el bot está vivo |
| `/fecha` | Fecha y hora del sistema |
| `/comandos` | Lista de comandos disponibles |
| `/status` | CPU, RAM, disco y temperatura |
| `/ip` | IP local de la Raspberry |

### Servicios (solo admins para on/off)

| Comando | Descripción |
|---|---|
| `/plex` | Estado del servicio Plex Media Server |
| `/plex on` | Arranca Plex |
| `/plex off` | Para Plex |
| `/zerotier` | Estado del servicio ZeroTier |
| `/zerotier on` | Arranca ZeroTier |
| `/zerotier off` | Para ZeroTier |

### Minecraft

| Comando | Descripción |
|---|---|
| `/minecraft`, `/mc` | Panel interactivo: arrancar, parar, ver estado |
| `/mc_online`, `/online` | Jugadores conectados en este momento |
| `/mc_last`, `/last` | Última actividad registrada |

### Torrents

| Comando | Descripción |
|---|---|
| `/torrents` | Menú de Transmission: listar, agregar, eliminar y ver estado |

### Solo admins

| Comando | Descripción |
|---|---|
| `/admin` | Panel de administración |
| `/apagar` | Apaga la Raspberry Pi |

---

## Estructura del proyecto

```
bot_telegram/
├── bot.py                        # Punto de entrada, registro de handlers
├── logger.py                     # Logging a archivo (log/bot.log) y stdout
├── utils.py                      # Helpers: llamadaSistema, obtener_ip
├── oled_display.py               # Control de pantalla OLED
├── handlers/
│   ├── basic_commands.py         # start, ping, fecha, comandos
│   ├── system_commands.py        # status, ip
│   ├── admin_handler.py          # admin
│   ├── services_handler.py       # plex, zerotier
│   ├── minecraft_handler.py      # minecraft, mc_online, mc_last
│   └── transmission_handler.py  # torrents
└── log/                          # Rotación diaria, 14 días de histórico (ignorado en git)
```

---

## Logs

```bash
# En tiempo real via journald
journalctl -u bot_telegram -f

# Archivo de log
tail -f /home/pi/code/bot_telegram/log/bot.log
```

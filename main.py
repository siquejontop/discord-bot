import discord
from discord.ext import commands
import asyncio
import logging
import colorlog
import pyfiglet
import os
from flask import Flask
from threading import Thread

# ==========================
# 🔑 TOKEN
# ==========================
TOKEN = os.getenv("DISCORD_TOKEN")

# ==========================
# 🌐 KEEP ALIVE
# ==========================
app = Flask('')

@app.route('/')
def home():
    return "✅ Bot online y funcionando!"

@app.route('/healthz')
def health():
    return "OK", 200

def run_flask():
    port = int(os.environ.get("PORT", 8080))  # Usa puerto dinámico de Render
    app.run(host="0.0.0.0", port=port)

def keep_alive():
    t = Thread(target=run_flask)
    t.start()

# ==========================
# 🎨 CONFIG LOGGING
# ==========================
log_colors = {
    'DEBUG': 'cyan',
    'INFO': 'green',
    'WARNING': 'yellow',
    'ERROR': 'red',
    'CRITICAL': 'bold_red',
}

formatter = colorlog.ColoredFormatter(
    "%(log_color)s%(asctime)s [%(levelname)s] %(message)s",
    log_colors=log_colors
)

logger = logging.getLogger("discord_bot")
logger.setLevel(logging.INFO)

file_handler = logging.FileHandler("bot.log", encoding="utf-8")
file_formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
file_handler.setFormatter(file_formatter)

console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)

if not logger.hasHandlers():
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
else:
    logger.handlers.clear()
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

# ==========================
# 🤖 BOT CLASS
# ==========================
intents = discord.Intents.all()

class MyBot(commands.Bot):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.ready_once = False

    async def setup_hook(self):
        from cogs.hits import HitsButtonsES, HitsButtonsEN
        if not hasattr(self, "views_loaded"):
            self.add_view(HitsButtonsES(self))
            self.add_view(HitsButtonsEN(self))
            self.views_loaded = True
            logger.info("🎛️ Views registradas correctamente")

        cogs = [
            "cogs.events",
            "cogs.moderation",
            "cogs.fun",
            "cogs.hits",
            "cogs.logs",
            "cogs.snipe",
            "cogs.translate",
            "cogs.utils",
            "cogs.afk",
            "cogs.howto",
            "cogs.admin",
            "cogs.backup",
            "cogs.roles",
            "cogs.brainrotcalc",
            "cogs.antinuke",
            "cogs.autobanalts",
        ]

        for cog in cogs:
            if cog not in self.extensions:
                try:
                    await self.load_extension(cog)
                    logger.info(f"✅ Cog cargado: {cog}")
                except Exception as e:
                    logger.error(f"❌ Error cargando {cog}: {e}")

bot = MyBot(command_prefix=",", intents=intents)

# ==========================
# 📡 BOT EVENTS
# ==========================
@bot.event
async def on_connect():
    logger.info("🔌 Conectando al cliente de Discord...")

@bot.event
async def on_ready():
    if bot.ready_once:
        return
    bot.ready_once = True

    banner = pyfiglet.figlet_format("MY BOT")
    print(f"\n{banner}")
    logger.info(f"✅ Bot conectado como {bot.user} (ID: {bot.user.id})")

# ==========================
# 📡 ERROR HANDLER GLOBAL
# ==========================
@bot.event
async def on_command_error(ctx, error):
    # Ignorar errores que ya tengan handler local
    if hasattr(ctx.command, 'on_error'):
        return

    # Diccionario de errores comunes
    error_messages = {
        commands.MissingPermissions: "You're **missing** permission: `{}`",
        commands.BotMissingPermissions: "I'm **missing** permission: `{}`",
        commands.MissingRequiredArgument: "Te faltó el argumento requerido: `{}`",
        commands.BadArgument: "El argumento que diste no es válido.",
        commands.CommandNotFound: "Ese comando no existe.",
        commands.NotOwner: "Este comando es solo para dueños del bot.",
        commands.CommandOnCooldown: "Este comando está en cooldown. Intenta de nuevo en `{}` segundos.",
    }

    # Buscar error específico
    msg = None
    for err_type, text in error_messages.items():
        if isinstance(error, err_type):
            if isinstance(error, commands.MissingPermissions) or isinstance(error, commands.BotMissingPermissions):
                missing = ", ".join(error.missing_permissions)
                msg = text.format(missing)
            elif isinstance(error, commands.MissingRequiredArgument):
                msg = text.format(error.param.name)
            elif isinstance(error, commands.CommandOnCooldown):
                msg = text.format(round(error.retry_after, 2))
            else:
                msg = text
            break

    # Fallback si no está en el diccionario
    if not msg:
        msg = f"Ocurrió un error inesperado: `{error}`"

    # Responder con el mismo estilo pequeño ⚠️
    embed = discord.Embed(
        description=f"⚠️ {ctx.author.mention}: {msg}",
        color=discord.Color.orange()
    )
    await ctx.send(embed=embed)
    
# Iniciar Flask en un hilo separado
keep_alive()

# Iniciar el bot
bot.run(TOKEN)

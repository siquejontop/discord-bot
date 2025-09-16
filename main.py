import discord
from discord.ext import commands
import asyncio
import logging
import colorlog
import pyfiglet
import os
TOKEN = os.getenv("DISCORD_TOKEN")


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

# Evitar handlers duplicados
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
    async def setup_hook(self):
        # Registro de views persistentes (SOLO UNA VEZ)
        from cogs.hits import HitsButtonsES, HitsButtonsEN
        if not hasattr(self, "views_loaded"):
            self.add_view(HitsButtonsES(self))
            self.add_view(HitsButtonsEN(self))
            self.views_loaded = True
            logger.info("🎛️ Views registradas correctamente")

        # Carga de cogs con logs bonitos
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
        ]

        for cog in cogs:
            if cog not in self.extensions:  # 👈 evita recargar duplicado
                try:
                    await self.load_extension(cog)
                    logger.info(f"✅ Cog cargado: {cog}")
                except Exception as e:
                    logger.error(f"❌ Error cargando {cog}: {e}")

bot = MyBot(command_prefix="$", intents=intents)

# ==========================
# 📡 BOT EVENTS
# ==========================
@bot.event
async def on_connect():
    logger.info("🔌 Conectando al cliente de Discord...")

@bot.event
async def on_ready():
    banner = pyfiglet.figlet_format("MY BOT")  # 🔥 cambia "MY BOT"
    print(f"\n{banner}")
    logger.info(f"✅ Bot conectado como {bot.user} (ID: {bot.user.id})")
    logger.info(f"🌍 Conectado a {len(bot.guilds)} servidores")
    logger.info("⚡ Listo para recibir comandos!")

@bot.event
async def on_guild_join(guild):
    logger.info(f"🟢 El bot se unió al servidor: {guild.name} (ID: {guild.id})")

@bot.event
async def on_guild_remove(guild):
    logger.warning(f"🔴 El bot fue expulsado de: {guild.name} (ID: {guild.id})")

# ==========================
# 🚀 MAIN
# ==========================
async def main():
    async with bot:
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())

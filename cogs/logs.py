# cogs/logs.py
import logging
import logging.handlers
import os
from datetime import datetime, timezone
import traceback

import discord
from discord.ext import commands

# Intentional optional import for pretty console colors
try:
    import colorlog  # prettier colored output (pip install colorlog)
    HAS_COLORLOG = True
except Exception:
    HAS_COLORLOG = False

# Optional config import: si tienes un config.py con LOG_CHANNEL_ID lo usará
try:
    import config
    CONFIG = config
except Exception:
    CONFIG = None

# Ajustes
LOG_DIR = "logs"
LOG_FILENAME = "bot.log"
MAX_BYTES = 5 * 1024 * 1024  # 5 MB por archivo
BACKUP_COUNT = 5
CONSOLE_LEVEL = logging.INFO
FILE_LEVEL = logging.DEBUG
LOGGER_NAME = "unban_bot"  # nombre del logger usado por el cog

# Asegurar carpeta de logs
os.makedirs(LOG_DIR, exist_ok=True)
log_path = os.path.join(LOG_DIR, LOG_FILENAME)


def setup_root_logger():
    """
    Configura el logger raíz con handler a fichero y handler a consola.
    Devuelve el logger configurado.
    """
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.DEBUG)

    # --- File handler (rotating) ---
    fh = logging.handlers.RotatingFileHandler(
        log_path, maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT, encoding="utf-8"
    )
    fh.setLevel(FILE_LEVEL)
    file_fmt = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    fh.setFormatter(file_fmt)
    logger.addHandler(fh)

    # --- Console handler (colored if possible) ---
    ch = logging.StreamHandler()
    ch.setLevel(CONSOLE_LEVEL)
    if HAS_COLORLOG:
        # colorlog requires a different format string with %(log_color)s
        log_colors = {
            "DEBUG": "reset",
            "INFO": "cyan",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "bold_red",
        }
        formatter = colorlog.ColoredFormatter(
            "%(log_color)s%(asctime)s%(reset)s [%(log_color)s%(levelname)s%(reset)s] "
            "%(log_color)s%(message)s%(reset)s",
            datefmt="%H:%M:%S",
            log_colors=log_colors,
        )
    else:
        formatter = logging.Formatter(fmt="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    # Prevent duplicate handlers if invoked multiple times
    logger.propagate = False

    return logger


logger = setup_root_logger()


class Logs(commands.Cog):
    """Cog para logging: consola + fichero + envíos a canal de logs en cada guild."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logger = logging.getLogger(LOGGER_NAME)
        self.logger.debug("Logs cog inicializado.")

    # ----------------------------
    # Utilidades internas
    # ----------------------------
    def _find_log_channel(self, guild: discord.Guild) -> discord.TextChannel | None:
        """
        Devuelve el canal de logs preferido:
         - Si config.LOG_CHANNEL_ID existe y pertenece al guild -> se usa.
         - Sino busca por nombre común: 'logs','log','mod-log','bot-logs'
         - Sino None
        """
        # 1) config override global (si existe)
        if CONFIG and hasattr(CONFIG, "LOG_CHANNEL_ID"):
            try:
                ch = guild.get_channel(getattr(CONFIG, "LOG_CHANNEL_ID"))
                if ch:
                    return ch
            except Exception:
                pass

        # 2) buscar por nombre
        candidates = ["logs", "log", "mod-log", "bot-logs", "bot-logs📜", "moderation"]
        for name in candidates:
            for ch in guild.text_channels:
                if ch.name and ch.name.lower() == name:
                    return ch

        # 3) devolver None si no encuentra
        return None

    def _make_embed(self, title: str, description: str, color: discord.Color = discord.Color.blurple()):
        return discord.Embed(title=title, description=description, color=color, timestamp=datetime.now(timezone.utc))

    async def _safe_send(self, channel: discord.TextChannel, embed: discord.Embed):
        """Enviar embed ignorando errores por permisos/limites."""
        try:
            await channel.send(embed=embed)
        except Exception as exc:
            # registrar a fichero/console que falló el envío al canal
            self.logger.warning(f"No se pudo enviar embed a {channel.guild}/{channel.name}: {exc}")

    # ----------------------------
    # EVENTOS
    # ----------------------------
    @commands.Cog.listener()
    async def on_ready(self):
        # Mensajes por consola y fichero
        self.logger.info(f"Bot conectado: {self.bot.user} (ID: {self.bot.user.id})")
        # Enviar embed a los canales de logs de cada guild (opcional)
        for guild in self.bot.guilds:
            ch = self._find_log_channel(guild)
            if ch:
                embed = self._make_embed(
                    title="🤖 Bot en línea",
                    description=f"El bot **{self.bot.user}** se ha conectado.\nGuild: **{guild.name}** ({guild.id})",
                    color=discord.Color.green()
                )
                # No await directo en loop de inicio (evitar bloqueos): crear tarea
                try:
                    self.bot.loop.create_task(self._safe_send(ch, embed))
                except Exception:
                    self.logger.exception("Error creando tarea para enviar embed on_ready")

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        self.logger.info(f"Entré a guild: {guild.name} ({guild.id}) — miembros: {guild.member_count}")
        ch = self._find_log_channel(guild)
        if ch:
            embed = self._make_embed(
                title="➕ Bot añadido al servidor",
                description=f"Me han añadido a **{guild.name}**\nMiembros: **{guild.member_count}**",
                color=discord.Color.blue()
            )
            await self._safe_send(ch, embed)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        self.logger.info(f"Salí de guild: {guild.name} ({guild.id})")

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        self.logger.info(f"Member join: {member} ({member.id}) in {member.guild.name}")
        ch = self._find_log_channel(member.guild)
        if ch:
            embed = self._make_embed(
                title="✅ Usuario unido",
                description=f"{member.mention} se unió\nID: `{member.id}`",
                color=discord.Color.green()
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            await self._safe_send(ch, embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        self.logger.info(f"Member left: {member} ({member.id}) from {member.guild.name}")
        ch = self._find_log_channel(member.guild)
        if ch:
            embed = self._make_embed(
                title="❌ Usuario salió",
                description=f"{member} salió del servidor.\nID: `{member.id}`",
                color=discord.Color.red()
            )
            await self._safe_send(ch, embed)

    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        self.logger.warning(f"Usuario baneado: {user} en {guild.name}")
        ch = self._find_log_channel(guild)
        if ch:
            embed = self._make_embed(
                title="🚫 Usuario baneado",
                description=f"{user} fue baneado del servidor.",
                color=discord.Color.dark_red()
            )
            await self._safe_send(ch, embed)

    @commands.Cog.listener()
    async def on_member_unban(self, guild, user):
        self.logger.info(f"Usuario desbaneado: {user} en {guild.name}")
        ch = self._find_log_channel(guild)
        if ch:
            embed = self._make_embed(
                title="✅ Usuario desbaneado",
                description=f"{user} fue desbaneado del servidor.",
                color=discord.Color.green()
            )
            await self._safe_send(ch, embed)

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        # ignora bots para evitar ruido
        if message.author and message.author.bot:
            return
        guild = message.guild
        if not guild:
            return
        self.logger.info(f"Mensaje borrado por {message.author} en #{message.channel}: {message.content!r}")
        ch = self._find_log_channel(guild)
        if ch:
            description = (
                f"**Autor:** {message.author} (`{message.author.id}`)\n"
                f"**Canal:** {message.channel.mention}\n"
                f"**Contenido:**\n{message.content or '*[embed/archivo]*'}"
            )
            embed = self._make_embed(title="🗑️ Mensaje eliminado", description=description, color=discord.Color.orange())
            await self._safe_send(ch, embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if before.author and before.author.bot:
            return
        if before.content == after.content:
            return
        guild = before.guild
        if not guild:
            return
        self.logger.info(f"Mensaje editado por {before.author} en #{before.channel}: {before.content!r} -> {after.content!r}")
        ch = self._find_log_channel(guild)
        if ch:
            description = (
                f"**Autor:** {before.author} (`{before.author.id}`)\n"
                f"**Canal:** {before.channel.mention}\n\n"
                f"**Antes:**\n{before.content or '*Vacío*'}\n\n"
                f"**Después:**\n{after.content or '*Vacío*'}"
            )
            embed = self._make_embed(title="✏️ Mensaje editado", description=description, color=discord.Color.yellow())
            embed.add_field(name="Link", value=after.jump_url, inline=False)
            await self._safe_send(ch, embed)

    # ----------------------------
    # Comandos (registro de uso y errores)
    # ----------------------------
    @commands.Cog.listener()
    async def on_command(self, ctx):
        # Se dispara antes de la ejecución del comando
        self.logger.info(f"CMD: {ctx.author} ({ctx.author.id}) -> {ctx.command} in {ctx.guild}/{ctx.channel}")

    @commands.Cog.listener()
    async def on_command_completion(self, ctx):
        self.logger.info(f"CMD OK: {ctx.command} by {ctx.author} in {ctx.guild}/{ctx.channel}")

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        # Loguea error y manda un embed informando (no muestra stacktrace al usuario)
        err_text = "".join(traceback.format_exception(type(error), error, error.__traceback__))[:1500]
        self.logger.error(f"Error en comando {ctx.command} por {ctx.author}: {error}\n{err_text}")

        # Notificar en canal (embed) si el comando falló
        embed = self._make_embed(
            title="⚠️ Error ejecutando comando",
            description=f"Comando: `{ctx.command}`\nError: `{error}`",
            color=discord.Color.orange()
        )
        try:
            await ctx.send(embed=embed)
        except Exception:
            # si falla enviar al canal, lo logueamos
            self.logger.exception("No se pudo enviar el embed de error al canal.")

    # ----------------------------
    # Comando opcional para ver últimos logs (útil en desarrollo)
    # ----------------------------
    @commands.command(name="showlogs")
    @commands.is_owner()
    async def showlogs(self, ctx, lines: int = 25):
        """Comando para el owner: muestra últimas líneas del archivo de logs."""
        try:
            with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read().splitlines()
            tail = content[-lines:]
            text = "```\n" + "\n".join(tail[-1500:]) + "\n```"
            await ctx.send(content=text[:2000])  # discord message limit
        except Exception as e:
            self.logger.exception("Error al leer el archivo de logs")
            await ctx.send(f"Error leyendo logs: {e}")


async def setup(bot):
    # Evitar agregar múltiples handlers si el módulo se recarga — ya lo hace setup_root_logger
    # Añadimos el cog normalmente
    logger.debug("Cargando cog logs...")
    await bot.add_cog(Logs(bot))
    logger.debug("Cog logs cargado correctamente.")

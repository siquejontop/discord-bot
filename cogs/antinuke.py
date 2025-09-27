import discord
from discord.ext import commands
from datetime import datetime, timedelta, timezone
import logging

# =====================================================
# CONFIGURACIÓN
# =====================================================
OWNER_IDS = [335596693603090434, 523662219020337153, 1158970670928113745]  # IDs de dueños del bot
WHITELIST = {1325579039888511056, 235148962103951360, 762271645855252501, 416358583220043796}  # IDs de usuarios whitelist
LOG_CHANNEL_ID = 1421331172969156660  # Canal donde se mandan los logs

# Roles importantes (poner IDs directos)
PROTECTED_ROLE_ID = 1421330892038869063  # Rol "auth mm"
OWNER_ROLE_ID = 1421330806399565888  # Rol "owner"

# Límites anti-abuso
MAX_BANS = 3
MAX_CHANNELS = 3
MAX_ROLES = 3

# Tiempo de expiración para contadores de acciones (en segundos)
ACTION_EXPIRY_SECONDS = 300  # 5 minutos

# Archivo de logs local
LOG_FILE = "/data/antinuke.log"

# Configurar logging local
logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format='%(asctime)s - %(message)s')

class AntiNuke(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.user_actions = {}  # {user_id: {"bans": int, "channels": int, "roles": int, "last_action": datetime}}

    # =====================================================
    # 📜 Logs
    # =====================================================
    async def log_action(self, guild, description):
        channel = guild.get_channel(LOG_CHANNEL_ID)
        if channel:
            embed = discord.Embed(
                title="🛡️ Sistema AntiNuke",
                description=description,
                color=discord.Color.red()
            )
            await channel.send(embed=embed)
        logging.info(f"{guild.name}: {description}")

    def is_whitelisted(self, user_id, guild):
        return (
            user_id in OWNER_IDS
            or user_id == guild.owner_id
            or user_id in WHITELIST
        )

    async def check_actions(self, executor):
        current_time = datetime.now(timezone.utc)
        if executor.id in self.user_actions:
            last_action = self.user_actions[executor.id].get("last_action", current_time)
            if (current_time - last_action).total_seconds() > ACTION_EXPIRY_SECONDS:
                self.user_actions[executor.id] = {"bans": 0, "channels": 0, "roles": 0, "last_action": current_time}
            else:
                self.user_actions[executor.id]["last_action"] = current_time

    # =====================================================
    # 🚨 Anti Massban
    # =====================================================
    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.ban):
            if (datetime.now(timezone.utc) - entry.created_at).total_seconds() < 60:
                executor = entry.user
                if self.is_whitelisted(executor.id, guild):
                    return
                await self.check_actions(executor)
                self.user_actions.setdefault(executor.id, {"bans": 0, "channels": 0, "roles": 0, "last_action": datetime.now(timezone.utc)})
                self.user_actions[executor.id]["bans"] += 1
                if self.user_actions[executor.id]["bans"] >= MAX_BANS:
                    await guild.ban(executor, reason="AntiNuke: demasiados bans")
                    await self.log_action(guild, f"🚫 {executor.mention} baneado por intentar hacer massban.")
                break

    # =====================================================
    # 🚨 Anti creación masiva de canales
    # =====================================================
    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        guild = channel.guild
        async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.channel_create):
            if (datetime.now(timezone.utc) - entry.created_at).total_seconds() < 60:
                executor = entry.user
                if self.is_whitelisted(executor.id, guild):
                    return
                await self.check_actions(executor)
                self.user_actions.setdefault(executor.id, {"bans": 0, "channels": 0, "roles": 0, "last_action": datetime.now(timezone.utc)})
                self.user_actions[executor.id]["channels"] += 1
                if self.user_actions[executor.id]["channels"] >= MAX_CHANNELS:
                    await guild.ban(executor, reason="AntiNuke: demasiados canales creados")
                    await self.log_action(guild, f"🚨 {executor.mention} baneado por creación masiva de canales.")
                break

    # =====================================================
    # 🚨 Anti creación masiva de roles
    # =====================================================
    @commands.Cog.listener()
    async def on_guild_role_create(self, role):
        guild = role.guild
        async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.role_create):
            if (datetime.now(timezone.utc) - entry.created_at).total_seconds() < 60:
                executor = entry.user
                if self.is_whitelisted(executor.id, guild):
                    return
                await self.check_actions(executor)
                self.user_actions.setdefault(executor.id, {"bans": 0, "channels": 0, "roles": 0, "last_action": datetime.now(timezone.utc)})
                self.user_actions[executor.id]["roles"] += 1
                if self.user_actions[executor.id]["roles"] >= MAX_ROLES:
                    await guild.ban(executor, reason="AntiNuke: demasiados roles creados")
                    await self.log_action(guild, f"🚨 {executor.mention} baneado por creación masiva de roles.")
                break

    # =====================================================
    # 🚨 Anti permisos peligrosos
    # =====================================================
    @commands.Cog.listener()
    async def on_guild_role_update(self, before, after):
        guild = after.guild
        async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.role_update):
            if (datetime.now(timezone.utc) - entry.created_at).total_seconds() < 60:
                executor = entry.user
                if self.is_whitelisted(executor.id, guild):
                    return

                dangerous = [
                    after.permissions.administrator,
                    after.permissions.ban_members,
                    after.permissions.kick_members,
                    after.permissions.manage_channels,
                    after.permissions.manage_roles,
                ]

                if any(dangerous):
                    await after.edit(permissions=before.permissions)
                    await guild.ban(executor, reason="AntiNuke: intentó dar permisos peligrosos")
                    await self.log_action(guild, f"⚠️ {executor.mention} intentó dar permisos peligrosos.")
                break

    # =====================================================
    # 🚨 Protección rol AUTH MM
    # =====================================================
    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        guild = after.guild
        auth_mm = guild.get_role(PROTECTED_ROLE_ID)
        owner_role = guild.get_role(OWNER_ROLE_ID)

        if not auth_mm or not owner_role:
            return

        if auth_mm in after.roles and auth_mm not in before.roles:
            async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.member_role_update):
                if (datetime.now(timezone.utc) - entry.created_at).total_seconds() < 60:
                    executor = entry.user

                    if (
                        executor.id in OWNER_IDS
                        or executor.id == guild.owner_id
                        or owner_role in executor.roles
                    ):
                        return

                    try:
                        await after.remove_roles(auth_mm, reason="AntiNuke: rol protegido")
                        await executor.timeout(timedelta(minutes=10), reason="Intentó dar rol protegido")
                    except discord.Forbidden:
                        await self.log_action(guild, f"⛔ No tengo permisos para remover el rol de {after.mention} o aplicar timeout a {executor.mention}.")
                    except discord.HTTPException as e:
                        await self.log_action(guild, f"⛔ Error al gestionar rol protegido: {e}")
                    else:
                        await self.log_action(
                            guild,
                            f"⛔ {executor.mention} intentó dar el rol protegido a {after.mention}. "
                            f"El rol fue removido y se aplicó timeout (10 min)."
                        )
                    break

    # =====================================================
    # 🚨 Anti creación de webhooks
    # =====================================================
    @commands.Cog.listener()
    async def on_webhook_create(self, webhook):
        guild = webhook.guild
        logging.info(f"Evento on_webhook_create activado para {webhook.name} en {guild.name}")
        async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.webhook_create):
            logging.info(f"Entrada de auditoría encontrada: {entry.user} a las {entry.created_at}")
            if (datetime.now(timezone.utc) - entry.created_at).total_seconds() < 10:
                executor = entry.user
                logging.info(f"Webhook creado por {executor} en {webhook.channel.mention} dentro de los 10 segundos")
                if self.is_whitelisted(executor.id, guild):
                    logging.info(f"Usuario {executor} está en la whitelist, no se toman medidas.")
                    return
                logging.info(f"Usuario {executor} no está en la whitelist, procediendo con medidas.")
                try:
                    await webhook.delete(reason="AntiNuke: creación de webhook no autorizada")
                    await guild.ban(executor, reason="AntiNuke: creó un webhook no autorizado")
                    await self.log_action(guild, f"🔗 {executor.mention} baneado por crear un webhook no autorizado en el canal {webhook.channel.mention}.")
                    logging.info(f"Webhook eliminado y {executor} baneado exitosamente.")
                except discord.Forbidden:
                    await self.log_action(guild, f"⛔ No tengo permisos para eliminar el webhook creado por {executor.mention}.")
                    logging.info(f"Fallo por permisos insuficientes para eliminar webhook de {executor}.")
                except discord.HTTPException as e:
                    await self.log_action(guild, f"⛔ Error al eliminar webhook: {e}")
                    logging.info(f"Error HTTP al procesar webhook de {executor}: {e}")
                break
        else:
            logging.info(f"No se encontró entrada de auditoría para {webhook.name} en los últimos 10 segundos.")

    # =====================================================
    # 🚨 Anti adición de bots/aplicaciones
    # =====================================================
    @commands.Cog.listener()
    async def on_member_join(self, member):
        guild = member.guild
        if member.bot:
            async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.bot_add):
                if (datetime.now(timezone.utc) - entry.created_at).total_seconds() < 60:
                    executor = entry.user
                    if self.is_whitelisted(executor.id, guild):
                        return
                    try:
                        await member.ban(reason="AntiNuke: adición de bot no autorizada")
                        await guild.ban(executor, reason="AntiNuke: añadió un bot no autorizado")
                        await self.log_action(guild, f"🤖 {executor.mention} baneado por añadir un bot: {member.mention}.")
                    except discord.Forbidden:
                        await self.log_action(guild, f"⛔ No tengo permisos para banear al bot {member.mention} o a {executor.mention}.")
                    except discord.HTTPException as e:
                        await self.log_action(guild, f"⛔ Error al banear bot: {e}")
                    break

    # =====================================================
    # 📖 Comando de ayuda
    # =====================================================
    @commands.command(name="helpantinuke")
    async def helpantinuke(self, ctx):
        embed = discord.Embed(
            title="🛡️ Ayuda AntiNuke",
            description="Lista de protecciones activas (la whitelist es estática y definida en el código):",
            color=discord.Color.blue()
        )
        embed.add_field(name="Protecciones activas", value="""  
        ✅ Anti massban  
        ✅ Anti creación masiva de canales  
        ✅ Anti creación masiva de roles  
        ✅ Anti permisos peligrosos  
        ✅ Protección especial rol **auth mm** (solo Owner pueden darlo)  
        ✅ Anti creación de webhooks  
        ✅ Anti adición de bots/aplicaciones  
        """, inline=False)
        await ctx.send(embed=embed)

# =====================================================
# 🔌 Setup
# =====================================================
async def setup(bot):
    await bot.add_cog(AntiNuke(bot))

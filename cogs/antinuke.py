import discord
from discord.ext import commands
from datetime import timedelta
import json
import os

# =====================================================
# CONFIGURACIÓN
# =====================================================
OWNER_IDS = [335596693603090434, 523662219020337153]  # IDs de dueños del bot
LOG_CHANNEL_ID = 1418097943730327642  # Canal donde se mandan los logs

# Roles importantes (poner IDs directos)
PROTECTED_ROLE_ID = 1415860205656215602  # Rol "auth mm"
OWNER_ROLE_ID = 1415860178120609925  # Rol "owner"

# Límites anti-abuso
MAX_BANS = 3
MAX_CHANNELS = 3
MAX_ROLES = 3

# Archivo de whitelist
WHITELIST_FILE = "whitelist.json"

def load_whitelist():
    if os.path.exists(WHITELIST_FILE):
        with open(WHITELIST_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()

def save_whitelist():
    with open(WHITELIST_FILE, "w", encoding="utf-8") as f:
        json.dump(list(WHITELIST), f, indent=4)

# Cargar whitelist al iniciar
WHITELIST = load_whitelist()


class AntiNuke(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.user_actions = {}

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

    def is_whitelisted(self, user_id, guild):
        return (
            user_id in OWNER_IDS
            or user_id == guild.owner_id
            or user_id in WHITELIST
        )

    # =====================================================
    # ⚡ Comandos de whitelist
    # =====================================================
    @commands.command()
    async def whitelist(self, ctx, member: discord.Member):
        if ctx.author.id not in OWNER_IDS and ctx.author.id != ctx.guild.owner_id:
            return await ctx.send("❌ No tienes permisos para usar este comando.")

        WHITELIST.add(member.id)
        save_whitelist()
        await ctx.send(f"✅ {member.mention} ha sido añadido a la whitelist.")

        await self.log_action(ctx.guild, f"✅ {ctx.author.mention} añadió a {member.mention} a la whitelist.")

    @commands.command()
    async def unwhitelist(self, ctx, member: discord.Member):
        if ctx.author.id not in OWNER_IDS and ctx.author.id != ctx.guild.owner_id:
            return await ctx.send("❌ No tienes permisos para usar este comando.")

        if member.id in WHITELIST:
            WHITELIST.remove(member.id)
            save_whitelist()
            await ctx.send(f"✅ {member.mention} ha sido removido de la whitelist.")
            await self.log_action(ctx.guild, f"❌ {ctx.author.mention} quitó a {member.mention} de la whitelist.")
        else:
            await ctx.send("⚠️ Ese usuario no estaba en la whitelist.")

    @commands.command()
    async def whitelisted(self, ctx):
        if not WHITELIST:
            return await ctx.send("⚠️ No hay usuarios en la whitelist.")

        embed = discord.Embed(
            title="📝 Usuarios en Whitelist",
            color=discord.Color.blue()
        )
        for user_id in WHITELIST:
            user = ctx.guild.get_member(user_id)
            if user:
                embed.add_field(name=user.name, value=f"{user.mention} (`{user.id}`)", inline=False)
            else:
                embed.add_field(name="Usuario desconocido", value=f"`{user_id}`", inline=False)

        await ctx.send(embed=embed)

    # =====================================================
    # 🚨 Anti Massban
    # =====================================================
    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.ban):
            executor = entry.user
            if self.is_whitelisted(executor.id, guild):
                return

            self.user_actions.setdefault(executor.id, {"bans": 0})
            self.user_actions[executor.id]["bans"] += 1

            if self.user_actions[executor.id]["bans"] >= MAX_BANS:
                await guild.ban(executor, reason="AntiNuke: demasiados bans")
                await self.log_action(guild, f"🚫 {executor.mention} baneado por intentar hacer massban.")

    # =====================================================
    # 🚨 Anti creación masiva de canales
    # =====================================================
    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        guild = channel.guild
        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_create):
            executor = entry.user
            if self.is_whitelisted(executor.id, guild):
                return

            self.user_actions.setdefault(executor.id, {"channels": 0})
            self.user_actions[executor.id]["channels"] += 1

            if self.user_actions[executor.id]["channels"] >= MAX_CHANNELS:
                await guild.ban(executor, reason="AntiNuke: demasiados canales creados")
                await self.log_action(guild, f"🚨 {executor.mention} baneado por creación masiva de canales.")

    # =====================================================
    # 🚨 Anti creación masiva de roles
    # =====================================================
    @commands.Cog.listener()
    async def on_guild_role_create(self, role):
        guild = role.guild
        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.role_create):
            executor = entry.user
            if self.is_whitelisted(executor.id, guild):
                return

            self.user_actions.setdefault(executor.id, {"roles": 0})
            self.user_actions[executor.id]["roles"] += 1

            if self.user_actions[executor.id]["roles"] >= MAX_ROLES:
                await guild.ban(executor, reason="AntiNuke: demasiados roles creados")
                await self.log_action(guild, f"🚨 {executor.mention} baneado por creación masiva de roles.")

    # =====================================================
    # 🚨 Anti permisos peligrosos
    # =====================================================
    @commands.Cog.listener()
    async def on_guild_role_update(self, before, after):
        guild = after.guild
        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.role_update):
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
            async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.member_role_update):
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
                except:
                    pass

                await self.log_action(
                    guild,
                    f"⛔ {executor.mention} intentó dar el rol protegido a {after.mention}. "
                    f"El rol fue removido y se aplicó timeout (10 min)."
                )

    # =====================================================
    # 📖 Comando de ayuda
    # =====================================================
    @commands.command(name="helpantinuke")
    async def helpantinuke(self, ctx):
        embed = discord.Embed(
            title="🛡️ Ayuda AntiNuke",
            description="Lista de comandos y protecciones activas:",
            color=discord.Color.blue()
        )
        embed.add_field(name="$whitelist <usuario>", value="Añade un usuario a la whitelist.", inline=False)
        embed.add_field(name="$unwhitelist <usuario>", value="Remueve un usuario de la whitelist.", inline=False)
        embed.add_field(name="$whitelisted", value="Muestra todos los usuarios en la whitelist.", inline=False)
        embed.add_field(name="Protecciones activas", value="""  
        ✅ Anti massban  
        ✅ Anti creación masiva de canales  
        ✅ Anti creación masiva de roles  
        ✅ Anti permisos peligrosos  
        ✅ Protección especial rol **auth mm** (solo Owner o dueños pueden darlo)  
        """, inline=False)
        await ctx.send(embed=embed)


# =====================================================
# 🔌 Setup
# =====================================================
async def setup(bot):
    await bot.add_cog(AntiNuke(bot))

import discord
from discord.ext import commands
from datetime import datetime, timedelta, timezone
import json
import os

# =====================================================
# CONFIG
# =====================================================
LOG_CHANNEL_ID = 1418314310739955742  # Reemplaza con el ID de tu canal de logs
WARN_FILE = "data/warns.json"
CASES_FILE = "data/cases.json"
MUTE_ROLE_ID = 1418314510049083576    # Reemplaza con tu rol mute


# =====================================================
# Helpers: JSON
# =====================================================
def load_json(path, default):
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(default, f, indent=4)
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


# =====================================================
# Moderation Cog
# =====================================================
class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.warns = load_json(WARN_FILE, {})
        self.cases = load_json(CASES_FILE, {"last_case": 0, "cases": []})

    # -------------------------------------------------
    # 📌 CASE SYSTEM
    # -------------------------------------------------
    def new_case(self, action, user, moderator, reason):
        self.cases["last_case"] += 1
        case_id = self.cases["last_case"]

        entry = {
            "id": case_id,
            "action": action,
            "user_id": getattr(user, "id", user),
            "moderator_id": moderator.id,
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        self.cases["cases"].append(entry)
        save_json(CASES_FILE, self.cases)
        return case_id

    async def log_action(self, guild, action, user, moderator, reason, case_id):
        channel = guild.get_channel(LOG_CHANNEL_ID)
        if not channel:
            return

        embed = discord.Embed(
            title=f"📌 {action.upper()} | Case #{case_id}",
            color=discord.Color.red() if action in ["ban", "kick", "mute", "warn", "timeout", "lock"] else discord.Color.green(),
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="👤 Usuario", value=f"{user.mention if hasattr(user,'mention') else user} (`{getattr(user,'id',user)}`)", inline=False)
        embed.add_field(name="🛠️ Moderador", value=f"{moderator.mention} (`{moderator.id}`)", inline=False)
        embed.add_field(name="📝 Razón", value=reason, inline=False)

        await channel.send(embed=embed)

    async def error_embed(self, ctx, msg, usage=None):
        embed = discord.Embed(
            title="❌ Error",
            description=msg,
            color=discord.Color.red()
        )
        if usage:
            embed.add_field(name="Uso correcto", value=f"`{usage}`", inline=False)
        await ctx.send(embed=embed)

    # =====================================================
    # 🔨 Ban
    # =====================================================
    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member = None, *, reason="No se especificó razón"):
        if not member:
            return await self.error_embed(ctx, "Debes mencionar un usuario.", "$ban @usuario [razón]")

        try:
            await member.ban(reason=reason)
        except discord.Forbidden:
            return await self.error_embed(ctx, "No tengo permisos para banear a ese usuario.")

        case_id = self.new_case("ban", member, ctx.author, reason)
        await ctx.send(f"✅ {member.mention} fue baneado. (Case #{case_id})")
        await self.log_action(ctx.guild, "ban", member, ctx.author, reason, case_id)

    # =====================================================
    # ♻️ Unban
    # =====================================================
    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx, user_id: int = None):
        if not user_id:
            return await self.error_embed(ctx, "Debes poner el ID del usuario.", "$unban <user_id>")

        user = await self.bot.fetch_user(user_id)
        try:
            await ctx.guild.unban(user)
        except discord.Forbidden:
            return await self.error_embed(ctx, "No tengo permisos para desbanear.")
        except discord.NotFound:
            return await self.error_embed(ctx, "Ese usuario no está baneado.")

        case_id = self.new_case("unban", user, ctx.author, "Unban manual")
        await ctx.send(f"✅ {user.mention} fue desbaneado. (Case #{case_id})")
        await self.log_action(ctx.guild, "unban", user, ctx.author, "Unban manual", case_id)

    # =====================================================
    # 🚫 Kick
    # =====================================================
    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member = None, *, reason="No se especificó razón"):
        if not member:
            return await self.error_embed(ctx, "Debes mencionar un usuario.", "$kick @usuario [razón]")

        try:
            await member.kick(reason=reason)
        except discord.Forbidden:
            return await self.error_embed(ctx, "No tengo permisos para expulsar a ese usuario.")

        case_id = self.new_case("kick", member, ctx.author, reason)
        await ctx.send(f"⚠️ {member.mention} fue expulsado. (Case #{case_id})")
        await self.log_action(ctx.guild, "kick", member, ctx.author, reason, case_id)

    # =====================================================
    # 🤐 Mute
    # =====================================================
    @commands.command()
    @commands.has_permissions(manage_roles=True)
    async def mute(self, ctx, member: discord.Member = None, *, reason="No se especificó razón"):
        if not member:
            return await self.error_embed(ctx, "Debes mencionar un usuario.", "$mute @usuario [razón]")

        mute_role = ctx.guild.get_role(MUTE_ROLE_ID)
        if not mute_role:
            return await self.error_embed(ctx, "No se encontró el rol de mute configurado.")

        await member.add_roles(mute_role, reason=reason)
        case_id = self.new_case("mute", member, ctx.author, reason)
        await ctx.send(f"🔇 {member.mention} fue muteado. (Case #{case_id})")
        await self.log_action(ctx.guild, "mute", member, ctx.author, reason, case_id)

    # =====================================================
    # 🔊 Unmute
    # =====================================================
    @commands.command()
    @commands.has_permissions(manage_roles=True)
    async def unmute(self, ctx, member: discord.Member = None):
        if not member:
            return await self.error_embed(ctx, "Debes mencionar un usuario.", "$unmute @usuario")

        mute_role = ctx.guild.get_role(MUTE_ROLE_ID)
        if not mute_role or mute_role not in member.roles:
            return await self.error_embed(ctx, "Ese usuario no estaba muteado.")

        await member.remove_roles(mute_role)
        case_id = self.new_case("unmute", member, ctx.author, "Unmute manual")
        await ctx.send(f"🔊 {member.mention} fue desmuteado. (Case #{case_id})")
        await self.log_action(ctx.guild, "unmute", member, ctx.author, "Unmute manual", case_id)

    # =====================================================
    # ⏳ Timeout
    # =====================================================
    @commands.command()
    @commands.has_permissions(moderate_members=True)
    async def timeout(self, ctx, member: discord.Member = None, minutes: int = None, *, reason="No se especificó razón"):
        if not member or not minutes:
            return await self.error_embed(ctx, "Debes mencionar un usuario y tiempo en minutos.", "$timeout @usuario <minutos> [razón]")

        until = datetime.now(timezone.utc) + timedelta(minutes=minutes)
        try:
            await member.timeout(until, reason=reason)
        except discord.Forbidden:
            return await self.error_embed(ctx, "No tengo permisos para dar timeout a ese usuario.")

        case_id = self.new_case("timeout", member, ctx.author, reason)
        await ctx.send(f"⏳ {member.mention} fue silenciado por {minutes} minutos. (Case #{case_id})")
        await self.log_action(ctx.guild, "timeout", member, ctx.author, reason, case_id)

    # =====================================================
    # 🔓 Remove Timeout
    # =====================================================
    @commands.command()
    @commands.has_permissions(moderate_members=True)
    async def remove_timeout(self, ctx, member: discord.Member = None):
        if not member:
            return await self.error_embed(ctx, "Debes mencionar un usuario.", "$remove_timeout @usuario")

        try:
            await member.timeout(None)
        except discord.Forbidden:
            return await self.error_embed(ctx, "No tengo permisos para quitar el timeout.")

        case_id = self.new_case("remove_timeout", member, ctx.author, "Timeout removido")
        await ctx.send(f"🔓 Timeout removido para {member.mention}. (Case #{case_id})")
        await self.log_action(ctx.guild, "remove_timeout", member, ctx.author, "Timeout removido", case_id)

    # =====================================================
    # 🧹 Purge
    # =====================================================
    @commands.command(aliases=["purge","c","p"])
    @commands.has_permissions(manage_messages=True)
    async def clear(self, ctx, amount: int = None):
        if not amount:
            return await self.error_embed(ctx, "Debes poner un número de mensajes.", "$purge <cantidad>")

        deleted = await ctx.channel.purge(limit=amount + 1)
        case_id = self.new_case("purge", ctx.author, ctx.author, f"Eliminó {len(deleted)-1} mensajes")
        await ctx.send(f"🧹 Se eliminaron {len(deleted)-1} mensajes. (Case #{case_id})", delete_after=5)
        await self.log_action(ctx.guild, "purge", ctx.author, ctx.author, f"Eliminó {len(deleted)-1} mensajes", case_id)

    # =====================================================
    # 👁️ Slowmode
    # =====================================================
    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def slowmode(self, ctx, seconds: int = None):
        if seconds is None:
            return await self.error_embed(ctx, "Debes poner el tiempo en segundos.", "$slowmode <segundos>")

        await ctx.channel.edit(slowmode_delay=seconds)
        case_id = self.new_case("slowmode", ctx.author, ctx.author, f"Slowmode {seconds}s")
        msg = "desactivado" if seconds == 0 else f"activado ({seconds}s)"
        await ctx.send(f"⏳ Slowmode {msg}. (Case #{case_id})")
        await self.log_action(ctx.guild, "slowmode", ctx.author, ctx.author, f"Slowmode {msg}", case_id)

    # =====================================================
    # 🔒 Lock
    # =====================================================
    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def lock(self, ctx):
        overwrite = ctx.channel.overwrites_for(ctx.guild.default_role)
        overwrite.send_messages = False
        await ctx.channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)

        case_id = self.new_case("lock", ctx.author, ctx.author, "Canal bloqueado")
        await ctx.send(f"🔒 Canal bloqueado. (Case #{case_id})")
        await self.log_action(ctx.guild, "lock", ctx.author, ctx.author, "Canal bloqueado", case_id)

    # =====================================================
    # 🔓 Unlock
    # =====================================================
    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def unlock(self, ctx):
        overwrite = ctx.channel.overwrites_for(ctx.guild.default_role)
        overwrite.send_messages = True
        await ctx.channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)

        case_id = self.new_case("unlock", ctx.author, ctx.author, "Canal desbloqueado")
        await ctx.send(f"🔓 Canal desbloqueado. (Case #{case_id})")
        await self.log_action(ctx.guild, "unlock", ctx.author, ctx.author, "Canal desbloqueado", case_id)

    # =====================================================
    # ⚠️ Warns
    # =====================================================
    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def warn(self, ctx, member: discord.Member = None, *, reason="No se especificó razón"):
        if not member:
            return await self.error_embed(ctx, "Debes mencionar un usuario.", "$warn @usuario [razón]")

        if str(member.id) not in self.warns:
            self.warns[str(member.id)] = []

        self.warns[str(member.id)].append({
            "moderator": ctx.author.id,
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        save_json(WARN_FILE, self.warns)

        case_id = self.new_case("warn", member, ctx.author, reason)
        await ctx.send(f"⚠️ {member.mention} recibió un warn. (Case #{case_id})")
        await self.log_action(ctx.guild, "warn", member, ctx.author, reason, case_id)

    @commands.command()
    async def warns(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        warns = self.warns.get(str(member.id), [])
        if not warns:
            return await ctx.send(f"✅ {member.mention} no tiene warns.")

        embed = discord.Embed(
            title=f"⚠️ Warns de {member}",
            color=discord.Color.orange()
        )
        for i, w in enumerate(warns, 1):
            mod = ctx.guild.get_member(w["moderator"])
            embed.add_field(
                name=f"#{i} - {w['timestamp'][:19]}",
                value=f"👮 Moderador: {mod.mention if mod else w['moderator']}\n📝 Razón: {w['reason']}",
                inline=False
            )
        await ctx.send(embed=embed)

    @commands.command()
    async def warnlist(self, ctx):
        if not self.warns:
            return await ctx.send("✅ Nadie tiene warns actualmente.")

        embed = discord.Embed(
            title="📋 Lista de usuarios con warns",
            color=discord.Color.gold()
        )
        for uid, warns in self.warns.items():
            user = ctx.guild.get_member(int(uid)) or f"ID: {uid}"
            embed.add_field(
                name=str(user),
                value=f"⚠️ {len(warns)} warns",
                inline=False
            )
        await ctx.send(embed=embed)


# =====================================================
# 🔌 Setup
# =====================================================
async def setup(bot):
    await bot.add_cog(Moderation(bot))

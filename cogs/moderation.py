import discord
from discord.ext import commands
from discord import utils
from datetime import datetime, timedelta, timezone
import json
import os

# =====================================================
# ⚙️ CONFIGURACIÓN LOCAL (aquí van los IDs)
# =====================================================
MUTE_ROLE_ID = 1418314510049083576   # Rol para muteados
LIMIT_ROLE_ID = 1415860204624416971  # Rol límite para usar moderación
LOG_CHANNEL_ID = 1418314310739955742 # Canal de logs

# Archivos de persistencia
WARNS_FILE = "warns.json"
CASES_FILE = "cases.json"

# =====================================================
# 📌 Helpers para persistencia
# =====================================================
def load_json(filename, default):
    if not os.path.exists(filename):
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(default, f, indent=4)
    with open(filename, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

# Inicializamos warns y cases
warns_data = load_json(WARNS_FILE, {})
cases_data = load_json(CASES_FILE, {"last_case": 0, "cases": []})

# =====================================================
# 📌 Helper: generar Case ID
# =====================================================
def create_case(action, user_id, moderator_id, reason):
    cases_data["last_case"] += 1
    case_id = cases_data["last_case"]
    case = {
        "id": case_id,
        "action": action,
        "user_id": user_id,
        "moderator_id": moderator_id,
        "reason": reason,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    cases_data["cases"].append(case)
    save_json(CASES_FILE, cases_data)
    return case_id

# =====================================================
# 📌 Helper: logs al canal
# =====================================================
async def send_log(guild, embed):
    channel = guild.get_channel(LOG_CHANNEL_ID)
    if channel:
        await channel.send(embed=embed)

# =====================================================
# 🛠️ Moderation Cog
# =====================================================
class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # -------------------------------------------------
    # 📌 Helper: verificar rol suficiente
    # -------------------------------------------------
    def has_permission(self, ctx):
        limit_role = ctx.guild.get_role(LIMIT_ROLE_ID)
        return not (limit_role and ctx.author.top_role <= limit_role)

    def permission_embed(self, ctx, action="usar este comando"):
        return discord.Embed(
            title="⛔ Permiso insuficiente",
            description=f"{ctx.author.mention}, tu rol no es suficiente para **{action}**.",
            color=discord.Color.red()
        )

    # =====================================================
    # 🔨 Ban
    # =====================================================
    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member = None, *, reason="No se especificó razón"):
        if member is None:
            embed = discord.Embed(
                title="❌ Uso incorrecto de ban",
                description="Formato correcto:\n`$ban @usuario [razón]`",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return

        try:
            await member.ban(reason=reason)
            case_id = create_case("ban", member.id, ctx.author.id, reason)

            embed = discord.Embed(
                title="⛔ Usuario baneado",
                description=f"{member.mention} fue baneado.\n**Razón:** {reason}\n📂 Case #{case_id}",
                color=discord.Color.red(),
                timestamp=datetime.now(timezone.utc)
            )
            await ctx.send(embed=embed)
            await send_log(ctx.guild, embed)
        except discord.Forbidden:
            await ctx.send(embed=discord.Embed(
                title="❌ Error",
                description="No tengo permisos para banear a ese usuario.",
                color=discord.Color.red()
            ))

    # =====================================================
    # ♻️ Unban
    # =====================================================
    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx, user_id: int = None):
        if user_id is None:
            embed = discord.Embed(
                title="❌ Uso incorrecto de unban",
                description="Formato correcto:\n`$unban <user_id>`",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return

        user = await self.bot.fetch_user(user_id)
        try:
            await ctx.guild.unban(user)
            case_id = create_case("unban", user.id, ctx.author.id, "Desbaneo manual")

            embed = discord.Embed(
                title="✅ Usuario desbaneado",
                description=f"{user.mention} fue desbaneado.\n📂 Case #{case_id}",
                color=discord.Color.green(),
                timestamp=datetime.now(timezone.utc)
            )
            await ctx.send(embed=embed)
            await send_log(ctx.guild, embed)
        except discord.NotFound:
            await ctx.send("⚠️ Ese usuario no estaba baneado.")

    # =====================================================
    # 🚫 Kick
    # =====================================================
    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member = None, *, reason="No se especificó razón"):
        if member is None:
            embed = discord.Embed(
                title="❌ Uso incorrecto de kick",
                description="Formato correcto:\n`$kick @usuario [razón]`",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return

        try:
            await member.kick(reason=reason)
            case_id = create_case("kick", member.id, ctx.author.id, reason)

            embed = discord.Embed(
                title="⚠️ Usuario expulsado",
                description=f"{member.mention} fue expulsado.\n**Razón:** {reason}\n📂 Case #{case_id}",
                color=discord.Color.orange(),
                timestamp=datetime.now(timezone.utc)
            )
            await ctx.send(embed=embed)
            await send_log(ctx.guild, embed)
        except discord.Forbidden:
            await ctx.send("❌ No tengo permisos para expulsar a ese usuario.")

    # =====================================================
    # 🤐 Mute / Unmute
    # =====================================================
    @commands.command()
    @commands.has_permissions(manage_roles=True)
    async def mute(self, ctx, member: discord.Member = None, *, reason="No se especificó razón"):
        if not self.has_permission(ctx):
            return await ctx.send(embed=self.permission_embed(ctx, "dar mute"))

        if member is None:
            embed = discord.Embed(
                title="❌ Uso incorrecto de mute",
                description="Formato correcto:\n`$mute @usuario [razón]`",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return

        mute_role = ctx.guild.get_role(MUTE_ROLE_ID)
        if mute_role:
            await member.add_roles(mute_role, reason=reason)
            case_id = create_case("mute", member.id, ctx.author.id, reason)

            embed = discord.Embed(
                title="🔇 Usuario muteado",
                description=f"{member.mention} fue muteado.\n**Razón:** {reason}\n📂 Case #{case_id}",
                color=discord.Color.dark_gray(),
                timestamp=datetime.now(timezone.utc)
            )
            await ctx.send(embed=embed)
            await send_log(ctx.guild, embed)
        else:
            await ctx.send("⚠️ No se encontró el rol de mute configurado.")

    @commands.command()
    @commands.has_permissions(manage_roles=True)
    async def unmute(self, ctx, member: discord.Member = None):
        if not self.has_permission(ctx):
            return await ctx.send(embed=self.permission_embed(ctx, "quitar mute"))

        if member is None:
            embed = discord.Embed(
                title="❌ Uso incorrecto de unmute",
                description="Formato correcto:\n`$unmute @usuario`",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return

        mute_role = ctx.guild.get_role(MUTE_ROLE_ID)
        if mute_role and mute_role in member.roles:
            await member.remove_roles(mute_role)
            case_id = create_case("unmute", member.id, ctx.author.id, "Unmute manual")

            embed = discord.Embed(
                title="🔊 Usuario desmuteado",
                description=f"{member.mention} fue desmuteado.\n📂 Case #{case_id}",
                color=discord.Color.green(),
                timestamp=datetime.now(timezone.utc)
            )
            await ctx.send(embed=embed)
            await send_log(ctx.guild, embed)
        else:
            await ctx.send("⚠️ Ese usuario no estaba muteado.")

    # =====================================================
    # 🚨 Warns
    # =====================================================
    @commands.command()
    async def warn(self, ctx, member: discord.Member = None, *, reason="No se especificó razón"):
        if member is None:
            return await ctx.send("❌ Uso correcto: `$warn @usuario [razón]`")

        if str(member.id) not in warns_data:
            warns_data[str(member.id)] = []

        warns_data[str(member.id)].append({
            "moderator": ctx.author.id,
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        save_json(WARNS_FILE, warns_data)

        case_id = create_case("warn", member.id, ctx.author.id, reason)

        embed = discord.Embed(
            title="⚠️ Usuario advertido",
            description=f"{member.mention} recibió un warn.\n**Razón:** {reason}\n📂 Case #{case_id}",
            color=discord.Color.orange(),
            timestamp=datetime.now(timezone.utc)
        )
        await ctx.send(embed=embed)
        await send_log(ctx.guild, embed)

    @commands.command()
    async def warns(self, ctx, member: discord.Member = None):
        if member is None:
            member = ctx.author

        user_warns = warns_data.get(str(member.id), [])
        if not user_warns:
            return await ctx.send(f"✅ {member.mention} no tiene warns.")

        embed = discord.Embed(
            title=f"📋 Warns de {member}",
            color=discord.Color.orange()
        )
        for i, warn in enumerate(user_warns, 1):
            mod = ctx.guild.get_member(warn["moderator"])
            embed.add_field(
                name=f"#{i} - {warn['timestamp']}",
                value=f"👮‍♂️ Moderador: {mod.mention if mod else warn['moderator']}\n📝 Razón: {warn['reason']}",
                inline=False
            )
        await ctx.send(embed=embed)

    # =====================================================
    # 📖 Help Moderation (completo con secciones)
    # =====================================================
    @commands.command(name="helpmoderation")
    async def helpmoderation(self, ctx):
        embed = discord.Embed(
            title="📖 Ayuda de Moderación",
            description="Lista de comandos de moderación disponibles:",
            color=discord.Color.blurple()
        )

        embed.add_field(
            name="🔨 Baneos",
            value="`$ban @usuario [razón]`\n`$unban <user_id>`",
            inline=False
        )
        embed.add_field(
            name="🚫 Expulsiones",
            value="`$kick @usuario [razón]`",
            inline=False
        )
        embed.add_field(
            name="🤐 Mutes",
            value="`$mute @usuario [razón]`\n`$unmute @usuario`",
            inline=False
        )
        embed.add_field(
            name="🚨 Advertencias",
            value="`$warn @usuario [razón]`\n`$warns [@usuario]`",
            inline=False
        )
        embed.add_field(
            name="⏱️ Timeouts",
            value="`$timeout @usuario <minutos> [razón]`\n`$untimeout @usuario`",
            inline=False
        )
        embed.add_field(
            name="🔒 Locks",
            value="`$lock #canal`\n`$unlock #canal`",
            inline=False
        )
        embed.add_field(
            name="🐌 Slowmode",
            value="`$slowmode #canal <segundos>`\n`$slowmode #canal 0` *(para quitar)*",
            inline=False
        )

        await ctx.send(embed=embed)

# =====================================================
# 🔌 Setup obligatorio
# =====================================================
async def setup(bot):
    await bot.add_cog(Moderation(bot))

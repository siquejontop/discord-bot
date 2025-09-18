import discord
from discord.ext import commands
from datetime import datetime, timedelta, timezone
import json
import os

# ==============================
# CONFIG LOCAL
# ==============================
MUTE_ROLE_ID = 123456789012345678
LIMIT_ROLE_ID = 987654321098765432
LOG_CHANNEL_ID = 112233445566778899

WARNS_FILE = "warns.json"
CASES_FILE = "cases.json"

# ==============================
# HELPERS JSON
# ==============================
def load_json(filename, default):
    if not os.path.exists(filename):
        with open(filename, "w") as f:
            json.dump(default, f, indent=4)
    with open(filename, "r") as f:
        return json.load(f)

def save_json(filename, data):
    with open(filename, "w") as f:
        json.dump(data, f, indent=4)

# ==============================
# CASE SYSTEM
# ==============================
def next_case(action, user_id, moderator_id, reason="No especificado"):
    data = load_json(CASES_FILE, {"last_case": 0, "cases": []})
    data["last_case"] += 1
    case_id = data["last_case"]

    case = {
        "id": case_id,
        "action": action,
        "user_id": user_id,
        "moderator_id": moderator_id,
        "reason": reason,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    data["cases"].append(case)
    save_json(CASES_FILE, data)
    return case

# ==============================
# Moderation Cog
# ==============================
class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ==============================
    # 📌 Helpers
    # ==============================
    def has_permission(self, ctx):
        limit_role = ctx.guild.get_role(LIMIT_ROLE_ID)
        return not (limit_role and ctx.author.top_role <= limit_role)

    async def log_action(self, ctx, case, title, color, extra=""):
        log_channel = ctx.guild.get_channel(LOG_CHANNEL_ID)
        if not log_channel:
            return
        embed = discord.Embed(
            title=title,
            color=color,
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="👤 Usuario", value=f"<@{case['user_id']}> (`{case['user_id']}`)", inline=False)
        embed.add_field(name="🛠️ Moderador", value=f"<@{case['moderator_id']}> (`{case['moderator_id']}`)", inline=False)
        embed.add_field(name="📝 Razón", value=case["reason"], inline=False)
        embed.add_field(name="📂 Case ID", value=f"#{case['id']}", inline=False)
        if extra:
            embed.add_field(name="📌 Extra", value=extra, inline=False)
        await log_channel.send(embed=embed)

    # ==============================
    # 🔨 Ban
    # ==============================
    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member = None, *, reason="No especificado"):
        if not member:
            return await ctx.send(embed=discord.Embed(
                title="❌ Uso incorrecto",
                description="Formato correcto:\n`$ban @usuario [razón]`",
                color=discord.Color.red()
            ))

        await member.ban(reason=reason)
        case = next_case("ban", member.id, ctx.author.id, reason)
        embed = discord.Embed(
            title="⛔ Usuario baneado",
            description=f"{member.mention} fue baneado.\n**Razón:** {reason}\n📂 Case #{case['id']}",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        await self.log_action(ctx, case, "⛔ Usuario baneado", discord.Color.red())

    # ==============================
    # ♻️ Unban
    # ==============================
    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx, user_id: int = None):
        if not user_id:
            return await ctx.send(embed=discord.Embed(
                title="❌ Uso incorrecto",
                description="Formato correcto:\n`$unban <user_id>`",
                color=discord.Color.red()
            ))

        user = await self.bot.fetch_user(user_id)
        await ctx.guild.unban(user)
        case = next_case("unban", user.id, ctx.author.id, "Unban manual")
        embed = discord.Embed(
            title="✅ Usuario desbaneado",
            description=f"{user.mention} fue desbaneado.\n📂 Case #{case['id']}",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
        await self.log_action(ctx, case, "✅ Usuario desbaneado", discord.Color.green())

    # ==============================
    # ⚠️ Kick
    # ==============================
    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member = None, *, reason="No especificado"):
        if not member:
            return await ctx.send(embed=discord.Embed(
                title="❌ Uso incorrecto",
                description="Formato correcto:\n`$kick @usuario [razón]`",
                color=discord.Color.red()
            ))

        await member.kick(reason=reason)
        case = next_case("kick", member.id, ctx.author.id, reason)
        embed = discord.Embed(
            title="⚠️ Usuario expulsado",
            description=f"{member.mention} fue expulsado.\n**Razón:** {reason}\n📂 Case #{case['id']}",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)
        await self.log_action(ctx, case, "⚠️ Usuario expulsado", discord.Color.orange())

    # ==============================
    # 🔇 Mute
    # ==============================
    @commands.command()
    @commands.has_permissions(manage_roles=True)
    async def mute(self, ctx, member: discord.Member = None, *, reason="No especificado"):
        mute_role = ctx.guild.get_role(MUTE_ROLE_ID)
        if not member or not mute_role:
            return await ctx.send("⚠️ Uso: `$mute @usuario [razón]` (y debe estar configurado el rol mute).")

        await member.add_roles(mute_role, reason=reason)
        case = next_case("mute", member.id, ctx.author.id, reason)
        embed = discord.Embed(
            title="🔇 Usuario muteado",
            description=f"{member.mention} fue muteado.\n**Razón:** {reason}\n📂 Case #{case['id']}",
            color=discord.Color.dark_gray()
        )
        await ctx.send(embed=embed)
        await self.log_action(ctx, case, "🔇 Usuario muteado", discord.Color.dark_gray())

    # ==============================
    # 🔊 Unmute
    # ==============================
    @commands.command()
    @commands.has_permissions(manage_roles=True)
    async def unmute(self, ctx, member: discord.Member = None):
        mute_role = ctx.guild.get_role(MUTE_ROLE_ID)
        if not member or not mute_role:
            return await ctx.send("⚠️ Uso: `$unmute @usuario`.")

        await member.remove_roles(mute_role)
        case = next_case("unmute", member.id, ctx.author.id, "Unmute manual")
        embed = discord.Embed(
            title="🔊 Usuario desmuteado",
            description=f"{member.mention} fue desmuteado.\n📂 Case #{case['id']}",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
        await self.log_action(ctx, case, "🔊 Usuario desmuteado", discord.Color.green())

    # ==============================
    # ⏳ Timeout
    # ==============================
    @commands.command()
    @commands.has_permissions(moderate_members=True)
    async def timeout(self, ctx, member: discord.Member = None, minutes: int = None, *, reason="No especificado"):
        if not member or not minutes:
            return await ctx.send("⚠️ Uso: `$timeout @usuario <minutos> [razón]`")

        until = datetime.now(timezone.utc) + timedelta(minutes=minutes)
        await member.timeout(until, reason=reason)
        case = next_case("timeout", member.id, ctx.author.id, reason)
        embed = discord.Embed(
            title="⏳ Timeout aplicado",
            description=f"{member.mention} fue silenciado {minutes}m.\n📂 Case #{case['id']}",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)
        await self.log_action(ctx, case, "⏳ Timeout aplicado", discord.Color.blue())

    # ==============================
    # 🔓 Remove Timeout
    # ==============================
    @commands.command()
    @commands.has_permissions(moderate_members=True)
    async def remove_timeout(self, ctx, member: discord.Member = None):
        if not member:
            return await ctx.send("⚠️ Uso: `$remove_timeout @usuario`")

        await member.timeout(None)
        case = next_case("remove_timeout", member.id, ctx.author.id, "Remove timeout")
        embed = discord.Embed(
            title="🔓 Timeout removido",
            description=f"{member.mention} puede hablar de nuevo.\n📂 Case #{case['id']}",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
        await self.log_action(ctx, case, "🔓 Timeout removido", discord.Color.green())

    # ==============================
    # 🧹 Purge (alias: clear, c)
    # ==============================
    @commands.command(aliases=["purge", "c"])
    @commands.has_permissions(manage_messages=True)
    async def clear(self, ctx, amount: int = None):
        if not amount or amount < 1:
            return await ctx.send(embed=discord.Embed(
                title="❌ Uso incorrecto",
                description="Formato correcto:\n`$clear <cantidad>`\nEjemplo: `$clear 10`",
                color=discord.Color.red()
            ))

        deleted = await ctx.channel.purge(limit=amount + 1)
        case = next_case("purge", ctx.author.id, ctx.author.id, f"Purge de {amount} mensajes en #{ctx.channel.name}")

        confirm = discord.Embed(
            title="🧹 Purge realizado",
            description=(
                f"👤 Moderador: {ctx.author.mention}\n"
                f"🗑️ Se eliminaron **{len(deleted)-1}** mensajes en {ctx.channel.mention}.\n"
                f"📂 Case #{case['id']}"
            ),
            color=discord.Color.blurple(),
            timestamp=datetime.now(timezone.utc)
        )
        await ctx.send(embed=confirm, delete_after=3)

        await self.log_action(
            ctx,
            case,
            "🧹 Purge realizado",
            discord.Color.blurple(),
            extra=f"Canal: {ctx.channel.mention}\nMensajes: {len(deleted)-1}"
        )

    # ==============================
    # ⚠️ Warn System
    # ==============================
    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def warn(self, ctx, member: discord.Member = None, *, reason="No especificado"):
        if not member:
            return await ctx.send("⚠️ Uso: `$warn @usuario [razón]`")

        data = load_json(WARNS_FILE, {})
        user_id = str(member.id)
        if user_id not in data:
            data[user_id] = []
        warn_entry = {
            "reason": reason,
            "moderator": ctx.author.id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        data[user_id].append(warn_entry)
        save_json(WARNS_FILE, data)

        case = next_case("warn", member.id, ctx.author.id, reason)
        embed = discord.Embed(
            title="⚠️ Usuario advertido",
            description=f"{member.mention} recibió un warn.\n**Razón:** {reason}\n📂 Case #{case['id']}",
            color=discord.Color.yellow()
        )
        await ctx.send(embed=embed)
        await self.log_action(ctx, case, "⚠️ Warn aplicado", discord.Color.yellow())

    @commands.command()
    async def warns(self, ctx, member: discord.Member = None):
        if not member:
            member = ctx.author
        data = load_json(WARNS_FILE, {})
        warns = data.get(str(member.id), [])

        if not warns:
            return await ctx.send(f"✅ {member.mention} no tiene warns.")

        embed = discord.Embed(
            title=f"📋 Warns de {member}",
            color=discord.Color.orange()
        )
        for i, warn in enumerate(warns, 1):
            mod = f"<@{warn['moderator']}>"
            embed.add_field(
                name=f"#{i} - {warn['reason']}",
                value=f"👮 Moderador: {mod}\n📅 {warn['timestamp']}",
                inline=False
            )
        await ctx.send(embed=embed)

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def clearwarns(self, ctx, member: discord.Member = None):
        if not member:
            return await ctx.send("⚠️ Uso: `$clearwarns @usuario`")

        data = load_json(WARNS_FILE, {})
        if str(member.id) in data:
            data[str(member.id)] = []
            save_json(WARNS_FILE, data)

        case = next_case("clearwarns", member.id, ctx.author.id, "Warns limpiados")
        embed = discord.Embed(
            title="🧹 Warns eliminados",
            description=f"Todos los warns de {member.mention} fueron eliminados.\n📂 Case #{case['id']}",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
        await self.log_action(ctx, case, "🧹 Warns eliminados", discord.Color.green())

    @commands.command()
    async def listwarns(self, ctx):
        data = load_json(WARNS_FILE, {})
        if not data:
            return await ctx.send("✅ Nadie tiene warns.")

        embed = discord.Embed(
            title="📋 Lista de usuarios con warns",
            color=discord.Color.gold()
        )
        for user_id, warns in data.items():
            if warns:
                user = await self.bot.fetch_user(int(user_id))
                embed.add_field(
                    name=f"{user} ({user_id})",
                    value=f"Warns: {len(warns)}",
                    inline=False
                )
        await ctx.send(embed=embed)

    # ==============================
    # 📖 HelpModeration
    # ==============================

    @commands.command(name="helpmoderation", aliases=["helpmod", "hmod"])
    async def helpmoderation(self, ctx):
        # ========================
        # 📄 Páginas del Help
        # ========================
        pages = [
            discord.Embed(
                title="📖 Ayuda de Moderación - Página 1",
                description="**Comandos básicos de moderación.**",
                color=discord.Color.blue()
            )
            .add_field(name="🔨 Ban", value="`$ban <usuario> [razón]`\nBanea a un usuario del servidor.", inline=False)
            .add_field(name="⚡ Kick", value="`$kick <usuario> [razón]`\nExpulsa a un usuario del servidor.", inline=False)
            .add_field(name="⏳ Timeout", value="`$timeout <usuario> <tiempo> [razón]`\nSilencia temporalmente a un usuario.", inline=False)
            .set_footer(text="Página 1/3"),

            discord.Embed(
                title="📖 Ayuda de Moderación - Página 2",
                description="**Sistema de warns y control.**",
                color=discord.Color.orange()
            )
            .add_field(name="⚠️ Warn", value="`$warn <usuario> [razón]`\nDa un aviso a un usuario.", inline=False)
            .add_field(name="📋 Warns", value="`$warns <usuario>`\nMuestra la lista de advertencias de un usuario.", inline=False)
            .add_field(name="🧹 Clearwarns", value="`$clearwarns <usuario>`\nElimina todas las advertencias de un usuario.", inline=False)
            .set_footer(text="Página 2/3"),

            discord.Embed(
                title="📖 Ayuda de Moderación - Página 3",
                description="**Comandos de limpieza y control avanzado.**",
                color=discord.Color.green()
            )
            .add_field(name="🧼 Clear/Purge", value="`$clear <número>` o `$c <número>`\nElimina mensajes en masa (máx. 100).", inline=False)
            .add_field(name="🗃️ Casos", value="Cada acción tiene un **Case ID** único, para rastrear sanciones.", inline=False)
            .add_field(name="📌 Logs", value="Todas las acciones se envían a un canal de logs definido por el bot.", inline=False)
            .set_footer(text="Página 3/3"),
        ]

        # ========================
        # 📌 Sistema de Botones
        # ========================
        class Paginator(View):
            def __init__(self):
                super().__init__(timeout=60)
                self.current = 0

            async def update(self, interaction):
                await interaction.response.edit_message(embed=pages[self.current], view=self)

            @discord.ui.button(label="⬅️ Atrás", style=discord.ButtonStyle.primary)
            async def previous(self, interaction: discord.Interaction, button: Button):
                if self.current > 0:
                    self.current -= 1
                    await self.update(interaction)

            @discord.ui.button(label="➡️ Siguiente", style=discord.ButtonStyle.primary)
            async def next(self, interaction: discord.Interaction, button: Button):
                if self.current < len(pages) - 1:
                    self.current += 1
                    await self.update(interaction)

        # ========================
        # 📌 Enviar el primer embed
        # ========================
        await ctx.send(embed=pages[0], view=Paginator())

async def setup(bot):
    await bot.add_cog(HelpModeration(bot))


# ==============================
# Setup
# ==============================
async def setup(bot):
    await bot.add_cog(Moderation(bot))

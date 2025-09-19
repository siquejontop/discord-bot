import discord
from discord.ext import commands
from datetime import datetime, timedelta, timezone
from discord.ui import View, Button
import os
import logging
import re

# ==============================
# CONFIG LOCAL
# ==============================
MUTE_ROLE_ID = 1418314510049083576
LIMIT_ROLE_ID = 1415860204624416971
LOG_CHANNEL_ID = 1418314310739955742
OWNER_IDS = [335596693603090434, 523662219020337153]  # IDs de dueños del bot

# ==============================
# HELPERS
# ==============================
logging.basicConfig(level=logging.INFO)

# ==============================
# Moderation Cog
# ==============================
class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.warnings = {}  # {user_id: list of warnings}

    # ==============================
    # 📌 Helpers
    # ==============================
    def has_permission(self, ctx):
        limit_role = ctx.guild.get_role(LIMIT_ROLE_ID)
        return (
            ctx.author.id in OWNER_IDS
            or ctx.author == ctx.guild.owner
            or (not limit_role or ctx.author.top_role > limit_role)
        )

    async def log_action(self, ctx, title, color, extra=""):
        log_channel = ctx.guild.get_channel(LOG_CHANNEL_ID)
        if not log_channel:
            return
        embed = discord.Embed(
            title=title,
            color=color,
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="👤 Usuario", value=ctx.author.mention, inline=False)
        embed.add_field(name="🛠️ Moderador", value=ctx.author.mention, inline=False)
        if extra:
            embed.add_field(name="📌 Extra", value=extra, inline=False)
        await log_channel.send(embed=embed)

    def parse_duration(self, duration_str):
        """Parsea una duración en formato '5s', '10m', '7d', '2w' a timedelta."""
        match = re.match(r'^(\d+)([smhdw])$', duration_str.lower())
        if not match:
            return None
        value, unit = int(match.group(1)), match.group(2)
        if unit == 's':
            return timedelta(seconds=value)
        elif unit == 'm':
            return timedelta(minutes=value)
        elif unit == 'h':
            return timedelta(hours=value)
        elif unit == 'd':
            return timedelta(days=value)
        elif unit == 'w':
            return timedelta(weeks=value)
        return None

    # ==============================
    # 🧹 Purge (alias: clear, c)
    # ==============================
    @commands.command(aliases=["purge", "c"])
    @commands.has_permissions(manage_messages=True)
    async def clear(self, ctx, amount: int = None):
        if not amount or amount < 1 or amount > 100 or not self.has_permission(ctx):
            return await ctx.send(embed=discord.Embed(
                title="❌ Uso incorrecto",
                description="Formato correcto:\n`$clear <cantidad>` (máx. 100)\nEjemplo: `$clear 10`",
                color=discord.Color.red()
            ))
        try:
            deleted = await ctx.channel.purge(limit=amount + 1)
            confirm = discord.Embed(
                title="🧹 Purge realizado",
                description=(
                    f"👤 Moderador: {ctx.author.mention}\n"
                    f"🗑️ Se eliminaron **{len(deleted)-1}** mensajes en {ctx.channel.mention}."
                ),
                color=discord.Color.blurple(),
                timestamp=datetime.now(timezone.utc)
            )
            await ctx.send(embed=confirm, delete_after=3)
            await self.log_action(
                ctx,
                "🧹 Purge realizado",
                discord.Color.blurple(),
                extra=f"Canal: {ctx.channel.mention}\nMensajes: {len(deleted)-1}"
            )
        except discord.Forbidden:
            await ctx.send("❌ No tengo permisos para eliminar mensajes.")
        except discord.HTTPException as e:
            await ctx.send(f"❌ Error al purgar: {e}")

    # ==============================
    # 🧹 Clearuser
    # ==============================
    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def clearuser(self, ctx, member: discord.Member, amount: int = None):
        if not amount or amount < 1 or amount > 100 or not self.has_permission(ctx):
            return await ctx.send(embed=discord.Embed(
                title="❌ Uso incorrecto",
                description="Formato correcto:\n`$clearuser @usuario <cantidad>` (máx. 100)",
                color=discord.Color.red()
            ))
        def is_member_message(m):
            return m.author == member
        try:
            deleted = await ctx.channel.purge(limit=amount + 1, check=is_member_message)
            confirm = discord.Embed(
                title="🧹 Mensajes eliminados",
                description=f"Se eliminaron **{len(deleted)-1}** mensajes de {member.mention} en {ctx.channel.mention}.",
                color=discord.Color.blurple(),
                timestamp=datetime.now(timezone.utc)
            )
            await ctx.send(embed=confirm, delete_after=3)
            await self.log_action(
                ctx,
                "🧹 Mensajes eliminados",
                discord.Color.blurple(),
                extra=f"Usuario: {member.mention}\nMensajes: {len(deleted)-1}"
            )
        except discord.Forbidden:
            await ctx.send("❌ No tengo permisos para eliminar mensajes.")
        except discord.HTTPException as e:
            await ctx.send(f"❌ Error al purgar: {e}")

    # ==============================
    # 🔇 Mute
    # ==============================
    @commands.command()
    @commands.has_permissions(manage_roles=True)
    async def mute(self, ctx, member: discord.Member = None, duration: str = None, *, reason="No especificado"):
        mute_role = ctx.guild.get_role(MUTE_ROLE_ID)
        if not member or not mute_role or not self.has_permission(ctx):
            return await ctx.send("⚠️ Uso: `$mute @usuario [duración(s/m/h/d/w)] [razón]` (ej. 5m)")
        duration_timedelta = None
        if duration:
            duration_timedelta = self.parse_duration(duration)
            if not duration_timedelta:
                return await ctx.send("⚠️ Duración inválida. Usa formato: 5s, 10m, 7d, 2w (segundos, minutos, días, semanas).")
        await member.add_roles(mute_role, reason=reason)
        embed = discord.Embed(
            title="🔇 Usuario muteado",
            description=f"{member.mention} fue muteado.\n**Razón:** {reason}"
            f"{f'\n⏳ Duración: {duration}' if duration else ''}",
            color=discord.Color.dark_gray()
        )
        await ctx.send(embed=embed)
        await self.log_action(ctx, "🔇 Usuario muteado", discord.Color.dark_gray())

    # ==============================
    # 🔊 Unmute
    # ==============================
    @commands.command()
    @commands.has_permissions(manage_roles=True)
    async def unmute(self, ctx, member: discord.Member = None):
        mute_role = ctx.guild.get_role(MUTE_ROLE_ID)
        if not member or not mute_role or not self.has_permission(ctx):
            return await ctx.send("⚠️ Uso: `$unmute @usuario`.")
        await member.remove_roles(mute_role)
        embed = discord.Embed(
            title="🔊 Usuario desmuteado",
            description=f"{member.mention} fue desmuteado.",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
        await self.log_action(ctx, "🔊 Usuario desmuteado", discord.Color.green())

    # ==============================
    # ⏳ Timeout
    # ==============================
    @commands.command()
    @commands.has_permissions(moderate_members=True)
    async def timeout(self, ctx, member: discord.Member = None, duration: str = None, *, reason="No especificado"):
        if not member or not self.has_permission(ctx):
            return await ctx.send("⚠️ Uso: `$timeout @usuario <duración(s/m/h/d/w)> [razón]` (ej. 5m, máx. 28 días)")
        if not duration:
            return await ctx.send("⚠️ Debes especificar una duración (ej. 5s, 10m, 7d, 2w).")
        duration_timedelta = self.parse_duration(duration)
        if not duration_timedelta:
            return await ctx.send("⚠️ Duración inválida. Usa formato: 5s, 10m, 7d, 2w (segundos, minutos, días, semanas).")
        # Límite de 28 días
        if duration_timedelta > timedelta(days=28):
            return await ctx.send("⚠️ El timeout no puede exceder 28 días.")
        until = datetime.now(timezone.utc) + duration_timedelta
        await member.timeout(until, reason=reason)
        embed = discord.Embed(
            title="⏳ Timeout aplicado",
            description=f"{member.mention} fue silenciado {duration}.\n**Razón:** {reason}",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)
        await self.log_action(ctx, "⏳ Timeout aplicado", discord.Color.blue())

    # ==============================
    # 🔓 Remove Timeout
    # ==============================
    @commands.command()
    @commands.has_permissions(moderate_members=True)
    async def remove_timeout(self, ctx, member: discord.Member = None):
        if not member or not self.has_permission(ctx):
            return await ctx.send("⚠️ Uso: `$remove_timeout @usuario`")
        await member.timeout(None)
        embed = discord.Embed(
            title="🔓 Timeout removido",
            description=f"{member.mention} puede hablar de nuevo.",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
        await self.log_action(ctx, "🔓 Timeout removido", discord.Color.green())

    # ==============================
    # 🔒 Lock
    # ==============================
    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def lock(self, ctx):
        overwrite = ctx.channel.overwrites_for(ctx.guild.default_role)
        overwrite.send_messages = False
        await ctx.channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
        embed = discord.Embed(title="🔒 Canal bloqueado", description=f"{ctx.channel.mention} ha sido bloqueado.", color=discord.Color.red())
        await ctx.send(embed=embed)
        await self.log_action(ctx, "🔒 Canal bloqueado", discord.Color.red(), extra=f"Canal: {ctx.channel.mention}")

    # ==============================
    # 🔓 Unlock
    # ==============================
    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def unlock(self, ctx):
        overwrite = ctx.channel.overwrites_for(ctx.guild.default_role)
        overwrite.send_messages = None
        await ctx.channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
        embed = discord.Embed(title="🔓 Canal desbloqueado", description=f"{ctx.channel.mention} ha sido desbloqueado.", color=discord.Color.green())
        await ctx.send(embed=embed)
        await self.log_action(ctx, "🔓 Canal desbloqueado", discord.Color.green(), extra=f"Canal: {ctx.channel.mention}")

    # ==============================
    # ⚠️ Warn
    # ==============================
    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def warn(self, ctx, member: discord.Member, *, reason="No especificado"):
        if not self.has_permission(ctx):
            return await ctx.send("⚠️ No tienes permisos para advertir usuarios.")
        if member == ctx.author:
            return await ctx.send("⚠️ No puedes advertirte a ti mismo.")
        user_id = str(member.id)
        if user_id not in self.warnings:
            self.warnings[user_id] = []
        self.warnings[user_id].append({"reason": reason, "moderator": ctx.author.id, "timestamp": datetime.now(timezone.utc)})
        embed = discord.Embed(
            title="⚠️ Advertencia",
            description=f"{member.mention} ha sido advertido.\n**Razón:** {reason}",
            color=discord.Color.yellow(),
            timestamp=datetime.now(timezone.utc)
        )
        await ctx.send(embed=embed)
        await self.log_action(ctx, "⚠️ Advertencia", discord.Color.yellow(), extra=f"Usuario: {member.mention}\nRazón: {reason}")
        if len(self.warnings[user_id]) >= 3:  # Límite de 3 advertencias
            mute_role = ctx.guild.get_role(MUTE_ROLE_ID)
            if mute_role:
                await member.add_roles(mute_role, reason=f"Alcanzó 3 advertencias por {reason}")
                embed = discord.Embed(
                    title="🔇 Mute automático",
                    description=f"{member.mention} fue muteado automáticamente por alcanzar 3 advertencias.",
                    color=discord.Color.dark_gray()
                )
                await ctx.send(embed=embed)
                await self.log_action(ctx, "🔇 Mute automático", discord.Color.dark_gray(), extra=f"Usuario: {member.mention}")

    # ==============================
    # 📋 Warnings
    # ==============================
    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def warnings(self, ctx, member: discord.Member = None):
        if not self.has_permission(ctx):
            return await ctx.send("⚠️ No tienes permisos para ver advertencias.")
        target = member or ctx.author
        user_id = str(target.id)
        if user_id not in self.warnings or not self.warnings[user_id]:
            await ctx.send(f"📋 {target.mention} no tiene advertencias.")
            return
        embed = discord.Embed(
            title=f"📋 Advertencias de {target.name}",
            color=discord.Color.orange(),
            timestamp=datetime.now(timezone.utc)
        )
        for i, warning in enumerate(self.warnings[user_id], 1):
            embed.add_field(
                name=f"Advertencia #{i}",
                value=f"Razón: {warning['reason']}\nModerador: <@{warning['moderator']}>\nFecha: {warning['timestamp'].strftime('%Y-%m-%d %H:%M:%S UTC')}",
                inline=False
            )
        await ctx.send(embed=embed)

    # ==============================
    # 🔧 Unwarn
    # ==============================
    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def unwarn(self, ctx, member: discord.Member, index: int):
        if not self.has_permission(ctx):
            return await ctx.send("⚠️ No tienes permisos para remover advertencias.")
        if member == ctx.author:
            return await ctx.send("⚠️ No puedes remover tus propias advertencias.")
        user_id = str(member.id)
        if user_id not in self.warnings or not self.warnings[user_id]:
            await ctx.send(f"📋 {member.mention} no tiene advertencias para remover.")
            return
        if index < 1 or index > len(self.warnings[user_id]):
            await ctx.send(f"⚠️ Índice inválido. Usa un número entre 1 y {len(self.warnings[user_id])}.")
            return
        removed_warning = self.warnings[user_id].pop(index - 1)
        embed = discord.Embed(
            title="🔧 Advertencia removida",
            description=f"Se removió la advertencia #{index} de {member.mention}.\n**Razón original:** {removed_warning['reason']}",
            color=discord.Color.green(),
            timestamp=datetime.now(timezone.utc)
        )
        await ctx.send(embed=embed)
        await self.log_action(ctx, "🔧 Advertencia removida", discord.Color.green(), extra=f"Usuario: {member.mention}\nÍndice: {index}")

    # ==============================
    # 👢 Kick
    # ==============================
    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason="No especificado"):
        if not self.has_permission(ctx):
            return await ctx.send("⚠️ No tienes permisos para expulsar usuarios.")
        if member == ctx.author:
            return await ctx.send("⚠️ No puedes expulsarte a ti mismo.")
        await member.kick(reason=reason)
        embed = discord.Embed(
            title="👢 Usuario expulsado",
            description=f"{member.mention} fue expulsado.\n**Razón:** {reason}",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)
        await self.log_action(ctx, "👢 Usuario expulsado", discord.Color.orange(), extra=f"Usuario: {member.mention}\nRazón: {reason}")

    # ==============================
    # 🚫 Ban
    # ==============================
    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member, *, reason="No especificado"):
        if not self.has_permission(ctx):
            return await ctx.send("⚠️ No tienes permisos para banear usuarios.")
        if member == ctx.author:
            return await ctx.send("⚠️ No puedes banearte a ti mismo.")
        await member.ban(reason=reason)
        embed = discord.Embed(
            title="🚫 Usuario baneado",
            description=f"{member.mention} fue baneado.\n**Razón:** {reason}",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        await self.log_action(ctx, "🚫 Usuario baneado", discord.Color.red(), extra=f"Usuario: {member.mention}\nRazón: {reason}")

    # ==============================
    # 🔓 Unban
    # ==============================
    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx, user: discord.User, *, reason="No especificado"):
        if not self.has_permission(ctx):
            return await ctx.send("⚠️ No tienes permisos para desbanear usuarios.")
        await ctx.guild.unban(user, reason=reason)
        embed = discord.Embed(
            title="🔓 Usuario desbaneado",
            description=f"{user.mention} fue desbaneado.\n**Razón:** {reason}",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
        await self.log_action(ctx, "🔓 Usuario desbaneado", discord.Color.green(), extra=f"Usuario: {user.mention}\nRazón: {reason}")

    # ==============================
    # 📖 HelpModeration
    # ==============================
    @commands.command(name="helpmoderation", aliases=["helpmod", "hmod"])
    async def helpmoderation(self, ctx):
        pages = [
            discord.Embed(
                title="Ayuda de Moderación",
                description="**Comandos de limpieza y control.**",
                color=discord.Color.blue()
            )
            .add_field(name="🧼 Clear/Purge", value="`$clear <número>` o `$purge <número>` o `$c <número>`\nElimina mensajes en masa (máx. 100).", inline=False)
            .add_field(name="🧹 Clearuser", value="`$clearuser @usuario <cantidad>`\nElimina mensajes de un usuario específico (máx. 100).", inline=False)
            .add_field(name="🔇 Mute", value="`$mute <usuario> [duración(s/m/h/d/w)] [razón]`\nSilencia a un usuario (ej. 5m).", inline=False)
            .add_field(name="⏳ Timeout", value="`$timeout <usuario> <duración(s/m/h/d/w)> [razón]`\nSilencia temporalmente a un usuario (máx. 28 días).", inline=False)
            .set_footer(text="Página 1/3"),

            discord.Embed(
                title="Ayuda de Moderación",
                description="**Comandos adicionales.**",
                color=discord.Color.green()
            )
            .add_field(name="🔊 Unmute", value="`$unmute <usuario>`\nDesmuta a un usuario.", inline=False)
            .add_field(name="🔓 Remove Timeout", value="`$remove_timeout <usuario>`\nRemueve el timeout de un usuario.", inline=False)
            .add_field(name="🔒 Lock", value="`$lock`\nBloquea el canal para @everyone.", inline=False)
            .add_field(name="🔓 Unlock", value="`$unlock`\nDesbloquea el canal para @everyone.", inline=False)
            .add_field(name="⚠️ Warn", value="`$warn @usuario [razón]`\nAdvertir a un usuario (máx. 3 antes de mute).", inline=False)
            .set_footer(text="Página 2/3"),

            discord.Embed(
                title="Ayuda de Moderación",
                description="**Comandos de gestión.**",
                color=discord.Color.purple()
            )
            .add_field(name="📋 Warnings", value="`$warnings [@usuario]`\nMuestra las advertencias de un usuario.", inline=False)
            .add_field(name="🔧 Unwarn", value="`$unwarn @usuario <índice>`\nRemueve una advertencia específica (usa $warnings para ver índices).", inline=False)
            .add_field(name="👢 Kick", value="`$kick @usuario [razón]`\nExpulsa a un usuario del servidor.", inline=False)
            .add_field(name="🚫 Ban", value="`$ban @usuario [razón]`\nBanea a un usuario del servidor.", inline=False)
            .add_field(name="🔓 Unban", value="`$unban @usuario [razón]`\nDesbanea a un usuario del servidor.", inline=False)

            .set_footer(text="Página 3/3"),
            )
        ]

        class Paginator(View):
            def __init__(self):
                super().__init__(timeout=300)
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

            @discord.ui.button(label="🚪 Salir", style=discord.ButtonStyle.danger)
            async def exit(self, interaction: discord.Interaction, button: Button):
                await interaction.message.delete()
                self.stop()

        await ctx.send(embed=pages[0], view=Paginator())

# ==============================
# Setup
# ==============================
async def setup(bot):
    await bot.add_cog(Moderation(bot))

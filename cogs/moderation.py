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
    # 📖 HelpModeration
    # ==============================
    @commands.command(name="helpmoderation", aliases=["helpmod", "hmod"])
    async def helpmoderation(self, ctx):
        pages = [
            discord.Embed(
                title="📖 Ayuda de Moderación - Página 1",
                description="**Comandos de limpieza y control.**",
                color=discord.Color.blue()
            )
            .add_field(name="🧼 Clear/Purge", value="`$clear <número>` o `$purge <número>` o `$c <número>`\nElimina mensajes en masa (máx. 100).", inline=False)
            .add_field(name="🧹 Clearuser", value="`$clearuser @usuario <cantidad>`\nElimina mensajes de un usuario específico (máx. 100).", inline=False)
            .add_field(name="🔇 Mute", value="`$mute <usuario> [duración(s/m/h/d/w)] [razón]`\nSilencia a un usuario (ej. 5m).", inline=False)
            .add_field(name="⏳ Timeout", value="`$timeout <usuario> <duración(s/m/h/d/w)> [razón]`\nSilencia temporalmente a un usuario (máx. 28 días).", inline=False)
            .set_footer(text="Página 1/2"),

            discord.Embed(
                title="📖 Ayuda de Moderación - Página 2",
                description="**Comandos adicionales.**",
                color=discord.Color.green()
            )
            .add_field(name="🔊 Unmute", value="`$unmute <usuario>`\nDesmuta a un usuario.", inline=False)
            .add_field(name="🔓 Remove Timeout", value="`$remove_timeout <usuario>`\nRemueve el timeout de un usuario.", inline=False)
            .add_field(name="🔒 Lock", value="`$lock`\nBloquea el canal para @everyone.", inline=False)
            .add_field(name="🔓 Unlock", value="`$unlock`\nDesbloquea el canal para @everyone.", inline=False)
            .set_footer(text="Página 2/2"),    
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

import discord
from discord.ext import commands
from discord import utils
from config import MUTE_ROLE_ID, LIMIT_ROLE_ID
from datetime import datetime, timedelta, timezone

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # =====================================================
    # 📌 Helper: verificar rol suficiente
    # =====================================================
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

        await member.ban(reason=reason)
        embed = discord.Embed(
            title="⛔ Usuario baneado",
            description=f"{member.mention} fue baneado.\n**Razón:** {reason}",
            color=discord.Color.red(),
            timestamp=datetime.now(timezone.utc)
        )
        await ctx.send(embed=embed)

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
        await ctx.guild.unban(user)
        embed = discord.Embed(
            title="✅ Usuario desbaneado",
            description=f"{user.mention} fue desbaneado.",
            color=discord.Color.green(),
            timestamp=datetime.now(timezone.utc)
        )
        await ctx.send(embed=embed)

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

        await member.kick(reason=reason)
        embed = discord.Embed(
            title="⚠️ Usuario expulsado",
            description=f"{member.mention} fue expulsado.\n**Razón:** {reason}",
            color=discord.Color.orange(),
            timestamp=datetime.now(timezone.utc)
        )
        await ctx.send(embed=embed)

    # =====================================================
    # 🤐 Mute
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
            embed = discord.Embed(
                title="🔇 Usuario muteado",
                description=f"{member.mention} fue muteado.\n**Razón:** {reason}",
                color=discord.Color.dark_gray(),
                timestamp=datetime.now(timezone.utc)
            )
            await ctx.send(embed=embed)
        else:
            await ctx.send("⚠️ No se encontró el rol de mute configurado.")

    # =====================================================
    # 🔊 Unmute
    # =====================================================
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
            embed = discord.Embed(
                title="🔊 Usuario desmuteado",
                description=f"{member.mention} fue desmuteado.",
                color=discord.Color.green(),
                timestamp=datetime.now(timezone.utc)
            )
            await ctx.send(embed=embed)
        else:
            await ctx.send("⚠️ Ese usuario no estaba muteado.")

    # =====================================================
    # 🧹 Purge (alias: clear)
    # =====================================================
    @commands.command(aliases=["purge","c","p"])
    @commands.has_permissions(manage_messages=True)
    async def clear(self, ctx, amount: int = None):
        """
        Borra mensajes en el canal. Uso: $purge <cantidad>
        (El comando también acepta el alias $clear si quieres)
        """
        if amount is None:
            embed = discord.Embed(
                title="❌ Uso incorrecto de purge",
                description="Formato correcto:\n`$purge <cantidad>`\nEjemplo: `$purge 10`",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return

        if amount < 1:
            embed = discord.Embed(
                title="❌ Uso incorrecto de purge",
                description="La cantidad debe ser un número mayor a 0.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return

        # Borramos amount mensajes + 1 (el comando)
        deleted = await ctx.channel.purge(limit=amount + 1)

        embed = discord.Embed(
            title="🧹 Purge realizado",
            description=f"Se eliminaron **{len(deleted)-1}** mensajes en {ctx.channel.mention}.",
            color=discord.Color.blurple(),
            timestamp=datetime.now(timezone.utc)
        )
        # Enviamos la confirmación y la borramos automáticamente
        await ctx.send(embed=embed, delete_after=5)

        # (Opcional) loguear en canal de logs si tienes función get_log_channel
        try:
            log = get_log_channel(ctx.guild)  # si tienes esa función disponible en el módulo
            if log:
                await log.send(embed=embed)
        except Exception:
            pass

    # =====================================================
    # 👁️ Slowmode
    # =====================================================
    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def slowmode(self, ctx, seconds: int = None):
        if seconds is None:
            embed = discord.Embed(
                title="❌ Uso incorrecto de slowmode",
                description="Formato correcto:\n`$slowmode <segundos>`\nPon `0` para desactivarlo.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return

        await ctx.channel.edit(slowmode_delay=seconds)
        if seconds == 0:
            await ctx.send("✅ Slowmode desactivado en este canal.")
        else:
            await ctx.send(f"⏳ Slowmode activado: **{seconds} segundos**.")

    # =====================================================
    # ⏳ Timeout
    # =====================================================
    @commands.command()
    @commands.has_permissions(moderate_members=True)
    async def timeout(self, ctx, member: discord.Member = None, minutes: int = None, *, reason="No se especificó razón"):
        if not self.has_permission(ctx):
            return await ctx.send(embed=self.permission_embed(ctx, "dar timeout"))

        if member is None or minutes is None:
            embed = discord.Embed(
                title="❌ Uso incorrecto de timeout",
                description="Formato correcto:\n`$timeout @usuario <minutos> [razón]`",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return

        until = datetime.now(timezone.utc) + timedelta(minutes=minutes)
        await member.timeout(until, reason=reason)
        embed = discord.Embed(
            title="⏳ Usuario en timeout",
            description=f"{member.mention} fue silenciado durante **{minutes} minutos**.\n**Razón:** {reason}",
            color=discord.Color.blue(),
            timestamp=datetime.now(timezone.utc)
        )
        await ctx.send(embed=embed)

    # =====================================================
    # 🔓 Quitar timeout
    # =====================================================
    @commands.command()
    @commands.has_permissions(moderate_members=True)
    async def remove_timeout(self, ctx, member: discord.Member = None):
        if not self.has_permission(ctx):
            return await ctx.send(embed=self.permission_embed(ctx, "quitar timeout"))

        if member is None:
            embed = discord.Embed(
                title="❌ Uso incorrecto de remove_timeout",
                description="Formato correcto:\n`$remove_timeout @usuario`",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return

        await member.timeout(None)
        embed = discord.Embed(
            title="🔓 Timeout removido",
            description=f"{member.mention} ya puede hablar de nuevo.",
            color=discord.Color.green(),
            timestamp=datetime.now(timezone.utc)
        )
        await ctx.send(embed=embed)

    # =====================================================
    # 🔒 Lock
    # =====================================================
    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def lock(self, ctx):
        if not self.has_permission(ctx):
            return await ctx.send(embed=self.permission_embed(ctx, "bloquear el canal"))

        overwrite = ctx.channel.overwrites_for(ctx.guild.default_role)
        overwrite.send_messages = False
        await ctx.channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)

        embed = discord.Embed(
            title="🔒 Canal bloqueado",
            description=f"{ctx.channel.mention} ha sido bloqueado.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)

    # =====================================================
    # 🔓 Unlock
    # =====================================================
    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def unlock(self, ctx):
        if not self.has_permission(ctx):
            return await ctx.send(embed=self.permission_embed(ctx, "desbloquear el canal"))

        overwrite = ctx.channel.overwrites_for(ctx.guild.default_role)
        overwrite.send_messages = True
        await ctx.channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)

        embed = discord.Embed(
            title="🔓 Canal desbloqueado",
            description=f"{ctx.channel.mention} ha sido desbloqueado.",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

# =====================================================
# 🔌 Setup obligatorio
# =====================================================
async def setup(bot):
    await bot.add_cog(Moderation(bot))

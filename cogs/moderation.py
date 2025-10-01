# moderation.py
import discord
from discord.ext import commands
from discord.ui import View, Button
from datetime import datetime, timedelta, timezone
import asyncio
import re
import logging
from typing import Optional

# ==============================
# CONFIG LOCAL
# ==============================
MUTE_ROLE_ID = 1418314510049083556  # cambia si hace falta
LIMIT_ROLE_ID = 1415860204624416971
LOG_CHANNEL_ID = 1418314310739955742
OWNER_IDS = [335596693603090434, 523662219020337153]  # IDs con poder absoluto

# ==============================
# HELPERS
# ==============================
logging.basicConfig(level=logging.INFO)
UTC = timezone.utc


class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # warnings: dict[user_id_str] = list of dicts {reason, moderator, timestamp}
        self.warnings = {}

    # ------------------------------
    # Helpers internos
    # ------------------------------
    def is_owner_or_bot_owner(self, ctx: commands.Context, user: discord.abc.Snowflake) -> bool:
        """True si user es uno de los OWNER_IDS o el owner del guild."""
        try:
            uid = int(getattr(user, "id", user))
        except Exception:
            return False
        if uid in OWNER_IDS:
            return True
        if ctx.guild and ctx.guild.owner and ctx.guild.owner.id == uid:
            return True
        return False

    def has_permission(self, ctx: commands.Context) -> bool:
        """
        Comprueba si el autor tiene permiso según LIMIT_ROLE_ID o es owner.
        Returns True si autor está en OWNER_IDS o es owner del servidor,
        o si no existe LIMIT_ROLE_ID o su top_role es > role_limit.
        """
        author = ctx.author
        if author.id in OWNER_IDS:
            return True
        if ctx.guild and author == ctx.guild.owner:
            return True

        limit_role = None
        if ctx.guild:
            limit_role = ctx.guild.get_role(LIMIT_ROLE_ID)
        # si no hay rol limit, permitir
        if not limit_role:
            return True
        # comparar jerarquía del autor vs role limit
        try:
            return author.top_role > limit_role
        except Exception:
            return False

    def check_hierarchy(self, ctx: commands.Context, target_member: discord.Member) -> (bool, str):
        """
        Verifica que:
         - target_member no sea el autor (evita auto-sanciones),
         - autor tenga rol mayor que target_member (a menos que sea owner/OWNER_IDS),
         - y que el bot tenga rol mayor que target_member.
        Devuelve (True, "") si pasa, else (False, "motivo").
        """
        if not ctx.guild:
            return False, "Comando solo en servidor."

        author = ctx.author

        # No te puedes sancionar a ti mismo
        if target_member.id == author.id:
            return False, "❌ No puedes aplicarte esa acción a ti mismo."

        # No puedes sancionar al owner del servidor ni a OWNER_IDS (salvo si eres owner o OWNER_IDS)
        if self.is_owner_or_bot_owner(ctx, target_member):
            if author.id in OWNER_IDS or (ctx.guild and author == ctx.guild.owner):
                # autor es owner absoluto -> allow
                pass
            else:
                return False, "❌ No puedes sancionar a ese usuario (es owner o protegido)."

        # Si autor es OWNER_IDS o guild owner, le permitimos (salvo cuando target == bot)
        if author.id in OWNER_IDS or (ctx.guild and author == ctx.guild.owner):
            # ensure bot can still act
            bot_member = ctx.guild.get_member(self.bot.user.id)
            if bot_member and bot_member.top_role <= target_member.top_role:
                return False, "❌ No puedo actuar sobre ese usuario: mi rol es inferior o igual."
            return True, ""

        # autor necesita top_role > target.top_role
        try:
            if author.top_role <= target_member.top_role:
                return False, "❌ No puedes actuar sobre ese usuario (rol igual o superior)."
        except Exception:
            return False, "❌ Error comprobando jerarquía del autor."

        # bot necesita ser capaz de actuar también
        bot_member = ctx.guild.get_member(self.bot.user.id)
        if bot_member:
            try:
                if bot_member.top_role <= target_member.top_role:
                    return False, "❌ No puedo actuar sobre ese usuario: mi rol es igual o inferior."
            except Exception:
                return False, "❌ Error comprobando jerarquía del bot."

        return True, ""

    async def log_action(self, ctx: commands.Context, title: str, color: discord.Colour,
                         target: Optional[discord.abc.Snowflake] = None, extra: str = ""):
        """Envía un embed al canal de logs configurado. No falla si no hay canal."""
        channel = None
        try:
            channel = self.bot.get_channel(LOG_CHANNEL_ID)
        except Exception:
            channel = None
        if not channel:
            return
        embed = discord.Embed(title=title, color=color, timestamp=datetime.now(UTC))
        if target:
            try:
                mention = target.mention
            except Exception:
                mention = f"{getattr(target, 'name', str(target))} ({getattr(target, 'id', '??')})"
            embed.add_field(name="👤 Usuario", value=mention, inline=False)
        else:
            embed.add_field(name="👤 Usuario", value="No especificado", inline=False)
        embed.add_field(name="🛠️ Moderador", value=ctx.author.mention, inline=False)
        if extra:
            embed.add_field(name="📌 Extra", value=extra, inline=False)
        try:
            await channel.send(embed=embed)
        except Exception:
            pass

    def parse_duration(self, duration_str: str) -> Optional[timedelta]:
        """Parsea 5s 10m 2h 3d 1w -> timedelta"""
        if not duration_str:
            return None
        m = re.match(r'^(\d+)([smhdw])$', duration_str.lower())
        if not m:
            return None
        v, u = int(m.group(1)), m.group(2)
        if u == 's':
            return timedelta(seconds=v)
        if u == 'm':
            return timedelta(minutes=v)
        if u == 'h':
            return timedelta(hours=v)
        if u == 'd':
            return timedelta(days=v)
        if u == 'w':
            return timedelta(weeks=v)
        return None

    async def resolve_member(self, ctx: commands.Context, identifier: str) -> Optional[discord.Member]:
        """Resuelve un Member del guild a partir de mention, id, name o name#discrim."""
        if not identifier or not ctx.guild:
            return None

        # Attempt mention or id
        id_match = re.search(r'(\d{6,20})', identifier)
        if id_match:
            try:
                member = ctx.guild.get_member(int(id_match.group(1)))
                if member:
                    return member
            except Exception:
                pass

        # name#discrim
        if '#' in identifier:
            name, discrim = identifier.rsplit('#', 1)
            for m in ctx.guild.members:
                if m.name == name and m.discriminator == discrim:
                    return m

        # match by display_name or name (case-insensitive)
        lower = identifier.lower()
        for m in ctx.guild.members:
            try:
                if m.display_name.lower() == lower or m.name.lower() == lower:
                    return m
            except Exception:
                continue

        return None

    async def find_banned_user(self, ctx: commands.Context, identifier: str) -> Optional[discord.User]:
        """Busca entre los bans por ID, name o name#discrim. Devuelve User o None."""
        if not ctx.guild:
            return None
        try:
            bans = await ctx.guild.bans()
        except discord.Forbidden:
            return None
        except Exception:
            bans = []

        # by id
        id_match = re.search(r'(\d{6,20})', identifier)
        if id_match:
            uid = int(id_match.group(1))
            for entry in bans:
                if entry.user.id == uid:
                    return entry.user
            # si no está entre bans, devolvemos usuario por fetch (para intentar unban por id)
            try:
                return await self.bot.fetch_user(uid)
            except Exception:
                return None

        # name#discrim
        if '#' in identifier:
            name, discrim = identifier.rsplit('#', 1)
            for entry in bans:
                if entry.user.name == name and entry.user.discriminator == discrim:
                    return entry.user

        # name only
        lower = identifier.lower()
        for entry in bans:
            try:
                if entry.user.name.lower() == lower:
                    return entry.user
            except Exception:
                continue

        return None

    # ==============================
    # ==============================
    # ⚠️ WARNINGS / UNWARN (soft actions)
    # ==============================
    # ==============================
    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def warn(self, ctx: commands.Context, target: str = None, *, reason: str = "No especificado"):
        """Añade una advertencia (warn) a un usuario."""
        if not target or not self.has_permission(ctx):
            embed = discord.Embed(title="⚠️ Uso incorrecto", description="`$warn <usuario/id/mention/name#1234> [razón]`", color=discord.Color.red(), timestamp=datetime.now(UTC))
            return await ctx.send(embed=embed)

        member = await self.resolve_member(ctx, target)
        if not member:
            return await ctx.send("❌ Usuario no encontrado en el servidor.")

        # comprobar jerarquía (evita auto-warn y warn a superiores)
        ok, reason_err = self.check_hierarchy(ctx, member)
        if not ok:
            return await ctx.send(reason_err)

        uid = str(member.id)
        self.warnings.setdefault(uid, [])
        self.warnings[uid].append({"reason": reason, "moderator": ctx.author.id, "timestamp": datetime.now(UTC)})

        embed = discord.Embed(title="⚠️ Advertencia", description=f"{member.mention} ha sido advertido.\n**Razón:** {reason}", color=discord.Color.yellow(), timestamp=datetime.now(UTC))
        embed.add_field(name="🔢 Total advertencias", value=str(len(self.warnings[uid])), inline=True)
        embed.set_footer(text=f"Moderador: {ctx.author}", icon_url=getattr(ctx.author, "display_avatar", None).url if hasattr(ctx.author, "display_avatar") else None)
        await ctx.send(embed=embed)
        await self.log_action(ctx, "⚠️ Advertencia", discord.Color.yellow(), target=member, extra=f"Razón: {reason}")

        # auto-mute al alcanzar 3 (si existe role)
        if len(self.warnings[uid]) >= 3:
            mute_role = ctx.guild.get_role(MUTE_ROLE_ID)
            if mute_role:
                try:
                    # re-check hierarchy for auto-mute
                    ok2, err2 = self.check_hierarchy(ctx, member)
                    if not ok2:
                        # no podemos aplicar mute automático si jerarquía impide
                        return
                    await member.add_roles(mute_role, reason=f"Alcanzó 3 advertencias: {reason}")
                    embed2 = discord.Embed(title="🔇 Mute automático", description=f"{member.mention} fue muteado automáticamente por alcanzar 3 advertencias.", color=discord.Color.dark_gray(), timestamp=datetime.now(UTC))
                    await ctx.send(embed=embed2)
                    await self.log_action(ctx, "🔇 Mute automático", discord.Color.dark_gray(), target=member, extra="3 advertencias alcanzadas")
                except Exception:
                    pass

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def unwarn(self, ctx: commands.Context, target: str = None, index: int = None):
        """Remueve una advertencia especifica por índice (1-based)."""
        if not target or index is None or not self.has_permission(ctx):
            embed = discord.Embed(title="⚠️ Uso incorrecto", description="`$unwarn <usuario/id/mention/name#1234> <índice>`", color=discord.Color.red(), timestamp=datetime.now(UTC))
            return await ctx.send(embed=embed)

        member = await self.resolve_member(ctx, target)
        if not member:
            return await ctx.send("❌ Usuario no encontrado en el servidor.")

        # comprobar jerarquía
        ok, reason_err = self.check_hierarchy(ctx, member)
        if not ok:
            return await ctx.send(reason_err)

        uid = str(member.id)
        if uid not in self.warnings or index < 1 or index > len(self.warnings[uid]):
            return await ctx.send("⚠️ Índice inválido o el usuario no tiene advertencias.")

        removed = self.warnings[uid].pop(index - 1)
        await ctx.send(f"✅ Advertencia #{index} removida de {member.mention}.")
        await self.log_action(ctx, "⚠️ Advertencia removida", discord.Color.orange(), target=member, extra=f"Índice: {index} - Razón original: {removed.get('reason')}")

    @commands.command(aliases=["infractions", "warns"])
    @commands.has_permissions(manage_messages=True)
    async def warnings(self, ctx: commands.Context, target: str = None):
        """Muestra advertencias de un usuario (si no se pasa target devuelve error para forzar identificar)."""
        if not target and ctx.message.mentions:
            # if user mentioned someone, resolve first mention
            target = str(ctx.message.mentions[0].id)
        if not target:
            return await ctx.send("⚠️ Uso: `$warnings <usuario/id/mention/name#1234>`")

        member = await self.resolve_member(ctx, target)
        if not member:
            return await ctx.send("❌ Usuario no encontrado en el servidor.")

        uid = str(member.id)
        if uid not in self.warnings or not self.warnings[uid]:
            return await ctx.send(f"📋 {member.mention} no tiene advertencias.")

        embed = discord.Embed(title=f"📋 Advertencias de {member}", color=discord.Color.orange(), timestamp=datetime.now(UTC))
        for i, warning in enumerate(self.warnings[uid], 1):
            ts = warning.get("timestamp")
            if isinstance(ts, datetime):
                ts_str = ts.strftime('%Y-%m-%d %H:%M:%S UTC')
            else:
                ts_str = str(ts)
            embed.add_field(name=f"Advertencia #{i}", value=f"Razón: {warning['reason']}\nModerador: <@{warning['moderator']}>\nFecha: {ts_str}", inline=False)
        await ctx.send(embed=embed)

    # ==============================
    # ==============================
    # 🔇 MUTE / 🔊 UNMUTE / ⏳ TIMEOUT (medium actions)
    # ==============================
    # ==============================
    @commands.command()
    @commands.has_permissions(manage_roles=True)
    async def mute(self, ctx: commands.Context, target: str = None, duration: str = None, *, reason: str = "No especificado"):
        """
        Mutea por ID/mention/name#discrim/nombre. Soporta duración (5s,10m,7h,2d,1w).
        Nota: para que el mute funcione correctamente, configura MUTE_ROLE_ID en config.
        """
        if not target or not self.has_permission(ctx):
            embed = discord.Embed(title="⚠️ Uso incorrecto", description="`$mute <usuario/id/mention/name#1234> [duración(s/m/h/d/w)] [razón]`", color=discord.Color.red(), timestamp=datetime.now(UTC))
            embed.add_field(name="Ejemplo", value="`$mute @Pepe 5m Spam`", inline=False)
            return await ctx.send(embed=embed)

        member = await self.resolve_member(ctx, target)
        if not member:
            return await ctx.send("❌ Usuario no encontrado en el servidor.")

        # jerarquía
        ok, err = self.check_hierarchy(ctx, member)
        if not ok:
            return await ctx.send(err)

        mute_role = ctx.guild.get_role(MUTE_ROLE_ID)
        if not mute_role:
            return await ctx.send("❌ Rol de mute no configurado o no encontrado. Define MUTE_ROLE_ID o crea el rol manualmente.")

        duration_td = None
        if duration:
            duration_td = self.parse_duration(duration)
            if not duration_td:
                return await ctx.send("⚠️ Duración inválida. Usa: 5s, 10m, 7h, 2d, 1w.")

        try:
            await member.add_roles(mute_role, reason=reason)
            embed = discord.Embed(
                title="🔇 Usuario muteado",
                description=f"{member.mention} fue muteado.\n**Razón:** {reason}{f'\\n⏳ Duración: {duration}' if duration else ''}",
                color=discord.Color.dark_gray(),
                timestamp=datetime.now(UTC)
            )
            await ctx.send(embed=embed)
            await self.log_action(ctx, "🔇 Usuario muteado", discord.Color.dark_gray(), target=member, extra=f"Duración: {duration or 'Indefinida'}")

            # si tiene duración, crear tarea para desmutear (no persiste reinicios)
            if duration_td:
                async def _auto_unmute(member_ref, role, delay_seconds, ctx_ref):
                    await asyncio.sleep(delay_seconds)
                    try:
                        guild = ctx_ref.guild
                        if not guild:
                            return
                        m = guild.get_member(member_ref.id)
                        if not m:
                            return
                        if role in m.roles:
                            await m.remove_roles(role, reason="Mute expirado automáticamente")
                            await self.log_action(ctx_ref, "🔊 Mute expirado", discord.Color.green(), target=m)
                    except Exception:
                        pass

                delay = int(duration_td.total_seconds())
                try:
                    self.bot.loop.create_task(_auto_unmute(member, mute_role, delay, ctx))
                except Exception:
                    asyncio.create_task(_auto_unmute(member, mute_role, delay, ctx))

        except discord.Forbidden:
            await ctx.send("❌ No tengo permisos para asignar roles (mi rol debe estar por encima del rol mute).")
        except Exception as e:
            await ctx.send(f"❌ Error al mutear: {e}")

    @commands.command()
    @commands.has_permissions(manage_roles=True)
    async def unmute(self, ctx: commands.Context, target: str = None):
        """Remueve el rol de mute de un usuario."""
        if not target or not self.has_permission(ctx):
            embed = discord.Embed(title="⚠️ Uso incorrecto", description="`$unmute <usuario/id/mention/name#1234>`", color=discord.Color.red(), timestamp=datetime.now(UTC))
            return await ctx.send(embed=embed)

        member = await self.resolve_member(ctx, target)
        if not member:
            return await ctx.send("❌ Usuario no encontrado en el servidor.")

        ok, err = self.check_hierarchy(ctx, member)
        if not ok:
            return await ctx.send(err)

        mute_role = ctx.guild.get_role(MUTE_ROLE_ID)
        if not mute_role:
            return await ctx.send("❌ Rol de mute no configurado.")

        try:
            if mute_role in member.roles:
                await member.remove_roles(mute_role, reason=f"Desmuteado por {ctx.author}")
                embed = discord.Embed(title="🔊 Usuario desmuteado", description=f"{member.mention} fue desmuteado.", color=discord.Color.green(), timestamp=datetime.now(UTC))
                await ctx.send(embed=embed)
                await self.log_action(ctx, "🔊 Usuario desmuteado", discord.Color.green(), target=member)
            else:
                await ctx.send("⚠️ Ese usuario no está muteado.")
        except discord.Forbidden:
            await ctx.send("❌ No tengo permisos para remover roles del usuario.")
        except Exception as e:
            await ctx.send(f"❌ Error al desmutear: {e}")

    @commands.command()
    @commands.has_permissions(moderate_members=True)
    async def timeout(self, ctx: commands.Context, target: str = None, duration: str = None, *, reason: str = "No especificado"):
        """
        Aplica timeout a un miembro. Duración ejemplo: 5m, 1h, 2d.
        Máx 28 días.
        """
        if not target or not duration or not self.has_permission(ctx):
            embed = discord.Embed(title="⚠️ Uso incorrecto", description="`$timeout <usuario/id/mention/name#1234> <duración>` (ej. 5m, máx. 28d)", color=discord.Color.red(), timestamp=datetime.now(UTC))
            return await ctx.send(embed=embed)

        member = await self.resolve_member(ctx, target)
        if not member:
            return await ctx.send("❌ Usuario no encontrado en el servidor.")

        ok, err = self.check_hierarchy(ctx, member)
        if not ok:
            return await ctx.send(err)

        duration_td = self.parse_duration(duration)
        if not duration_td or duration_td > timedelta(days=28):
            return await ctx.send("⚠️ Duración inválida (máx. 28 días).")

        until = datetime.now(UTC) + duration_td
        try:
            # Usamos member.edit con timed_out_until por compatibilidad con discord.py 2.x
            await member.edit(timed_out_until=until, reason=reason)
            embed = discord.Embed(title="⏳ Timeout aplicado", description=f"{member.mention} fue silenciado por {duration}.\n**Razón:** {reason}", color=discord.Color.blue(), timestamp=datetime.now(UTC))
            await ctx.send(embed=embed)
            await self.log_action(ctx, "⏳ Timeout aplicado", discord.Color.blue(), target=member, extra=f"Duración: {duration}")
        except discord.Forbidden:
            await ctx.send("❌ No tengo permisos para aplicar timeout.")
        except Exception as e:
            await ctx.send(f"❌ Error al aplicar timeout: {e}")

    @commands.command()
    @commands.has_permissions(moderate_members=True)
    async def remove_timeout(self, ctx: commands.Context, target: str = None):
        """Remueve timeout (timed_out_until=None)."""
        if not target or not self.has_permission(ctx):
            embed = discord.Embed(title="⚠️ Uso incorrecto", description="`$remove_timeout <usuario/id/mention/name#1234>`", color=discord.Color.red(), timestamp=datetime.now(UTC))
            return await ctx.send(embed=embed)

        member = await self.resolve_member(ctx, target)
        if not member:
            return await ctx.send("❌ Usuario no encontrado en el servidor.")

        ok, err = self.check_hierarchy(ctx, member)
        if not ok:
            return await ctx.send(err)

        try:
            await member.edit(timed_out_until=None, reason=f"Timeout removido por {ctx.author}")
            embed = discord.Embed(title="🔓 Timeout removido", description=f"{member.mention} puede hablar de nuevo.", color=discord.Color.green(), timestamp=datetime.now(UTC))
            await ctx.send(embed=embed)
            await self.log_action(ctx, "🔓 Timeout removido", discord.Color.green(), target=member)
        except discord.Forbidden:
            await ctx.send("❌ No tengo permisos para editar al usuario.")
        except Exception as e:
            await ctx.send(f"❌ Error al remover timeout: {e}")

    # ==============================
    # ==============================
    # 👢 KICK / 🚫 BAN / ♻️ UNBAN (strong actions)
    # ==============================
    # ==============================
    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx: commands.Context, target: str = None, *, reason: str = "No especificado"):
        """Expulsa a un miembro del servidor."""
        if not target or not self.has_permission(ctx):
            embed = discord.Embed(title="⚠️ Uso incorrecto", description="`$kick <usuario/id/mention/name#1234> [razón]`", color=discord.Color.red(), timestamp=datetime.now(UTC))
            return await ctx.send(embed=embed)

        member = await self.resolve_member(ctx, target)
        if not member:
            return await ctx.send("❌ Usuario no encontrado en el servidor (solo se puede kickear a miembros presentes).")

        ok, err = self.check_hierarchy(ctx, member)
        if not ok:
            return await ctx.send(err)

        try:
            await member.kick(reason=reason)
            embed = discord.Embed(title="👢 Usuario expulsado", description=f"{member.mention} fue expulsado.\n**Razón:** {reason}", color=discord.Color.orange(), timestamp=datetime.now(UTC))
            await ctx.send(embed=embed)
            await self.log_action(ctx, "👢 Usuario expulsado", discord.Color.orange(), target=member, extra=f"Razón: {reason}")
        except discord.Forbidden:
            await ctx.send("❌ No tengo permisos para expulsar a este usuario.")
        except Exception as e:
            await ctx.send(f"❌ Error al expulsar: {e}")

    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx: commands.Context, target: str = None, *, reason: str = "No especificado"):
        """
        Banea a un usuario. target puede ser member presente o ID/name#discrim.
        Evita banear OWNER_IDS o al guild owner si no eres owner.
        """
        if not target or not self.has_permission(ctx):
            embed = discord.Embed(title="⚠️ Uso incorrecto", description="`$ban <usuario/id/mention/name#1234> [razón]`", color=discord.Color.red(), timestamp=datetime.now(UTC))
            return await ctx.send(embed=embed)

        # intentar resolver como miembro primero
        member = await self.resolve_member(ctx, target)
        target_obj = None

        try:
            if member:
                # evitar self-ban
                if member.id == ctx.author.id:
                    return await ctx.send("❌ No puedes banearte a ti mismo.")
                ok, err = self.check_hierarchy(ctx, member)
                if not ok:
                    return await ctx.send(err)
                await member.ban(reason=reason)
                target_obj = member
            else:
                # si no está en el server, permitir ban por ID si no es owner/owner del servidor y si autor tiene permiso
                id_match = re.search(r'(\d{6,20})', target)
                if id_match:
                    uid = int(id_match.group(1))
                    if uid in OWNER_IDS:
                        return await ctx.send("❌ No puedes banear a ese usuario (protegido).")
                    # si el id coincide con owner del guild, bloquear salvo si autor es owner
                    try:
                        if ctx.guild and ctx.guild.owner and ctx.guild.owner.id == uid:
                            if ctx.author.id not in OWNER_IDS and ctx.author != ctx.guild.owner:
                                return await ctx.send("❌ No puedes banear al owner del servidor.")
                    except Exception:
                        pass
                    try:
                        user = await self.bot.fetch_user(uid)
                        await ctx.guild.ban(user, reason=reason)
                        target_obj = user
                    except discord.Forbidden:
                        return await ctx.send("❌ No tengo permisos para banear a ese usuario.")
                    except Exception as e:
                        return await ctx.send(f"❌ Error al banear: {e}")
                else:
                    # intentar por name#discrim en bans o fetch user
                    user = None
                    try:
                        user = await self.find_banned_user(ctx, target)
                    except Exception:
                        user = None
                    if user:
                        # si ya baneado, no tiene sentido banear de nuevo
                        return await ctx.send("⚠️ Ese usuario ya está baneado.")
                    return await ctx.send("❌ Usuario no encontrado para banear. Si no está en el servidor, usa su ID.")
            # embed y log
            embed = discord.Embed(title="🚫 Usuario baneado", description=f"{getattr(target_obj, 'mention', getattr(target_obj,'name',str(target_obj)))} fue baneado.\n**Razón:** {reason}", color=discord.Color.red(), timestamp=datetime.now(UTC))
            await ctx.send(embed=embed)
            await self.log_action(ctx, "🚫 Usuario baneado", discord.Color.red(), target=target_obj, extra=f"Razón: {reason}")
        except discord.Forbidden:
            await ctx.send("❌ No tengo permisos para banear a este usuario.")
        except Exception as e:
            await ctx.send(f"❌ Error al banear: {e}")

    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx: commands.Context, target: str = None, *, reason: str = "No especificado"):
        """
        Desbanea por ID o name#discrim. Evita desbanear protegidos inadvertidamente.
        """
        if not target or not self.has_permission(ctx):
            embed = discord.Embed(title="⚠️ Uso incorrecto", description="`$unban <usuario/id/name#1234/name> [razón]`", color=discord.Color.red(), timestamp=datetime.now(UTC))
            return await ctx.send(embed=embed)

        banned_user = await self.find_banned_user(ctx, target)
        if not banned_user:
            return await ctx.send("❌ No encontré al usuario en la lista de bans. Usa ID o name#discrim si no lo encuentras.")

        # prevenir desbanear a owners protegidos sin permisos especiales
        try:
            if getattr(banned_user, "id", None) in OWNER_IDS:
                return await ctx.send("❌ No puedes desbanear a ese usuario (protegido).")
            if ctx.guild and ctx.guild.owner and getattr(banned_user, "id", None) == ctx.guild.owner.id:
                if ctx.author.id not in OWNER_IDS and ctx.author != ctx.guild.owner:
                    return await ctx.send("❌ No puedes desbanear al owner del servidor.")
        except Exception:
            pass

        try:
            await ctx.guild.unban(banned_user, reason=reason)
            embed = discord.Embed(title="🔓 Usuario desbaneado", description=f"{getattr(banned_user, 'name', str(banned_user))} fue desbaneado.\n**Razón:** {reason}", color=discord.Color.green(), timestamp=datetime.now(UTC))
            await ctx.send(embed=embed)
            await self.log_action(ctx, "🔓 Usuario desbaneado", discord.Color.green(), target=banned_user, extra=f"Razón: {reason}")
        except discord.Forbidden:
            await ctx.send("❌ No tengo permisos para desbanear.")
        except discord.NotFound:
            await ctx.send("❌ No se encontró el ban (tal vez ya fue removido).")
        except Exception as e:
            await ctx.send(f"❌ Error al desbanear: {e}")

    # ==============================
    # ==============================
    # 🧹 Purge (clear) / clearuser
    # ==============================
    # ==============================
    @commands.command(aliases=["purge", "c"])
    @commands.has_permissions(manage_messages=True)
    async def clear(self, ctx: commands.Context, amount: int = None):
        """Elimina mensajes en el canal (máx 100)."""
        if not amount or amount < 1 or amount > 100 or not self.has_permission(ctx):
            embed = discord.Embed(title="❌ Uso incorrecto", description="Formato correcto:\n`$clear <cantidad>` (máx. 100)\nEjemplo: `$clear 10`", color=discord.Color.red(), timestamp=datetime.now(UTC))
            return await ctx.send(embed=embed)

        try:
            deleted = await ctx.channel.purge(limit=amount + 1)
            count = max(0, len(deleted) - 1)
            confirm = discord.Embed(
                title="🧹 Purge realizado",
                description=(f"👤 Moderador: {ctx.author.mention}\n🗑️ Se eliminaron **{count}** mensajes en {ctx.channel.mention}."),
                color=discord.Color.blurple(),
                timestamp=datetime.now(UTC)
            )
            await ctx.send(embed=confirm, delete_after=3)
            await self.log_action(ctx, "🧹 Purge realizado", discord.Color.blurple(), extra=f"Canal: {ctx.channel.mention}\nMensajes: {count}")
        except discord.Forbidden:
            await ctx.send("❌ No tengo permisos para eliminar mensajes.")
        except Exception as e:
            await ctx.send(f"❌ Error al purgar: {e}")

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def clearuser(self, ctx: commands.Context, target: str = None, amount: int = None):
        """Elimina mensajes de un usuario específico (máx 100)."""
        if not target or not amount or amount < 1 or amount > 100 or not self.has_permission(ctx):
            embed = discord.Embed(title="❌ Uso incorrecto", description="Formato correcto:\n`$clearuser <usuario/id/mention/name#1234> <cantidad>` (máx. 100)", color=discord.Color.red(), timestamp=datetime.now(UTC))
            return await ctx.send(embed=embed)

        member = await self.resolve_member(ctx, target)
        if not member:
            return await ctx.send("❌ Usuario no encontrado en el servidor.")

        # comprobar jerarquía: no permitir borrar mensajes de alguien superior
        ok, err = self.check_hierarchy(ctx, member)
        if not ok:
            return await ctx.send(err)

        def is_member_message(m):
            return m.author == member

        try:
            deleted = await ctx.channel.purge(limit=amount + 1, check=is_member_message)
            count = max(0, len(deleted) - 1)
            confirm = discord.Embed(
                title="🧹 Mensajes eliminados",
                description=f"Se eliminaron **{count}** mensajes de {member.mention} en {ctx.channel.mention}.",
                color=discord.Color.blurple(),
                timestamp=datetime.now(UTC)
            )
            await ctx.send(embed=confirm, delete_after=3)
            await self.log_action(ctx, "🧹 Mensajes eliminados", discord.Color.blurple(), target=member, extra=f"Usuario: {member.mention}\nMensajes: {count}")
        except discord.Forbidden:
            await ctx.send("❌ No tengo permisos para eliminar mensajes.")
        except Exception as e:
            await ctx.send(f"❌ Error al purgar: {e}")

    # ==============================
    # ==============================
    # 🔒 LOCK / 🔓 UNLOCK (channel management)
    # ==============================
    # ==============================
    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def lock(self, ctx: commands.Context, channel: Optional[discord.TextChannel] = None):
        """Bloquea el canal para @everyone (no puede enviar mensajes)."""
        channel = channel or ctx.channel
        try:
            overwrite = channel.overwrites_for(ctx.guild.default_role)
            overwrite.send_messages = False
            await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
            embed = discord.Embed(title="🔒 Canal bloqueado", description=f"{channel.mention} ha sido bloqueado.", color=discord.Color.red(), timestamp=datetime.now(UTC))
            await ctx.send(embed=embed)
            await self.log_action(ctx, "🔒 Canal bloqueado", discord.Color.red(), extra=f"Canal: {channel.mention}")
        except discord.Forbidden:
            await ctx.send("❌ No tengo permisos para modificar permisos del canal.")
        except Exception as e:
            await ctx.send(f"❌ Error al bloquear canal: {e}")

    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def unlock(self, ctx: commands.Context, channel: Optional[discord.TextChannel] = None):
        """Desbloquea el canal para @everyone."""
        channel = channel or ctx.channel
        try:
            overwrite = channel.overwrites_for(ctx.guild.default_role)
            overwrite.send_messages = None
            await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
            embed = discord.Embed(title="🔓 Canal desbloqueado", description=f"{channel.mention} ha sido desbloqueado.", color=discord.Color.green(), timestamp=datetime.now(UTC))
            await ctx.send(embed=embed)
            await self.log_action(ctx, "🔓 Canal desbloqueado", discord.Color.green(), extra=f"Canal: {channel.mention}")
        except discord.Forbidden:
            await ctx.send("❌ No tengo permisos para modificar permisos del canal.")
        except Exception as e:
            await ctx.send(f"❌ Error al desbloquear canal: {e}")

    # ==============================
    # ==============================
    # 📖 HELP (paginador con botones)
    # ==============================
    # ==============================
    @commands.command(name="helpmoderation", aliases=["helpmod", "hmod"])
    async def helpmoderation(self, ctx: commands.Context):
        pages = [
            discord.Embed(title="Ayuda de Moderación", description="**Comandos de limpieza y control.**", color=discord.Color.blue(), timestamp=datetime.now(UTC))
            .add_field(name="🧼 Clear/Purge", value="`$clear <número>`\nElimina mensajes en masa (máx. 100).", inline=False)
            .add_field(name="🧹 Clearuser", value="`$clearuser <usuario> <cantidad>`\nElimina mensajes de un usuario (máx. 100).", inline=False)
            .add_field(name="🔇 Mute", value="`$mute <usuario> [duración] [razón]`", inline=False)
            .set_footer(text="Página 1/3"),

            discord.Embed(title="Ayuda de Moderación", description="**Comandos adicionales.**", color=discord.Color.green(), timestamp=datetime.now(UTC))
            .add_field(name="🔊 Unmute", value="`$unmute <usuario>`", inline=False)
            .add_field(name="🔓 Remove Timeout", value="`$remove_timeout <usuario>`", inline=False)
            .add_field(name="🔒 Lock / 🔓 Unlock", value="`$lock` / `$unlock`", inline=False)
            .add_field(name="⚠️ Warn", value="`$warn <usuario> [razón]`", inline=False)
            .set_footer(text="Página 2/3"),

            discord.Embed(title="Ayuda de Moderación", description="**Comandos de gestión.**", color=discord.Color.purple(), timestamp=datetime.now(UTC))
            .add_field(name="📋 Warnings", value="`$warnings [usuario]`\nMuestra las advertencias de un usuario.", inline=False)
            .add_field(name="🔧 Unwarn", value="`$unwarn <usuario> <índice>`\nRemueve una advertencia específica.", inline=False)
            .add_field(name="👢 Kick", value="`$kick <usuario> [razón]`", inline=False)
            .add_field(name="🚫 Ban", value="`$ban <usuario/id> [razón]`", inline=False)
            .add_field(name="🔓 Unban", value="`$unban <usuario/id/name#1234> [razón]`", inline=False)
            .set_footer(text="Página 3/3"),
        ]

        class Paginator(View):
            def __init__(self):
                super().__init__(timeout=300)
                self.current = 0

            async def update(self, interaction: discord.Interaction):
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
                try:
                    await interaction.message.delete()
                except Exception:
                    pass
                self.stop()

        await ctx.send(embed=pages[0], view=Paginator())

# ==============================
# SETUP
# ==============================
async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot))

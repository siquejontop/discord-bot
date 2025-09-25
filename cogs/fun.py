import discord
from discord.ext import commands
from datetime import datetime, timedelta, timezone
import asyncio

# ---------- Configuración ----------
COLOMBIA_TZ = timezone(timedelta(hours=-5))

# IDs (pon aquí los tuyos si cambian)
ORDERED_ROLE_ID = 1415860212438667325
STAFF_CHANNEL_ID = 1376127149412716586
REGLAS_CHANNEL_ID = 1415896991891984434
GUIDE_CHANNEL_ID = 1415860305568727240
HELP_CHANNEL_ID = 1415860320572018799
RULES_CHANNEL_ID = 1415860303794802798

MIDDLEMANNOVATO_ROLE_ID = 1415860204624416971
VENTAS_CHANNEL_ID = 1419948313251155978
MMGUIDE_CHANNEL_ID = 1415860325223235606

OWNER_ID = 335596693603090434  # tu ID (dueño del bot)
# ------------------------------------

class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # =====================================================
    # 🏓 Ping
    # =====================================================
    @commands.command()
    async def ping(self, ctx):
        await ctx.send("🏓 Pong!")

    # =====================================================
    # 📡 Listener: Detectar cuando alguien recibe un rol
    # =====================================================
    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        before_roles = set(before.roles)
        after_roles = set(after.roles)
        added_roles = after_roles - before_roles

        # ------------------------
        # Caso 1: "ordered from site"
        # ------------------------
        ordered_role = discord.utils.get(after.guild.roles, id=ORDERED_ROLE_ID)
        if ordered_role and ordered_role in added_roles:
            staff_channel = after.guild.get_channel(STAFF_CHANNEL_ID)
            if staff_channel:
                await staff_channel.send(f"📢 {after.mention} acaba de recibir el rol de **hitter**")

                reglas_channel = after.guild.get_channel(REGLAS_CHANNEL_ID)
                guide_channel = after.guild.get_channel(GUIDE_CHANNEL_ID)
                help_channel = after.guild.get_channel(HELP_CHANNEL_ID)
                rules_channel = after.guild.get_channel(RULES_CHANNEL_ID)

                embed = discord.Embed(
                    title="Ahora tienes el rol de hitter // Now you've the role of hitter",
                    description=(
                        f"Ahora eres hitter, recuerda revisar {reglas_channel.mention} {guide_channel.mention} {help_channel.mention}\n\n"
                        f"You're now a hitter, make sure to check {rules_channel.mention} {guide_channel.mention} {help_channel.mention}\n"
                    ),
                    color=discord.Color.red()
                )
                await staff_channel.send(embed=embed)

        # ------------------------
        # Caso Middleman
        # ------------------------
        mm_role = discord.utils.get(after.guild.roles, id=MIDDLEMANNOVATO_ROLE_ID)
        if mm_role and mm_role in added_roles:
            ventas_channel = after.guild.get_channel(VENTAS_CHANNEL_ID)
            mmguide_channel = after.guild.get_channel(MMGUIDE_CHANNEL_ID)

            if ventas_channel:
                await ventas_channel.send(f"⭐ {after.mention} acaba de recibir el rol de **Middleman**")

                embed_channel = discord.Embed(
                    title="Bienvenido Middleman",
                    description=(f"No olvides de leer {mmguide_channel.mention} para evitar cualquier problema en el servidor."),
                    color=discord.Color.gold()
                )
                await ventas_channel.send(embed=embed_channel)

            # DM al usuario que recibió el rol
            embed_dm = discord.Embed(
                title="🎉 Felicidades, recibiste el rol de Middleman",
                description=(
                    f"Ahora formas parte de los **Middleman** del servidor.\n\n"
                    f"Recuerda leer {mmguide_channel.mention} y tener en cuenta todas las reglas."
                ),
                color=discord.Color.gold()
            )
            embed_dm.set_footer(text="Gracias por tu apoyo")
            try:
                await after.send(embed=embed_dm)
            except discord.Forbidden:
                if ventas_channel:
                    await ventas_channel.send(f"⚠️ No pude enviarle DM a {after.mention} (tiene bloqueados los mensajes directos).")

            # ----------------------------------------------
            # Notificar al OWNER con audit logs (espera 2s)
            # ----------------------------------------------
            await asyncio.sleep(2)  # esperar para que Discord registre el log

            # Obtener responsable desde audit logs (robusto)
            giver = None
            try:
                async for entry in after.guild.audit_logs(limit=20, action=discord.AuditLogAction.member_role_update):
                    if entry.target.id != after.id:
                        continue

                    # Intentamos extraer la lista "roles" del "after" del cambio
                    roles_after = None
                    try:
                        roles_after = entry.changes.after.roles  # lo más común
                    except Exception:
                        # otros formatos posibles (dict)
                        try:
                            after_attr = entry.changes.after
                            if isinstance(after_attr, dict):
                                roles_after = after_attr.get("roles") or after_attr.get("role")
                        except Exception:
                            roles_after = None

                    if not roles_after:
                        # si no pudimos extraer roles, pasamos a la siguiente entrada
                        continue

                    # normalizar a ids
                    try:
                        role_ids = {r.id if isinstance(r, discord.Role) else int(r) for r in roles_after}
                    except Exception:
                        # fallback si roles_after es extraño
                        role_ids = set()
                        for r in roles_after:
                            try:
                                role_ids.add(int(getattr(r, "id", r)))
                            except Exception:
                                pass

                    if MIDDLEMANNOVATO_ROLE_ID in role_ids:
                        giver = entry.user
                        break
            except discord.Forbidden:
                # falta permiso VIEW_AUDIT_LOG
                print("No tengo permiso para leer audit logs (VIEW_AUDIT_LOG).")
            except Exception as e:
                print("Error al leer audit logs:", e)

            # preparar responsable legible
            if giver:
                responsable = f"{giver.mention} (`{giver.id}`)"
                if getattr(giver, "bot", False):
                    responsable += " 🤖 (Bot)"
            else:
                responsable = "⚠️ No encontrado"

            # conseguir owner (try cache -> fetch)
            owner = after.guild.get_member(OWNER_ID)
            if owner is None:
                try:
                    owner = await self.bot.fetch_user(OWNER_ID)
                except Exception as e:
                    print("No pude obtener el usuario owner:", e)
                    owner = None

            if owner:
                fecha_col = datetime.now(timezone.utc).astimezone(COLOMBIA_TZ)
                embed_owner = discord.Embed(
                    title="📢 Notificación: Nuevo Middleman",
                    description=(
                        f"📌 **Usuario:** {after.mention} (`{after.id}`)\n"
                        f"👤 **Asignado por:** {responsable}\n\n"
                        f"📅 **Fecha y hora:** {fecha_col.strftime('%Y-%m-%d %H:%M:%S')} (Hora Colombia)"
                    ),
                    color=discord.Color.blue()
                )
                embed_owner.set_footer(text=f"Servidor: {after.guild.name}")
                try:
                    await owner.send(embed=embed_owner)
                except discord.Forbidden:
                    print("⚠️ No se pudo enviar DM al owner (forbidden).")
                except Exception as e:
                    print("Error enviando DM al owner:", e)
            else:
                print("Owner no encontrado; no se envió notificación.")    

# =====================================================
# 👥 Contador de baneados
# =====================================================
@bot.command()
@commands.has_permissions(ban_members=True)
async def banlist(ctx):
    """Muestra la cantidad de usuarios baneados en el servidor"""
    try:
        banned_users = [entry async for entry in ctx.guild.bans()]
        total = len(banned_users)

        embed = discord.Embed(
            title="📊 Lista de baneados",
            description=f"🔒 Este servidor tiene **{total}** usuarios baneados.",
            color=discord.Color.dark_red(),
            timestamp=datetime.now(timezone.utc)
        )

        await ctx.send(embed=embed)

    except Exception as e:
        await ctx.send(f"⚠️ Error al obtener la lista de baneados: {e}")

# =====================================================
# 🔌 Setup obligatorio
# =====================================================
async def setup(bot):
    await bot.add_cog(Fun(bot))

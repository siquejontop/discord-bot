import discord
from discord.ext import commands
from datetime import datetime, timedelta, timezone
import asyncio

# ---------- Configuración ----------
COLOMBIA_TZ = timezone(timedelta(hours=-5))

# IDs (pon aquí los tuyos si cambian)
ORDERED_ROLE_ID = 1421330898569269409
STAFF_CHANNEL_ID = 1421331102890725487
REGLAS_CHANNEL_ID = 1421331154006577182
GUIDE_CHANNEL_ID = 1421331155604471839
HELP_CHANNEL_ID = 1421331102890725487
RULES_CHANNEL_ID = 1421331109622583447

MIDDLEMANNOVATO_ROLE_ID = 1421330888192561152
VENTAS_CHANNEL_ID = 1421331128161140878
MMGUIDE_CHANNEL_ID = 1421331155604471839

OWNER_ID = 335596693603090434  # tu ID (dueño del bot)
# ------------------------------------

class Fun(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # =====================================================
    # 🏓 Ping
    # =====================================================
    @commands.command()
    async def ping(self, ctx: commands.Context):
        await ctx.send("🏓 Pong!")

    # =====================================================
    # 📡 Listener: Detectar cuando alguien recibe un rol
    # =====================================================
    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        try:
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

                    # Enviar mensaje en embed por DM
                    dm_embed = discord.Embed(
                        title="¿__Quieres aprender a como estafar__?",
                        description=(
                            ":lock: Asegurate de estar verificado en el canal verify para tener acceso a todos los canales!\n\n"
                            ":lock: Busca victimas en otros servers o personas de aca si no tienen el rol ordered from site\n\n"
                            ":office_worker: Diles que usen middleman de este servidor\n\n"
                            ":detective: Te ayudaremos a asegurar el objeto\n\n"
                            ":white_check_mark: Una vez realizado recibiras tu parte\n\n"
                            ":handshake: Tu y el middleman se repartiran los objetos. El middleman te dara mitad y mitad o algunos te pueden dar el 100% si quieren.\n\n"
                            "__Nota__: Si tienes alguna duda, pregunta en ⁠⁠https://discord.com/channels/1376127147847979050/1421331102890725487"
                        ),
                        color=discord.Color.blue()
                    )
                    try:
                        await after.send(embed=dm_embed)
                    except discord.Forbidden:
                        await staff_channel.send(f"⚠️ No pude enviarle DM a {after.mention} (tiene bloqueados los mensajes directos).")

            # ------------------------
            # Caso Middleman
            # ------------------------
            mm_role = discord.utils.get(after.guild.roles, id=MIDDLEMANNOVATO_ROLE_ID)
            if mm_role and mm_role in added_roles:
                print(f"DEBUG: {after} recibió el rol {mm_role.name} ({mm_role.id})")

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

                giver = None
                for attempt in range(3):
                    await asyncio.sleep(2)
                    try:
                        async for entry in after.guild.audit_logs(limit=20, action=discord.AuditLogAction.member_role_update):
                            if entry.target.id != after.id:
                                continue

                            roles_after = None
                            try:
                                roles_after = entry.changes.after.roles
                            except Exception:
                                try:
                                    after_attr = entry.changes.after
                                    if isinstance(after_attr, dict):
                                        roles_after = after_attr.get("roles") or after_attr.get("role")
                                except Exception:
                                    roles_after = None

                            if not roles_after:
                                continue

                            role_ids = set()
                            try:
                                for r in roles_after:
                                    if isinstance(r, discord.Role):
                                        role_ids.add(r.id)
                                    else:
                                        role_ids.add(int(getattr(r, "id", r)))
                            except Exception:
                                pass

                            if MIDDLEMANNOVATO_ROLE_ID in role_ids:
                                giver = entry.user
                                break
                    except discord.Forbidden:
                        print("No tengo permiso para leer audit logs (VIEW_AUDIT_LOG).")
                        break
                    except Exception as e:
                        print("Error al leer audit logs:", e)

                    if giver:
                        break

                if giver:
                    responsable = f"{giver.mention} (`{giver.id}`)"
                    if getattr(giver, "bot", False):
                        responsable += " 🤖 (Bot)"
                else:
                    responsable = "⚠️ No encontrado"

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

        except Exception as e:
            print("Error en on_member_update:", e)

    # =====================================================
    # 🔓 Comando para desbanear a todos
    # =====================================================
    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def unbanall(self, ctx: commands.Context):
        """Desbanea a todos los usuarios baneados"""
        await ctx.send("🔓 Iniciando proceso de desbaneo...")

        try:
            banned_users = [entry async for entry in ctx.guild.bans()]
            if not banned_users:
                await ctx.send("✅ No hay usuarios baneados.")
                return

            await ctx.send(f"🛠️ Desbaneando {len(banned_users)} usuarios...")
            desbaneados = 0

            for ban_entry in banned_users:
                user = ban_entry.user
                try:
                    await ctx.guild.unban(user)
                    desbaneados += 1
                except discord.NotFound:
                    continue
                except discord.Forbidden:
                    await ctx.send(f"⛔ No tengo permiso para desbanear a {user}.")
                    continue
                except Exception as e:
                    await ctx.send(f"⚠️ Error con {user}: {e}")
                    continue

            await ctx.send(f"✅ Desbaneados {desbaneados} usuarios exitosamente.")

        except Exception as e:
            await ctx.send(f"❌ Error inesperado: {e}")
            print(f"[ERROR] {e}")

    # =====================================================
    # 👥 Contador de baneados
    # =====================================================
    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def banlist(self, ctx: commands.Context):
        """Muestra la cantidad de usuarios baneados en el servidor"""
        try:
            banned_entries = [ban async for ban in ctx.guild.bans()]
            total = len(banned_entries)

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
async def setup(bot: commands.Bot):
    await bot.add_cog(Fun(bot))

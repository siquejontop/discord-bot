import discord
from discord.ext import commands
from datetime import datetime, timedelta, timezone
import asyncio

# Zona horaria Colombia (UTC-5)
COLOMBIA_TZ = timezone(timedelta(hours=-5))

class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # =====================================================
    # 📡 Listener: Detectar cuando alguien recibe un rol
    # =====================================================
    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        before_roles = set(before.roles)
        after_roles = set(after.roles)

        added_roles = after_roles - before_roles

        # ========================
        # 🎯 Caso: Rol "Middleman"
        # ========================
        MIDDLEMANNOVATO_ROLE_ID = 1415860204624416971  
        VENTAS_CHANNEL_ID = 1419948313251155978  
        OWNER_ID = 335596693603090434  # tu ID

        mm_role = discord.utils.get(after.guild.roles, id=MIDDLEMANNOVATO_ROLE_ID)
        if mm_role in added_roles:
            ventas_channel = after.guild.get_channel(VENTAS_CHANNEL_ID)
            if ventas_channel:
                await ventas_channel.send(f"⭐ {after.mention} acaba de recibir el rol de **Middleman**")

                MMGUIDE_CHANNEL_ID = 1415860325223235606
                mmguide_channel = after.guild.get_channel(MMGUIDE_CHANNEL_ID)

                embed_channel = discord.Embed(
                    title="Bienvenido Middleman",
                    description=(f"No olvides de leer {mmguide_channel.mention} para evitar cualquier problema en el servidor."),
                    color=discord.Color.gold()
                )
                await ventas_channel.send(embed=embed_channel)

            # 📩 Enviar DM al usuario
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

            # ===============================
            # 📩 Notificación al dueño del bot
            # ===============================
            await asyncio.sleep(2)  # ⏳ Esperar para que el log se registre

            owner = after.guild.get_member(OWNER_ID)
            if owner:
                giver = None
                async for entry in after.guild.audit_logs(limit=10, action=discord.AuditLogAction.member_role_update):
                    if entry.target.id == after.id and mm_role in entry.changes.after.roles:
                        giver = entry.user
                        break

                fecha_colombia = datetime.now(timezone.utc).astimezone(COLOMBIA_TZ)

                if giver:
                    responsable = f"{giver.mention} (`{giver.id}`)"
                    if giver.bot:
                        responsable += " 🤖 (Bot)"
                else:
                    responsable = "⚠️ No encontrado"

                embed_owner = discord.Embed(
                    title="📢 Notificación: Nuevo Middleman",
                    description=(
                        f"📌 **Usuario:** {after.mention} (`{after.id}`)\n"
                        f"👤 **Asignado por:** {responsable}\n\n"
                        f"📅 **Fecha y hora:** {fecha_colombia.strftime('%Y-%m-%d %H:%M:%S')} (Hora Colombia)"
                    ),
                    color=discord.Color.blue()
                )
                embed_owner.set_footer(text=f"Servidor: {after.guild.name}")
                try:
                    await owner.send(embed=embed_owner)
                except discord.Forbidden:
                    print("⚠️ No se pudo enviar DM al dueño del bot.")

# =====================================================
# 🔌 Setup obligatorio
# =====================================================
async def setup(bot):
    await bot.add_cog(Fun(bot))

import discord
from discord.ext import commands

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

        # ========================
        # 🎯 Caso 1: Rol "ordered from site"
        # ========================
        ORDERED_ROLE_ID = 1415860212438667325  
        STAFF_CHANNEL_ID = 1376127149412716586  

        ordered_role = discord.utils.get(after.guild.roles, id=ORDERED_ROLE_ID)
        if ordered_role in added_roles:
            staff_channel = after.guild.get_channel(STAFF_CHANNEL_ID)
            if staff_channel:
                await staff_channel.send(f"📢 {after.mention} acaba de recibir el rol de **hitter**")

                REGLAS_CHANNEL_ID = 1415896991891984434
                GUIDE_CHANNEL_ID = 1415860305568727240
                HELP_CHANNEL_ID = 1415860320572018799
                RULES_CHANNEL_ID = 1415860303794802798

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

        # ========================
        # 🎯 Caso 2: Rol "Middleman"
        # ========================
        MIDDLEMANNOVATO_ROLE_ID = 1415860204624416971  
        VENTAS_CHANNEL_ID = 1419948313251155978  

        vip_role = discord.utils.get(after.guild.roles, id=MIDDLEMANNOVATO_ROLE_ID)
        if vip_role in added_roles:
            vip_channel = after.guild.get_channel(VENTAS_CHANNEL_ID)
            if vip_channel:
                await vip_channel.send(f"⭐ {after.mention} acaba de recibir el rol de **Middleman**")
                
                MMGUIDE_CHANNEL_ID = 1415860325223235606

                reglas_channel = after.guild.get_channel(MMGUIDE_CHANNEL_ID)

                embed_channel = discord.Embed(
                    title="Bienvenido Middleman",
                    description=(
                        f"No olvides de leer el canal de {mmguide_channel.mention} para evitar cualquier problema en el servidor."
                    ),
                    color=discord.Color.gold()
                )
                await vip_channel.send(embed=embed_channel)

            # 📩 Enviar mensaje directo (DM) con embed
            embed_dm = discord.Embed(
                title="🎉 Felicidades, recibiste el rol de Middleman",
                description=(
                    "Ahora formas parte de los **Middleman** del servidor.\n\n"
                    "Recuerda leer {mmguide_channel.mention} y tener encuenta todas las reglas para evitar warns innecesarios."
                ),
                color=discord.Color.gold()
            )
            embed_dm.set_footer(text="Gracias por tu apoyo")

            try:
                await after.send(embed=embed_dm)
            except discord.Forbidden:
                if vip_channel:
                    await vip_channel.send(
                        f"⚠️ No pude enviarle DM a {after.mention} (tiene bloqueados los mensajes directos)."
                    )


# =====================================================
# 🔌 Setup obligatorio
# =====================================================
async def setup(bot):
    await bot.add_cog(Fun(bot))

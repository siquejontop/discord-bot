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
    # 📡 Listener: Detectar cuando alguien recibe el rol
    # =====================================================
    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        ORDERED_ROLE_ID = 1415860212438667325  # 👈 rol "ordered from site"
        STAFF_CHANNEL_ID = 1376127149412716586  # 👈 canal staff

        before_roles = set(before.roles)
        after_roles = set(after.roles)

        added_roles = after_roles - before_roles
        ordered_role = discord.utils.get(after.guild.roles, id=ORDERED_ROLE_ID)

        if ordered_role in added_roles:
            staff_channel = after.guild.get_channel(STAFF_CHANNEL_ID)
            if staff_channel:
                # Aviso con ping
                await staff_channel.send(f"📢 {after.mention} acaba de recibir el rol de **hitter**")

                # Canales que quieres mencionar en el embed
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


# =====================================================
# 🔌 Setup obligatorio
# =====================================================
async def setup(bot):
    await bot.add_cog(Fun(bot))

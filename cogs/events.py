import discord
from discord.ext import commands
from datetime import datetime, timezone
from config import get_log_channel

class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member):
        channel = get_log_channel(member.guild)
        if channel:
            embed = discord.Embed(
                title=f"✅ {member} se unió",
                color=discord.Color.green(),
                timestamp=datetime.now(timezone.utc)
            )
            embed.add_field(name="Cuenta creada", value=member.created_at.strftime("%d/%m/%Y %H:%M"))
            embed.add_field(name="ID", value=member.id)
            embed.set_thumbnail(url=member.display_avatar.url)
            await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        channel = get_log_channel(member.guild)
        if channel:
            embed = discord.Embed(
                title=f"❌ {member} salió",
                color=discord.Color.red(),
                timestamp=datetime.now(timezone.utc)
            )
            embed.add_field(name="Se unió el", value=member.joined_at.strftime("%d/%m/%Y %H:%M") if member.joined_at else "Desconocido")
            embed.add_field(name="ID", value=member.id)
            embed.set_thumbnail(url=member.display_avatar.url)
            await channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Events(bot))

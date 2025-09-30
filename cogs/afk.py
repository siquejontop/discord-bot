import discord
from discord.ext import commands
import datetime

class AFK(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Estructura: {user_id: {"reason": str, "since": datetime}}
        self.afk_users = {}

    # ================================
    # 🔹 Comando AFK
    # ================================
    @commands.command()
    async def afk(self, ctx, *, reason: str = "AFK"):
        self.afk_users[ctx.author.id] = {
            "reason": reason,
            "since": datetime.datetime.utcnow()
        }
        embed = discord.Embed(
            description=f"✅ {ctx.author.mention}: You're now AFK with the status: **{reason}**",
            color=0x2ecc71,
            timestamp=datetime.datetime.utcnow()
        )
        await ctx.send(embed=embed)

    # ================================
    # 🔹 Listener AFK
    # ================================
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        user_id = message.author.id

        # 📌 Si el autor estaba AFK y habló → quitar AFK
        if user_id in self.afk_users:
            afk_data = self.afk_users.pop(user_id)
            afk_time = datetime.datetime.utcnow() - afk_data["since"]

            minutes, seconds = divmod(int(afk_time.total_seconds()), 60)
            hours, minutes = divmod(minutes, 60)

            embed = discord.Embed(
                description=f"👋 {message.author.mention}: Welcome back, you were away for **{hours}h {minutes}m {seconds}s**",
                color=0xf1c40f,
                timestamp=datetime.datetime.utcnow()
            )
            await message.channel.send(embed=embed)

        # 📌 Si menciona a alguien AFK → avisar
        for user in message.mentions:
            if user.id in self.afk_users:
                afk_data = self.afk_users[user.id]
                afk_time = datetime.datetime.utcnow() - afk_data["since"]

                minutes, seconds = divmod(int(afk_time.total_seconds()), 60)
                hours, minutes = divmod(minutes, 60)

                embed = discord.Embed(
                    description=f"💤 {user.mention} is AFK: **{afk_data['reason']}** – hace {hours}h {minutes}m {seconds}s",
                    color=0x3498db,
                    timestamp=datetime.datetime.utcnow()
                )
                await message.channel.send(embed=embed)

        await self.bot.process_commands(message)


# ================================
# 🔌 Setup
# ================================
async def setup(bot):
    await bot.add_cog(AFK(bot))

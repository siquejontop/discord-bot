import discord
from discord.ext import commands
from datetime import datetime

class AFK(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Diccionario de usuarios AFK
        self.afk_users = {}  # user_id: {"reason": str, "since": datetime, "old_nick": str}

    # ======================
    # Comando AFK
    # ======================
    @commands.command()
    async def afk(self, ctx, *, reason: str = "AFK"):
        """Marca al usuario como AFK"""
        member = ctx.author

        # Guardar nickname actual (si no tiene, usar None)
        old_nick = member.nick

        # Cambiar nickname a [AFK] nombre
        try:
            await member.edit(nick=f"[AFK] {member.display_name}")
        except discord.Forbidden:
            pass  # por si no tiene permisos para cambiar nick

        # Guardar en el diccionario
        self.afk_users[member.id] = {
            "reason": reason,
            "since": datetime.utcnow(),
            "old_nick": old_nick
        }

        embed = discord.Embed(
            description=f"✅ {member.mention} ahora está AFK: **{reason}**",
            color=0x2ecc71
        )
        await ctx.send(embed=embed)

    # ======================
    # Evento de mensajes
    # ======================
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        # Si alguien AFK escribe → quitar AFK
        if message.author.id in self.afk_users:
            afk_data = self.afk_users.pop(message.author.id)
            afk_time = (datetime.utcnow() - afk_data["since"]).seconds

            # Restaurar nickname
            try:
                await message.author.edit(nick=afk_data["old_nick"])
            except discord.Forbidden:
                pass

            embed = discord.Embed(
                description=f"👋 {message.author.mention} bienvenido de vuelta, estuviste AFK por **{afk_time} segundos**",
                color=0xf1c40f
            )
            await message.channel.send(embed=embed)

        # Si menciona a alguien AFK
        for user in message.mentions:
            if user.id in self.afk_users:
                afk_data = self.afk_users[user.id]
                afk_time = (datetime.utcnow() - afk_data["since"]).seconds

                embed = discord.Embed(
                    description=f"💤 {user.mention} está AFK: **{afk_data['reason']}** – hace {afk_time} segundos",
                    color=0x3498db
                )
                await message.channel.send(embed=embed)

    # ======================
    # Setup del cog
    # ======================
async def setup(bot):
    await bot.add_cog(AFK(bot))

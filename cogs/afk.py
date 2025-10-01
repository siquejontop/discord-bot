import discord
from discord.ext import commands
from datetime import datetime

class AFK(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.afk_users = {}

    # ======================
    # Función para formatear tiempo
    # ======================
    def tiempo_hace(self, delta):
        segundos = int(delta.total_seconds())
        horas, resto = divmod(segundos, 3600)
        minutos, segundos = divmod(resto, 60)

        partes = []
        if horas > 0:
            partes.append(f"{horas} hora{'s' if horas > 1 else ''}")
        if minutos > 0:
            partes.append(f"{minutos} minuto{'s' if minutos > 1 else ''}")
        if segundos > 0:
            partes.append(f"{segundos} segundo{'s' if segundos > 1 else ''}")

        if not partes:
            partes.append("0 segundos")

        return "hace " + ", ".join(partes)

    # ======================
    # Comando AFK
    # ======================
    @commands.command()
    async def afk(self, ctx, *, reason: str = "AFK"):
        member = ctx.author
        old_nick = member.nick

        try:
            await member.edit(nick=f"[AFK] {member.display_name}")
        except discord.Forbidden:
            pass

        self.afk_users[member.id] = {
            "reason": reason,
            "since": datetime.utcnow(),
            "old_nick": old_nick,
            "mentions": []
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

        # Quitar AFK si habla
        if message.author.id in self.afk_users:
            afk_data = self.afk_users.pop(message.author.id)
            delta = datetime.utcnow() - afk_data["since"]
            afk_time = self.tiempo_hace(delta)

            try:
                await message.author.edit(nick=afk_data["old_nick"])
            except discord.Forbidden:
                pass

            embed = discord.Embed(
                description=f"👋 {message.author.mention} bienvenido de vuelta! Estuviste AFK {afk_time}",
                color=0xf1c40f
            )
            await message.channel.send(embed=embed)

        # Avisar si mencionan a un AFK
        for user in message.mentions:
            if user.id in self.afk_users:
                afk_data = self.afk_users[user.id]
                delta = datetime.utcnow() - afk_data["since"]
                afk_time = self.tiempo_hace(delta)

                jump = f"[Mensaje]({message.jump_url})"
                afk_data["mentions"].append(f"{message.author.mention} → {jump}")

                embed = discord.Embed(
                    description=f"💤 {user.mention} está AFK: **{afk_data['reason']}** – {afk_time}",
                    color=0x3498db
                )
                await message.channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(AFK(bot))

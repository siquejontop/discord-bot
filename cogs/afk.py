import discord
from discord.ext import commands
from datetime import datetime

class AFK(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # user_id: {"reason": str, "since": datetime, "old_nick": str, "mentions": [str]}
        self.afk_users = {}

    # ======================
    # Función para formatear tiempo
    # ======================
    def format_timedelta(self, delta):
        total_seconds = int(delta.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        parts = []
        if hours > 0:
            parts.append(f"{hours} hora{'s' if hours != 1 else ''}")
        if minutes > 0:
            parts.append(f"{minutes} minuto{'s' if minutes != 1 else ''}")
        if seconds > 0 or not parts:
            parts.append(f"{seconds} segundo{'s' if seconds != 1 else ''}")

        return ", ".join(parts)

    # ======================
    # Comando AFK
    # ======================
    @commands.command()
    async def afk(self, ctx, *, reason: str = "AFK"):
        """Marca al usuario como AFK"""
        member = ctx.author
        old_nick = member.nick

        # Cambiar nickname
        try:
            await member.edit(nick=f"[AFK] {member.display_name}")
        except discord.Forbidden:
            pass

        # Guardar info
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
            afk_time = self.format_timedelta(delta)

            # Restaurar nick
            try:
                await message.author.edit(nick=afk_data["old_nick"])
            except discord.Forbidden:
                pass

            # Crear mensaje de regreso
            desc = f"👋 {message.author.mention} bienvenido de vuelta, estuviste AFK por **{afk_time}**"

            if afk_data["mentions"]:
                desc += f"\n\nRecibiste **{len(afk_data['mentions'])} menciones** mientras estabas AFK:"
                for mention in afk_data["mentions"][:5]:  # mostrar hasta 5
                    desc += f"\n{mention}"
                if len(afk_data["mentions"]) > 5:
                    desc += f"\n... y {len(afk_data['mentions']) - 5} más."

            embed = discord.Embed(description=desc, color=0xf1c40f)
            await message.channel.send(embed=embed)

        # Avisar si mencionan a un AFK
        for user in message.mentions:
            if user.id in self.afk_users:
                afk_data = self.afk_users[user.id]
                delta = datetime.utcnow() - afk_data["since"]
                afk_time = self.format_timedelta(delta)

                # Guardar la mención con jump_url
                jump = f"[Mensaje]({message.jump_url})"
                afk_data["mentions"].append(f"{message.author.mention} → {jump}")

                embed = discord.Embed(
                    description=f"💤 {user.mention} está AFK: **{afk_data['reason']}** – hace {afk_time}",
                    color=0x3498db
                )
                await message.channel.send(embed=embed)

# ======================
# Setup
# ======================
async def setup(bot):
    await bot.add_cog(AFK(bot))

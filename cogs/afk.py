import discord
from discord.ext import commands
import datetime

class AFK(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.afk_users = {}  # {user_id: {"reason": str, "time": datetime, "mentions": [], "old_nick": str}}

    # ================================
    # 🔹 Comando AFK
    # ================================
    @commands.command()
    async def afk(self, ctx, *, reason: str = "AFK"):
        user = ctx.author

        # Guardar su apodo original (si tiene)
        old_nick = user.nick if user.nick else user.name

        # Cambiar el nick a [AFK] Nombre (si se puede)
        try:
            await user.edit(nick=f"[AFK] {old_nick}")
        except discord.Forbidden:
            pass  # Si el bot no tiene permisos, lo ignoramos

        self.afk_users[user.id] = {
            "reason": reason,
            "time": datetime.datetime.utcnow(),
            "mentions": [],
            "old_nick": old_nick
        }

        embed = discord.Embed(
            title="🌙 Ahora estás AFK",
            color=discord.Color.orange()
        )
        embed.add_field(name="Razón", value=reason, inline=False)
        embed.add_field(name="✏️", value="Escribe cualquier mensaje para quitar el AFK.", inline=False)
        embed.set_footer(text=datetime.datetime.now().strftime("Today at %H:%M"))
        embed.set_author(name=user.display_name, icon_url=user.display_avatar.url)

        await ctx.send(embed=embed)

    # ================================
    # 🔹 Detectar mensajes AFK
    # ================================
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        user_id = message.author.id

        # 📌 Si el autor estaba AFK y habló, quitar AFK
        if user_id in self.afk_users:
            afk_data = self.afk_users.pop(user_id)
            afk_time = datetime.datetime.utcnow() - afk_data["time"]
            minutes, seconds = divmod(int(afk_time.total_seconds()), 60)

            # Restaurar nick original
            try:
                await message.author.edit(nick=afk_data["old_nick"])
            except discord.Forbidden:
                pass

            desc = f"👋 Bienvenido de vuelta, {message.author.mention}!\n"
            desc += f"Estuviste AFK por **{minutes} minutos {seconds} segundos.**"

            if afk_data["mentions"]:
                desc += f"\n\n📩 Recibiste **{len(afk_data['mentions'])} menciones** mientras estabas AFK:"
                for mention in afk_data["mentions"][:5]:  # máximo 5
                    desc += f"\n- {mention}"

            embed = discord.Embed(
                description=desc,
                color=discord.Color.green()
            )
            await message.channel.send(embed=embed)

        # 📌 Si menciona a alguien AFK, avisar
        if message.mentions:
            for mention in message.mentions:
                if mention.id in self.afk_users:
                    afk_data = self.afk_users[mention.id]
                    reason = afk_data["reason"]

                    # Guardar el link del mensaje en el historial
                    jump_url = f"[Ver mensaje]({message.jump_url})"
                    self.afk_users[mention.id]["mentions"].append(
                        f"{message.author.mention} → {jump_url}"
                    )

                    embed = discord.Embed(
                        description=f"💤 {mention.display_name} está AFK.\n**Razón:** {reason}",
                        color=discord.Color.red()
                    )
                    await message.channel.send(embed=embed)

        await self.bot.process_commands(message)


async def setup(bot):
    await bot.add_cog(AFK(bot))

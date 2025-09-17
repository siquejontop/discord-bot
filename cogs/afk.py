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

        # Guardar su apodo original
        old_nick = user.nick if user.nick else user.name

        # Cambiar el nick a [AFK] Nombre (si se puede)
        try:
            await user.edit(nick=f"[AFK] {old_nick}")
        except discord.Forbidden:
            pass

        self.afk_users[user.id] = {
            "reason": reason,
            "time": datetime.datetime.utcnow(),
            "mentions": [],
            "old_nick": old_nick
        }

        embed = discord.Embed(
            title="🌙 Modo AFK activado",
            description=f"{user.mention} ahora está AFK.",
            color=discord.Color.orange(),
            timestamp=datetime.datetime.utcnow()
        )
        embed.add_field(name="Razón", value=reason, inline=False)
        embed.set_footer(text="Escribe cualquier mensaje para quitar el AFK.")
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

        # 📌 Si el autor estaba AFK y habló → quitar AFK
        if user_id in self.afk_users:
            afk_data = self.afk_users.pop(user_id)
            afk_time = datetime.datetime.utcnow() - afk_data["time"]
            minutes, seconds = divmod(int(afk_time.total_seconds()), 60)
            hours, minutes = divmod(minutes, 60)

            # Restaurar nick original
            try:
                await message.author.edit(nick=afk_data["old_nick"])
            except discord.Forbidden:
                pass

            desc = f"👋 Bienvenido de vuelta, {message.author.mention}!\n"
            desc += f"Estuviste AFK por **{hours}h {minutes}m {seconds}s.**"

            if afk_data["mentions"]:
                mentions_list = "\n".join(afk_data["mentions"][:5])
                desc += f"\n\n📩 Recibiste **{len(afk_data['mentions'])} menciones** mientras estabas AFK:\n{mentions_list}"
            else:
                desc += "\n\n📩 Nadie te mencionó mientras estabas AFK."

            embed = discord.Embed(
                description=desc,
                color=discord.Color.green(),
                timestamp=datetime.datetime.utcnow()
            )
            embed.set_author(name=message.author.display_name, icon_url=message.author.display_avatar.url)

            await message.channel.send(embed=embed)

        # 📌 Si menciona a alguien AFK, avisar
        for mention in message.mentions:
            if mention.id in self.afk_users:
                afk_data = self.afk_users[mention.id]
                reason = afk_data["reason"]

                jump_url = f"[Ver mensaje]({message.jump_url})"
                self.afk_users[mention.id]["mentions"].append(
                    f"{message.author.mention} → {jump_url}"
                )

                embed = discord.Embed(
                    description=f"💤 {mention.display_name} está AFK.\n**Razón:** {reason}",
                    color=discord.Color.red(),
                    timestamp=datetime.datetime.utcnow()
                )
                embed.set_author(name=mention.display_name, icon_url=mention.display_avatar.url)

                await message.channel.send(embed=embed)

        # 📌 Evita duplicar mensajes: solo procesar comandos si el mensaje empieza con un prefijo válido
        prefixes = await self.bot.get_prefix(message)
        if isinstance(prefixes, str):
            prefixes = [prefixes]
        if any(message.content.startswith(p) for p in prefixes):
            await self.bot.process_commands(message)


async def setup(bot):
    await bot.add_cog(AFK(bot))

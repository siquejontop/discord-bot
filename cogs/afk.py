import discord
from discord.ext import commands
from datetime import datetime

class AFK(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # user_id: {"reason": str, "since": datetime, "mentions": [(author, link, content)]}
        self.afk_users = {}

    # ==========================
    # 📌 Comando AFK
    # ==========================
    @commands.command()
    async def afk(self, ctx, *, reason: str = "AFK"):
        """Ponerte en AFK con una razón opcional"""
        user_id = ctx.author.id

        # Guardar datos
        self.afk_users[user_id] = {
            "reason": reason,
            "since": datetime.utcnow(),
            "mentions": []
        }

        # Cambiar nick (añadir [AFK])
        try:
            if not ctx.author.display_name.startswith("[AFK]"):
                await ctx.author.edit(nick=f"[AFK] {ctx.author.display_name}")
        except discord.Forbidden:
            pass  # si no tiene permisos para cambiar el nick

        embed = discord.Embed(
            title="🌙 Ahora estás AFK",
            description=f"**Razón:** {reason}\n\n✏️ Escribe cualquier mensaje para quitar el AFK.",
            color=discord.Color.orange(),
            timestamp=datetime.utcnow()
        )
        await ctx.send(embed=embed)

    # ==========================
    # 📌 Listener mensajes
    # ==========================
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        # --- Evitar que comandos del bot quiten el AFK automáticamente ---
        prefixes = ["$", "!", "."]  # agrega aquí los prefijos que uses
        if any(message.content.startswith(p) for p in prefixes):
            return

        user_id = message.author.id

        # Si el usuario estaba AFK y escribe algo => quitar AFK
        if user_id in self.afk_users:
            data = self.afk_users.pop(user_id)
            since = data["since"]
            mentions = data["mentions"]

            # Restaurar nick (quitar [AFK])
            try:
                if message.author.display_name.startswith("[AFK]"):
                    await message.author.edit(nick=message.author.display_name[5:])
            except discord.Forbidden:
                pass

            # Tiempo AFK
            delta = datetime.utcnow() - since
            minutes, seconds = divmod(int(delta.total_seconds()), 60)
            hours, minutes = divmod(minutes, 60)
            time_text = f"{hours}h {minutes}m {seconds}s"

            # Embed de regreso
            embed = discord.Embed(
                title="✅ Ya no estás AFK",
                description=f"Estuviste AFK durante **{time_text}**",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )

            if mentions:
                mentions_text = "\n".join(
                    [f"[{author}]({link}) → {content[:40]}..."
                     for author, link, content in mentions]
                )
            else:
                mentions_text = "Nadie te mencionó 👌"

            embed.add_field(name="🔔 Menciones recibidas", value=mentions_text, inline=False)
            await message.channel.send(embed=embed)

        # Detectar si alguien menciona a un AFK
        for mention in message.mentions:
            if mention.id in self.afk_users:
                afk_data = self.afk_users[mention.id]
                reason = afk_data["reason"]

                # Guardar mención
                jump_link = message.jump_url
                afk_data["mentions"].append((str(message.author), jump_link, message.content))

                # Avisar
                embed = discord.Embed(
                    title=f"💤 {mention.display_name} está AFK",
                    description=f"**Razón:** {reason}",
                    color=discord.Color.blue(),
                    timestamp=datetime.utcnow()
                )
                await message.channel.send(embed=embed)


# ==========================
# 🔌 Setup
# ==========================
async def setup(bot):
    await bot.add_cog(AFK(bot))

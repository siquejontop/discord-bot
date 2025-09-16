# cogs/howto.py
import discord
from discord.ext import commands
from datetime import datetime, timezone

class HowTo(commands.Cog):
    """Cog que muestra instrucciones (howto) en inglés y español sin botones."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def howto(self, ctx):
        """
        English instructions embed.
        Uso: $howto
        """
        embed = discord.Embed(
            title="Want to know how to hit? 🤔",
            description=(
                "🔒 Make sure you verify in the verify channel to get access to all the channels!\n\n"
                "🔒 You find victims in various trading servers\n\n"
                "🧑‍💼 You get victims to use our middleman service\n\n"
                "🕵️ We will help you to secure the item\n\n"
                "✅ Once successfully receiving the item\n\n"
                "🤝 You, as well as the MM, will split the item(s). Our splits are 50/50 or MM can give you 100% if they choose to."
            ),
            color=discord.Color.blue(),
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url if ctx.author.display_avatar else None)
        await ctx.send(embed=embed)

    @commands.command(name="howtoes")
    async def howto_es(self, ctx):
        """
        Spanish instructions embed.
        Uso: $howtoes
        """
        embed = discord.Embed(
            title="Quieres aprender a como estafar? 🤔",
            description=(
                "🔒 Asegurate de estar verificado en el canal verify para tener acceso a todos los canales!\n\n"
                "🔒 Busca victimas en otros servers o personas de aca si no tienen el rol ordered from site\n\n"
                "🧑‍💼 Diles que usen middleman de este servidor\n\n"
                "🕵️ Te ayudaremos a asegurar el objeto\n\n"
                "✅  Una vez realizado recibiras tu parte\n\n"
                "🤝 Tu y el middleman se repartiran los objetos. El middleman te dara mitad y mitad o algunos te pueden dar el 100% si quieren."
            ),
            color=discord.Color.red(),
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_footer(text=f"Solicitado por {ctx.author}", icon_url=ctx.author.display_avatar.url if ctx.author.display_avatar else None)
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(HowTo(bot))

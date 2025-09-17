import discord
from discord.ext import commands

class BrainrotCalculator(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="lascombinasionas")
    async def brainrot(self, ctx, m: float):
        """
        Calculadora Brainrot: aplica la fórmula (M - 15) × 0.08 + 2
        """
        # Fórmula
        result = (m - 15) * 0.08 + 2

        # Embed bonito
        embed = discord.Embed(
            title="Calculadora Brainrot",
            description="Conversión automática usando la fórmula",
            color=discord.Color.blurple()
        )
        embed.add_field(
            name="📌 Operación",
            value=f"( {m} - 15 ) × 0.08 + 2",
            inline=False
        )
        embed.add_field(
            name="💰 Resultado",
            value=f"**{result:.2f}$**",
            inline=False
        )
        embed.set_footer(text=f"Pedido por {ctx.author}", icon_url=ctx.author.display_avatar.url)

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(BrainrotCalculator(bot))

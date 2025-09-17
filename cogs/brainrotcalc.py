import discord
from discord.ext import commands

class BrainrotCalculator(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ========================
    # Fórmulas Brainrot
    # ========================

    @commands.command(name="loscombinaciones")
    async def loscombinaciones(self, ctx, m: float):
        # Fórmula: (M - 15) × 0.08 + 2
        result = (m - 15) * 0.08 + 2
        await ctx.send(f"🧠 Resultado de **loscombinaciones** con M={m}: **{result:.2f}**")

    @commands.command(name="losotros")
    async def losotros(self, ctx, m: float):
        # Ejemplo de otra fórmula (puedes cambiarla por la que te pidan)
        result = (m * 2) + 10
        await ctx.send(f"🧠 Resultado de **losotros** con M={m}: **{result:.2f}**")

    @commands.command(name="brainformula")
    async def brainformula(self, ctx, m: float):
        # Otro ejemplo de fórmula
        result = (m ** 2) / 5
        await ctx.send(f"🧠 Resultado de **brainformula** con M={m}: **{result:.2f}**")

async def setup(bot):
    await bot.add_cog(BrainrotCalculator(bot))

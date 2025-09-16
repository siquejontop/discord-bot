import discord
from discord.ext import commands

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.is_owner()
    async def reload(self, ctx, extension: str):
        """♻️ Recarga un cog. Uso: $reload <nombre>"""
        try:
            await self.bot.reload_extension(f"cogs.{extension}")
            await ctx.send(f"♻️ Recargado **{extension}** correctamente.")
        except Exception as e:
            await ctx.send(f"❌ Error recargando {extension}: `{e}`")

async def setup(bot):
    await bot.add_cog(Admin(bot))

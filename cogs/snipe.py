import discord
from discord.ext import commands

last_deleted = {}

class Snipe(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        last_deleted[message.channel.id] = message

    @commands.command()
    async def snipe(self, ctx):
        msg = last_deleted.get(ctx.channel.id)
        if not msg:
            return await ctx.send("❌ No hay mensajes recientes eliminados.")
        embed = discord.Embed(
            title="📌 Snipe",
            description=msg.content,
            color=discord.Color.purple()
        )
        embed.set_footer(text=f"Autor: {msg.author}")
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Snipe(bot))

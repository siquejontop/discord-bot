import discord
from discord.ext import commands
from datetime import datetime, timezone, timedelta


# 🔹 Poner aquí el ID del canal de logs
LOG_CHANNEL_ID = 123456789012345678  # 👈 reemplázalo con el ID real de tu canal


class AutoBanNewAccounts(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.min_account_age = timedelta(days=30)  # Tiempo mínimo para no banear

    # ========================
    # 👤 Evento: nuevo miembro
    # ========================
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        account_age = datetime.now(timezone.utc) - member.created_at

        if account_age < self.min_account_age:
            try:
                await member.ban(reason=f"Cuenta demasiado nueva (creada hace {account_age.days} días)")

                log_channel = member.guild.get_channel(LOG_CHANNEL_ID)
                if log_channel:
                    embed = discord.Embed(
                        title="🚫 AutoBan",
                        description=f"{member.mention} fue baneado automáticamente.",
                        color=discord.Color.red(),
                        timestamp=datetime.now(timezone.utc)
                    )
                    embed.add_field(name="👤 Usuario", value=f"{member} (`{member.id}`)", inline=False)
                    embed.add_field(name="📅 Cuenta creada", value=f"<t:{int(member.created_at.timestamp())}:R>", inline=False)
                    embed.add_field(name="⏳ Antigüedad", value=f"{account_age.days} días", inline=False)
                    await log_channel.send(embed=embed)

            except discord.Forbidden:
                print(f"No tengo permisos para banear a {member}.")
            except Exception as e:
                print(f"Error al banear automáticamente a {member}: {e}")

    # ========================
    # ⚙️ Comando: configurar días
    # ========================
    @commands.command(name="setminage")
    @commands.has_permissions(administrator=True)
    async def set_min_age(self, ctx, days: int):
        """Configura el mínimo de días de antigüedad de cuenta para no ser baneado."""
        self.min_account_age = timedelta(days=days)
        await ctx.send(f"✅ Mínimo configurado en **{days} días**.")


# 👇 Obligatorio para que Render cargue el cog
async def setup(bot):
    await bot.add_cog(AutoBanNewAccounts(bot))

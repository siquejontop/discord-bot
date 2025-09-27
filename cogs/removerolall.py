import discord
from discord.ext import commands
import asyncio

# =====================================================
# ⚙️ CONFIG
# =====================================================
BOT_OWNER_IDS = [335596693603090434]  # IDs del dueño del bot


class RemoveRoleAll(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # =====================================================
    # 🔎 Utilidad para buscar rol
    # =====================================================
    def find_role(self, ctx: commands.Context, role_arg: str):
        """Busca un rol por ID o nombre (coincidencia parcial)."""
        if role_arg.isdigit():
            return ctx.guild.get_role(int(role_arg))

        role_arg = role_arg.lower()
        matches = [r for r in ctx.guild.roles if role_arg in r.name.lower()]

        if not matches:
            return None
        if len(matches) == 1:
            return matches[0]

        return matches  # múltiples coincidencias

    # =====================================================
    # 🛠️ Comando principal
    # =====================================================
    @commands.command(name="removerolall", aliases=["removerallrole", "rra"])
    @commands.has_permissions(manage_roles=True)
    async def removerolall(self, ctx: commands.Context, *, role_arg: str):
        """
        Remueve un rol de **todos los miembros** que lo tengan.
        Solo puede ser ejecutado por:
        - El dueño del servidor
        - El dueño del bot
        """

        # -------------------
        # Validar permisos
        # -------------------
        if ctx.author.id not in BOT_OWNER_IDS and ctx.author.id != ctx.guild.owner_id:
            return await ctx.send(
                embed=discord.Embed(
                    description="❌ Solo el **dueño del servidor** o el **dueño del bot** pueden usar este comando.",
                    color=discord.Color.red()
                )
            )

        # -------------------
        # Buscar rol
        # -------------------
        role = self.find_role(ctx, role_arg)
        if not role:
            return await ctx.send(
                embed=discord.Embed(
                    description=f"❌ No encontré el rol con el nombre o ID **{role_arg}**.",
                    color=discord.Color.red()
                )
            )
        if isinstance(role, list):
            lista = "\n".join([f"• {r.mention} (`{r.id}`)" for r in role[:10]])
            return await ctx.send(
                embed=discord.Embed(
                    title="❌ Se encontraron múltiples coincidencias",
                    description=f"{lista}\n\nEspecifica el **ID exacto** del rol.",
                    color=discord.Color.orange()
                )
            )

        # -------------------
        # Filtrar miembros
        # -------------------
        members_with_role = [m for m in ctx.guild.members if role in m.roles]
        total_members = len(members_with_role)

        if total_members == 0:
            return await ctx.send(
                embed=discord.Embed(
                    description=f"ℹ️ Nadie en este servidor tiene el rol {role.mention}.",
                    color=discord.Color.blurple()
                )
            )

        # -------------------
        # Confirmación inicial
        # -------------------
        confirm_msg = await ctx.send(
            embed=discord.Embed(
                title="⚠️ Confirmación requerida",
                description=f"Se removerá el rol {role.mention} de **{total_members}** miembros.\n\n"
                            f"Reacciona con ✅ para continuar o ❌ para cancelar.",
                color=discord.Color.orange()
            )
        )
        await confirm_msg.add_reaction("✅")
        await confirm_msg.add_reaction("❌")

        def check(reaction, user):
            return (
                user == ctx.author
                and str(reaction.emoji) in ["✅", "❌"]
                and reaction.message.id == confirm_msg.id
            )

        try:
            reaction, _ = await self.bot.wait_for("reaction_add", check=check, timeout=30)
        except asyncio.TimeoutError:
            return await ctx.send("⏰ Tiempo de confirmación agotado. Cancelado.")

        if str(reaction.emoji) == "❌":
            return await ctx.send("❌ Operación cancelada.")

        # -------------------
        # Mensaje de progreso
        # -------------------
        progress_embed = discord.Embed(
            title="⏳ Removiendo rol...",
            description=f"Iniciando proceso para {total_members} miembros.",
            color=discord.Color.orange()
        )
        progress_msg = await ctx.send(embed=progress_embed)

        # -------------------
        # Quitar roles con progreso
        # -------------------
        count = 0
        for member in members_with_role:
            try:
                await member.remove_roles(role, reason=f"Removido por {ctx.author}")
                count += 1
            except discord.Forbidden:
                await ctx.send(f"⚠️ No tengo permisos para quitar el rol de {member.mention}.")
            except Exception as e:
                print(f"Error al remover rol de {member}: {e}")

            # actualizar cada 10 miembros o al final
            if count % 10 == 0 or count == total_members:
                embed = discord.Embed(
                    title="⏳ Progreso",
                    description=f"Se removió el rol de **{count}/{total_members}** miembros.",
                    color=discord.Color.yellow()
                )
                await progress_msg.edit(embed=embed)

            await asyncio.sleep(1)  # evita rate limit

        # -------------------
        # Embed final
        # -------------------
        final_embed = discord.Embed(
            title="✅ Proceso completado",
            description=f"Se removió el rol {role.mention} de **{count}/{total_members}** miembros.",
            color=discord.Color.green()
        )
        final_embed.set_footer(text=f"Comando ejecutado por {ctx.author}")
        await progress_msg.edit(embed=final_embed)


# =====================================================
# 🔌 Setup obligatorio
# =====================================================
async def setup(bot: commands.Bot):
    await bot.add_cog(RemoveRoleAll(bot))

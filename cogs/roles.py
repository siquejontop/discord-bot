import discord
from discord.ext import commands

# ========================
# CONFIGURACIÓN
# ========================
LOG_CHANNEL_ID = 123456789012345678  # 🔴 PON AQUÍ EL ID DEL CANAL DE LOGS


class RolesPaginator(discord.ui.View):
    def __init__(self, roles):
        super().__init__(timeout=60)
        self.roles = roles
        self.page = 0
        self.chunk_size = 10

    def get_page_content(self):
        start = self.page * self.chunk_size
        end = start + self.chunk_size
        chunk = self.roles[start:end]

        description = "\n".join(
            [f"**{i+1}.** {r.mention}" for i, r in enumerate(chunk, start=start)]
        )

        embed = discord.Embed(
            title="📜 Roles",
            description=description or "No hay roles en esta página.",
            color=discord.Color.blurple()
        )
        embed.set_footer(
            text=f"Página {self.page+1}/{(len(self.roles)-1)//self.chunk_size+1} "
                 f"({len(self.roles)} roles en total)"
        )
        return embed

    @discord.ui.button(label="⬅️", style=discord.ButtonStyle.secondary)
    async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page > 0:
            self.page -= 1
            await interaction.response.edit_message(embed=self.get_page_content(), view=self)

    @discord.ui.button(label="➡️", style=discord.ButtonStyle.secondary)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if (self.page + 1) * self.chunk_size < len(self.roles):
            self.page += 1
            await interaction.response.edit_message(embed=self.get_page_content(), view=self)

    @discord.ui.button(label="❌", style=discord.ButtonStyle.danger)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.message.delete()


class Roles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ========================
    # 📜 Ver roles con páginas
    # ========================
    @commands.command(name="roles")
    async def roles(self, ctx):
        roles = ctx.guild.roles[1:]  # quitamos @everyone
        roles = sorted(roles, key=lambda r: r.position, reverse=True)

        if not roles:
            return await ctx.send("❌ Este servidor no tiene roles aparte de @everyone.")

        view = RolesPaginator(roles)
        await ctx.send(embed=view.get_page_content(), view=view)

    # ========================
    # Función auxiliar: buscar rol
    # ========================
    def find_role(self, ctx, role_arg: str):
        if role_arg.isdigit():  # ID
            return ctx.guild.get_role(int(role_arg))
        return discord.utils.find(lambda r: r.name.lower() == role_arg.lower(), ctx.guild.roles)

    # ========================
    # Función auxiliar: buscar usuario
    # ========================
    def find_member(self, ctx, member_arg: str):
        if member_arg.isdigit():  # ID
            return ctx.guild.get_member(int(member_arg))
        return discord.utils.find(
            lambda m: m.name.lower() == member_arg.lower() or (m.nick and m.nick.lower() == member_arg.lower()),
            ctx.guild.members
        )

    # ========================
    # Función auxiliar: validar jerarquía
    # ========================
    def can_modify_role(self, ctx, member: discord.Member, role: discord.Role):
        author = ctx.author
        bot_member = ctx.guild.me

        # Si se intenta modificar a sí mismo
        if member == author:
            if role == author.top_role:
                return False, f"❌ No puedes asignarte tu mismo rol ({role.mention})."
            if role >= author.top_role:
                return False, f"❌ No puedes asignarte un rol superior o igual al tuyo ({role.mention})."
        else:
            if member.top_role >= author.top_role:
                return False, f"❌ No puedes modificar a alguien con un rol superior o igual al tuyo ({member.top_role.mention})."

        if role >= bot_member.top_role:
            return False, f"❌ No puedo asignar/quitar un rol superior o igual al mío ({bot_member.top_role.mention})."

        return True, None

    # ========================
    # Función auxiliar: log de acción
    # ========================
    async def log_action(self, ctx, action: str, member: discord.Member, role: discord.Role):
        log_channel = ctx.guild.get_channel(LOG_CHANNEL_ID)
        if not log_channel:
            return

        # Colores según acción
        color_map = {
            "Added": discord.Color.green(),
            "Removed": discord.Color.red()
        }
        color = color_map.get(action, discord.Color.orange())

        embed = discord.Embed(
            title="📋 Registro de roles",
            description=f"{ctx.author.mention} **{action}** {role.mention} {'a' if action == 'Added' else 'de'} {member.mention}",
            color=color
        )
        embed.set_footer(text=f"Usuario: {ctx.author} | ID: {ctx.author.id}")
        await log_channel.send(embed=embed)

    # ========================
    # ➕ Añadir rol
    # ========================
    @commands.command(name="addrole", aliases=["addr", "ar"])
    @commands.has_permissions(manage_roles=True)
    async def addrole(self, ctx, member_arg: str, *, role_arg: str):
        member = ctx.guild.get_member(int(member_arg[2:-1])) if member_arg.startswith("<@") else self.find_member(ctx, member_arg)
        if not member:
            return await ctx.send(embed=discord.Embed(
                description=f"❌ No encontré el usuario **{member_arg}**.",
                color=discord.Color.red()
            ))

        role = self.find_role(ctx, role_arg)
        if not role:
            return await ctx.send(embed=discord.Embed(
                description=f"❌ No encontré el rol **{role_arg}**.",
                color=discord.Color.red()
            ))

        ok, error = self.can_modify_role(ctx, member, role)
        if not ok:
            return await ctx.send(embed=discord.Embed(description=error, color=discord.Color.red()))

        try:
            await member.add_roles(role)
            embed = discord.Embed(
                description=f"➕ {ctx.author.mention} : Added {role.mention} to {member.mention}",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
            await self.log_action(ctx, "Added", member, role)
        except discord.Forbidden:
            await ctx.send("❌ No tengo permisos suficientes para asignar ese rol.")

    # ========================
    # ➖ Quitar rol
    # ========================
    @commands.command(name="removerole", aliases=["delrole", "rr", "dr"])
    @commands.has_permissions(manage_roles=True)
    async def removerole(self, ctx, member_arg: str, *, role_arg: str):
        member = ctx.guild.get_member(int(member_arg[2:-1])) if member_arg.startswith("<@") else self.find_member(ctx, member_arg)
        if not member:
            return await ctx.send(embed=discord.Embed(
                description=f"❌ No encontré el usuario **{member_arg}**.",
                color=discord.Color.red()
            ))

        role = self.find_role(ctx, role_arg)
        if not role:
            return await ctx.send(embed=discord.Embed(
                description=f"❌ No encontré el rol **{role_arg}**.",
                color=discord.Color.red()
            ))

        ok, error = self.can_modify_role(ctx, member, role)
        if not ok:
            return await ctx.send(embed=discord.Embed(description=error, color=discord.Color.red()))

        try:
            await member.remove_roles(role)
            embed = discord.Embed(
                description=f"➖ {ctx.author.mention} : Removed {role.mention} from {member.mention}",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            await self.log_action(ctx, "Removed", member, role)
        except discord.Forbidden:
            await ctx.send("❌ No tengo permisos suficientes para quitar ese rol.")

    # ========================
    # 🔄 Toggle rol (dar o quitar con "r")
    # ========================
    @commands.command(name="r", aliases=["role"])
    @commands.has_permissions(manage_roles=True)
    async def toggle_role(self, ctx, member_arg: str, *, role_arg: str):
        member = ctx.guild.get_member(int(member_arg[2:-1])) if member_arg.startswith("<@") else self.find_member(ctx, member_arg)
        if not member:
            return await ctx.send(embed=discord.Embed(
                description=f"❌ No encontré el usuario **{member_arg}**.",
                color=discord.Color.red()
            ))

        role = self.find_role(ctx, role_arg)
        if not role:
            return await ctx.send(embed=discord.Embed(
                description=f"❌ No encontré el rol **{role_arg}**.",
                color=discord.Color.red()
            ))

        ok, error = self.can_modify_role(ctx, member, role)
        if not ok:
            return await ctx.send(embed=discord.Embed(description=error, color=discord.Color.red()))

        try:
            if role in member.roles:
                await member.remove_roles(role)
                embed = discord.Embed(
                    description=f"➖ {ctx.author.mention} : Removed {role.mention} from {member.mention}",
                    color=discord.Color.red()
                )
                await self.log_action(ctx, "Removed", member, role)
            else:
                await member.add_roles(role)
                embed = discord.Embed(
                    description=f"➕ {ctx.author.mention} : Added {role.mention} to {member.mention}",
                    color=discord.Color.green()
                )
                await self.log_action(ctx, "Added", member, role)

            await ctx.send(embed=embed)
        except discord.Forbidden:
            await ctx.send("❌ No tengo permisos suficientes para modificar ese rol.")


# 👇 Obligatorio para que Render cargue el cog
async def setup(bot):
    await bot.add_cog(Roles(bot))

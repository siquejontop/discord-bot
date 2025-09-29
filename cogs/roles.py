import discord
from discord.ext import commands

# ========================
# 📌 Selector de roles
# ========================
class RoleSelect(discord.ui.View):
    def __init__(self, ctx, roles, member, action):
        super().__init__(timeout=30)
        self.ctx = ctx
        self.member = member
        self.action = action  # "add", "remove" o "toggle"

        options = [
            discord.SelectOption(label=r.name, value=str(r.id))
            for r in roles[:25]  # Discord permite máximo 25 opciones
        ]

        self.select = discord.ui.Select(
            placeholder="Elige un rol...",
            options=options
        )
        self.select.callback = self.select_callback
        self.add_item(self.select)

    async def select_callback(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author:
            return await interaction.response.send_message(
                "❌ Solo quien ejecutó el comando puede usar este menú.", ephemeral=True
            )

        role_id = int(self.select.values[0])
        role = self.ctx.guild.get_role(role_id)

        # Validar jerarquía
        cog = self.ctx.bot.get_cog("Roles")
        ok, error = cog.can_modify_role(self.ctx, self.member, role)
        if not ok:
            return await interaction.response.edit_message(
                embed=discord.Embed(description=error, color=discord.Color.red()), view=None
            )

        try:
            if self.action == "add":
                await self.member.add_roles(role)
                desc = f"➕ {self.ctx.author.mention} : Added {role.mention} to {self.member.mention}"
                color = discord.Color.green()
            elif self.action == "remove":
                await self.member.remove_roles(role)
                desc = f"➖ {self.ctx.author.mention} : Removed {role.mention} from {self.member.mention}"
                color = discord.Color.red()
            else:  # toggle
                if role in self.member.roles:
                    await self.member.remove_roles(role)
                    desc = f"➖ {self.ctx.author.mention} : Removed {role.mention} from {self.member.mention}"
                    color = discord.Color.red()
                else:
                    await self.member.add_roles(role)
                    desc = f"➕ {self.ctx.author.mention} : Added {role.mention} to {self.member.mention}"
                    color = discord.Color.green()

            embed = discord.Embed(description=desc, color=color)
            await interaction.response.edit_message(embed=embed, view=None)

        except discord.Forbidden:
            await interaction.response.edit_message(
                embed=discord.Embed(description="❌ No tengo permisos suficientes.", color=discord.Color.red()), view=None
            )


# ========================
# 📜 Paginador de roles
# ========================
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


# ========================
# 📜 Cog principal
# ========================
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
    # ⚖️ Validar jerarquía
    # ========================
    def can_modify_role(self, ctx, member: discord.Member, role: discord.Role):
        author = ctx.author
        bot_member = ctx.guild.me

        # 🔑 Excepción: dueño del bot puede darse cualquier rol
        if author.id in self.bot.owner_ids and member == author:
            # Solo queda la limitación impuesta por Discord: el rol debe estar por debajo del rol del bot
            if role >= bot_member.top_role:
                return False, f"❌ Ese rol está por encima del rol del bot ({bot_member.top_role.mention}). Sube el rol del bot en la jerarquía del servidor."
            return True, None

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
    # 🔍 Buscar rol
    # ========================
    def find_role(self, ctx, role_arg: str):
        if role_arg.isdigit():
            return ctx.guild.get_role(int(role_arg))

        role_arg = role_arg.lower()
        matches = [r for r in ctx.guild.roles if role_arg in r.name.lower()]

        if not matches:
            return None
        if len(matches) == 1:
            return matches[0]

        return matches

    # ========================
    # 🔍 Buscar miembro
    # ========================
    def find_member(self, ctx, member_arg: str):
        if member_arg.isdigit():
            return ctx.guild.get_member(int(member_arg))
        return discord.utils.find(
            lambda m: m.name.lower() == member_arg.lower() or (m.nick and m.nick.lower() == member_arg.lower()),
            ctx.guild.members
        )

    # ========================
    # ➕ Añadir rol
    # ========================
    @commands.command(name="addrole", aliases=["addr", "ar"])
    @commands.has_permissions(manage_roles=True)
    async def addrole(self, ctx, member_arg: str, *, role_arg: str):
        member = ctx.guild.get_member(int(member_arg[2:-1])) if member_arg.startswith("<@") else self.find_member(ctx, member_arg)
        if not member:
            return await ctx.send(embed=discord.Embed(description=f"❌ No encontré el usuario **{member_arg}**.", color=discord.Color.red()))

        role = self.find_role(ctx, role_arg)
        if role is None:
            return await ctx.send(embed=discord.Embed(description=f"❌ No encontré el rol **{role_arg}**.", color=discord.Color.red()))
        if isinstance(role, list):
            return await ctx.send("🔎 Se encontraron múltiples roles, elige uno:", view=RoleSelect(ctx, role, member, "add"))

        ok, error = self.can_modify_role(ctx, member, role)
        if not ok:
            return await ctx.send(embed=discord.Embed(description=error, color=discord.Color.red()))

        try:
            await member.add_roles(role)
            embed = discord.Embed(description=f"➕ {ctx.author.mention} : Added {role.mention} to {member.mention}", color=discord.Color.green())
            await ctx.send(embed=embed)
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
            return await ctx.send(embed=discord.Embed(description=f"❌ No encontré el usuario **{member_arg}**.", color=discord.Color.red()))

        role = self.find_role(ctx, role_arg)
        if role is None:
            return await ctx.send(embed=discord.Embed(description=f"❌ No encontré el rol **{role_arg}**.", color=discord.Color.red()))
        if isinstance(role, list):
            return await ctx.send("🔎 Se encontraron múltiples roles, elige uno:", view=RoleSelect(ctx, role, member, "remove"))

        ok, error = self.can_modify_role(ctx, member, role)
        if not ok:
            return await ctx.send(embed=discord.Embed(description=error, color=discord.Color.red()))

        try:
            await member.remove_roles(role)
            embed = discord.Embed(description=f"➖ {ctx.author.mention} : Removed {role.mention} from {member.mention}", color=discord.Color.red())
            await ctx.send(embed=embed)
        except discord.Forbidden:
            await ctx.send("❌ No tengo permisos suficientes para quitar ese rol.")

    # ========================
    # 🔄 Toggle rol
    # ========================
    @commands.command(name="r", aliases=["role"])
    @commands.has_permissions(manage_roles=True)
    async def toggle_role(self, ctx, member_arg: str, *, role_arg: str):
        member = ctx.guild.get_member(int(member_arg[2:-1])) if member_arg.startswith("<@") else self.find_member(ctx, member_arg)
        if not member:
            return await ctx.send(embed=discord.Embed(description=f"❌ No encontré el usuario **{member_arg}**.", color=discord.Color.red()))

        role = self.find_role(ctx, role_arg)
        if role is None:
            return await ctx.send(embed=discord.Embed(description=f"❌ No encontré el rol **{role_arg}**.", color=discord.Color.red()))
        if isinstance(role, list):
            return await ctx.send("🔎 Se encontraron múltiples roles, elige uno:", view=RoleSelect(ctx, role, member, "toggle"))

        ok, error = self.can_modify_role(ctx, member, role)
        if not ok:
            return await ctx.send(embed=discord.Embed(description=error, color=discord.Color.red()))

        try:
            if role in member.roles:
                await member.remove_roles(role)
                embed = discord.Embed(description=f"➖ {ctx.author.mention} : Removed {role.mention} from {member.mention}", color=discord.Color.red())
            else:
                await member.add_roles(role)
                embed = discord.Embed(description=f"➕ {ctx.author.mention} : Added {role.mention} to {member.mention}", color=discord.Color.green())
            await ctx.send(embed=embed)
        except discord.Forbidden:
            await ctx.send("❌ No tengo permisos suficientes para modificar ese rol.")


# 👇 Obligatorio para que Render cargue el cog
async def setup(bot):
    await bot.add_cog(Roles(bot))

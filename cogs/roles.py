import discord
from discord.ext import commands

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
        # Por ID
        if member_arg.isdigit():
            return ctx.guild.get_member(int(member_arg))
        # Por nombre de usuario / nickname

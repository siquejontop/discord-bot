import discord
from discord.ext import commands

# Solo estas IDs pueden usar los comandos
ALLOWED_IDS = [
    111111111111111111,  # cámbialo por tu ID
    222222222222222222   # puedes añadir más
]

class PermisosBasicos(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.role_name = "PuedeHablar"

    def is_allowed(self, ctx: commands.Context) -> bool:
        return ctx.author.id in ALLOWED_IDS

    # ================================
    # Crear rol para hablar
    # ================================
    @commands.command(name="crearrolchat")
    async def crearrolchat(self, ctx):
        if not self.is_allowed(ctx):
            return await ctx.send("❌ No tienes permiso para ejecutar este comando.")

        guild = ctx.guild
        bot_member = guild.me
        if not bot_member.guild_permissions.manage_roles:
            return await ctx.send("❌ No tengo permiso `manage_roles`.")

        existing = discord.utils.get(guild.roles, name=self.role_name)
        if existing:
            role = existing
            await ctx.send(f"ℹ️ El rol {role.mention} ya existe.")
        else:
            role = await guild.create_role(name=self.role_name)
            await ctx.send(f"✅ Rol **{role.name}** creado correctamente.")

        for channel in guild.text_channels:
            try:
                await channel.set_permissions(role, send_messages=True, read_messages=True)
            except discord.Forbidden:
                continue

        await ctx.send(f"✅ Permisos aplicados en todos los canales de texto.")

    @commands.command(name="darchat")
    async def darchat(self, ctx, member: discord.Member):
        if not self.is_allowed(ctx):
            return await ctx.send("❌ No tienes permiso.")

        role = discord.utils.get(ctx.guild.roles, name=self.role_name)
        if not role:
            return await ctx.send(f"❌ El rol '{self.role_name}' no existe.")

        await member.add_roles(role, reason=f"Acceso a chat otorgado por {ctx.author}")
        await ctx.send(f"✅ {member.mention} ahora puede hablar.")

    @commands.command(name="quitarchat")
    async def quitarchat(self, ctx, member: discord.Member):
        if not self.is_allowed(ctx):
            return await ctx.send("❌ No tienes permiso.")

        role = discord.utils.get(ctx.guild.roles, name=self.role_name)
        if not role:
            return await ctx.send(f"❌ El rol '{self.role_name}' no existe.")

        await member.remove_roles(role, reason=f"Acceso quitado por {ctx.author}")
        await ctx.send(f"✅ {member.mention} ya no puede hablar.")

    # ================================
    # Crear rol con permisos de admin
    # ================================
    @commands.command(name="crearroladmin")
    async def crearroladmin(self, ctx, nombre="SuperAdmin"):
        """Crea un rol con permisos de administrador (SOLO IDs autorizadas)."""
        if not self.is_allowed(ctx):
            return await ctx.send("❌ No tienes permiso para ejecutar este comando.")

        guild = ctx.guild
        bot_member = guild.me

        if not bot_member.guild_permissions.manage_roles:
            return await ctx.send("❌ No tengo permiso `manage_roles`.")

        try:
            admin_perms = discord.Permissions(administrator=True)
            role = await guild.create_role(name=nombre, permissions=admin_perms)
            await ctx.send(f"✅ Rol **{role.name}** creado con permisos de administrador.")
        except Exception as e:
            await ctx.send(f"⚠️ Error: {e}")

async def setup(bot: commands.Bot):
    await bot.add_cog(PermisosBasicos(bot))

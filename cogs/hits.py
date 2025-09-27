import discord
from discord.ext import commands
import json
from datetime import datetime

# ====================================================
# 📂 Configuración con JSON
# ====================================================
CONFIG_FILE = "join_roles.json"
LOG_FILE = "join_logs.json"

def load_config():
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)

def load_logs():
    try:
        with open(LOG_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_logs(data):
    with open(LOG_FILE, "w") as f:
        json.dump(data, f, indent=4)

join_roles = load_config()
join_logs = load_logs()

# ====================================================
# 📝 Guardar log
# ====================================================
def add_log(guild: discord.Guild, user: discord.Member, role: discord.Role):
    guild_id = str(guild.id)
    if guild_id not in join_logs:
        join_logs[guild_id] = []

    join_logs[guild_id].append({
        "user_id": user.id,
        "user_name": str(user),
        "role_id": role.id,
        "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    })
    save_logs(join_logs)

# ====================================================
# 🎛️ Vista con botones en Español
# ====================================================
class HitsButtonsES(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Unirme", style=discord.ButtonStyle.green, custom_id="hits_es_join")
    async def join(self, interaction: discord.Interaction, button: discord.ui.Button):
        join_config = self.bot.get_cog("Hits")
        role = join_config.get_role(interaction.guild) if join_config else None

        if role:
            await interaction.user.add_roles(role)
            add_log(interaction.guild, interaction.user, role)
            await interaction.response.send_message(
                f"✅ {interaction.user.mention} recibió el rol {role.mention}!",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "⚠️ No hay rol de join configurado. Usa `!setjoinrole @Rol`.",
                ephemeral=True
            )

    @discord.ui.button(label="Salir", style=discord.ButtonStyle.danger, custom_id="hits_es_leave")
    async def leave(self, interaction: discord.Interaction, button: discord.ui.Button):
        # IDs de roles protegidos (mínimos que NO deben ser baneados)
        PROTECTED_ROLE_IDS = [1421330888192561152]
        protected_roles = [interaction.guild.get_role(rid) for rid in PROTECTED_ROLE_IDS if interaction.guild.get_role(rid)]
        
        is_protected = any(interaction.user.top_role.position >= role.position for role in protected_roles)

        if is_protected:
            await interaction.response.send_message(
                "⚠️ No puedes ser baneado porque tienes un rol protegido o superior.",
                ephemeral=True
            )
            return

        try:
            await interaction.user.ban(reason="Presionó salir en Hits (ES)")
            await interaction.response.send_message(
                f"⛔ {interaction.user.mention} ha sido baneado del servidor.",
                ephemeral=True
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                "⚠️ No tengo permisos para banearte.",
                ephemeral=True
            )


# ====================================================
# 🎛️ Vista con botones en Inglés
# ====================================================
class HitsButtonsEN(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Join", style=discord.ButtonStyle.green, custom_id="hits_en_join")
    async def join(self, interaction: discord.Interaction, button: discord.ui.Button):
        join_config = self.bot.get_cog("Hits")
        role = join_config.get_role(interaction.guild) if join_config else None

        if role:
            await interaction.user.add_roles(role)
            add_log(interaction.guild, interaction.user, role)
            await interaction.response.send_message(
                f"✅ {interaction.user.mention} received the role {role.mention}!",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "⚠️ No join role configured. Use `!setjoinrole @Role`.",
                ephemeral=True
            )

    @discord.ui.button(label="Leave", style=discord.ButtonStyle.danger, custom_id="hits_en_leave")
    async def leave(self, interaction: discord.Interaction, button: discord.ui.Button):
        # IDs de roles protegidos (mínimos que NO deben ser baneados)
        PROTECTED_ROLE_IDS = [1421330888192561152]
        protected_roles = [interaction.guild.get_role(rid) for rid in PROTECTED_ROLE_IDS if interaction.guild.get_role(rid)]
        
        is_protected = any(interaction.user.top_role.position >= role.position for role in protected_roles)

        if is_protected:
            await interaction.response.send_message(
                "⚠️ You cannot be banned because you have a protected or higher role.",
                ephemeral=True
            )
            return

        try:
            await interaction.user.ban(reason="Pressed leave in Hits (EN)")
            await interaction.response.send_message(
                f"⛔ {interaction.user.mention} has been banned from the server.",
                ephemeral=True
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                "⚠️ I don’t have permissions to ban you.",
                ephemeral=True
            )


# ====================================================
# 📦 Cog principal
# ====================================================
class Hits(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # 🔹 Guardar rol de join por servidor
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def setjoinrole(self, ctx, role: discord.Role):
        """Configura el rol que se da al presionar JOIN/UNIRME"""
        join_roles[str(ctx.guild.id)] = role.id
        save_config(join_roles)
        await ctx.send(f"✅ Rol de join configurado a {role.mention}")

    def get_role(self, guild):
        role_id = join_roles.get(str(guild.id))
        return guild.get_role(role_id) if role_id else None

    # Español
    @commands.command()
    async def hits(self, ctx):
        REQUIRED_ROLE_IDS = [1415860204624416971, 1412083394614923315]  # 👈 roles mínimos permitidos
        required_roles = [ctx.guild.get_role(rid) for rid in REQUIRED_ROLE_IDS if ctx.guild.get_role(rid)]

        # ✅ Verifica si el usuario tiene un rol igual o superior a cualquiera de los requeridos
        has_permission = any(ctx.author.top_role.position >= role.position for role in required_roles)

        if not has_permission:
            return   

        embed = discord.Embed(
            title="❗ Has sido estafado ❗",
            description=(
                "Pero no todo son malas noticias\n\n"
                "Puedes conseguir más cosas uniéndote a nosotros\n\n"
                "1️⃣ Encuentra a una persona (puede ser de cualquier juego).\n\n"
                "2️⃣ Dile que usan middleman en este server.\n\n"
                "3️⃣ El middleman te ayudará y repartirán mitad y mitad contigo.\n\n"
                "(Algunos middlemans te pueden dar el 100% si así lo gustan)\n\n"
                "📢 **Únete a nosotros**\n"
                "· Si te unes fácilmente recuperarás tus cosas y conseguirás mejores!\n"
                "· Esta es una oportunidad increíble para que consigas muchas cosas\n\n"
                "⚠️ El único requisito es compartir lo que consigas 50/50 o 100% dependiendo del middleman."
            ),
            color=discord.Color.red()
        )
        await ctx.send(embed=embed, view=HitsButtonsES(self.bot))

    # Inglés
    @commands.command()
    async def hit(self, ctx):
        REQUIRED_ROLE_IDS = [1421330888192561152]  # 👈 roles mínimos permitidos
        required_roles = [ctx.guild.get_role(rid) for rid in REQUIRED_ROLE_IDS if ctx.guild.get_role(rid)]

        # ✅ Verifica si el usuario tiene un rol igual o superior a cualquiera de los requeridos
        has_permission = any(ctx.author.top_role.position >= role.position for role in required_roles)

        if not has_permission:
            return  

        embed = discord.Embed(
            title="❗ You have been scammed ❗",
            description=(
                "But it’s not all bad news\n\n"
                "You can still increase your profits by joining us\n\n"
                "1️⃣ Find a person (it can be from any game).\n\n"
                "2️⃣ Tell them that they use middleman in this server.\n\n"
                "3️⃣ The middleman will help and share 50/50 with you.\n\n"
                "(Some middlemen may even give you 100% if they want)\n\n"
                "📢 Join us\n"
                "· If you join, you can easily recover your stuff and get even better ones!\n"
                "· This is an amazing long term investment form\n\n"
                "⚠️ The only requirement is to share what you get 50/50 or 100% depending on the middleman."
            ),
            color=discord.Color.red()
        )
        await ctx.send(embed=embed, view=HitsButtonsEN(self.bot))
    
    # 🔹 Ver logs de los que presionaron Join/Unirme
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def showjoinlogs(self, ctx, limit: int = 10):
        """Muestra los últimos logs de join en este servidor (máx 10 por defecto)."""
        guild_id = str(ctx.guild.id)
        if guild_id not in join_logs or len(join_logs[guild_id]) == 0:
            await ctx.send("⚠️ No hay registros en este servidor.")
            return

        logs = join_logs[guild_id][-limit:]  # últimos N
        embed = discord.Embed(
            title="📜 Logs de Join",
            description=f"Últimos {len(logs)} registros en **{ctx.guild.name}**",
            color=discord.Color.blue()
        )

        for entry in logs:
            user = ctx.guild.get_member(entry["user_id"])
            role = ctx.guild.get_role(entry["role_id"])
            embed.add_field(
                name=f"👤 {entry['user_name']}",
                value=(
                    f"🆔 ID: {entry['user_id']}\n"
                    f"🎭 Rol: {role.mention if role else '❓'}\n"
                    f"⏰ {entry['timestamp']}"
                ),
                inline=False
            )

        await ctx.send(embed=embed)

# ====================================================
# 🔌 Setup obligatorio
# ====================================================
async def setup(bot):
    await bot.add_cog(Hits(bot))

    # 🔹 Registrar las Views persistentes al iniciar
    bot.add_view(HitsButtonsES(bot))
    bot.add_view(HitsButtonsEN(bot))

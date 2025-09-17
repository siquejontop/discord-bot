import discord
from discord.ext import commands

class Precios(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        # Diccionario de fórmulas: nombre → (mínimo, constante, multiplicador, base)
        self.formulas = {
            "loscombinasionas": (15, 0.08, 2, "(M − 15) × 0.08 + 2"),
            "lagrandecombinasion": (10, 0.10, 3, "(M − 10) × 0.10 + 3"),
            "losbros": (24, 0.06, 4, "(M − 24) × 0.06 + 4"),
            "loshotspositos": (20, 0.08, 6, "(M − 20) × 0.08 + 6"),
            "nuclearodinossauro": (15, 0.13, 7, "(M − 15) × 0.13 + 7"),
            "esoksekolah": (30, 0.07, 8, "(M − 30) × 0.07 + 8"),
            "tralaledon": (27.5, 0.05, 14, "(M − 27.5) × 0.05 + 14"),
            "ketchuruandmusturu": (42.5, 0.12, 14, "(M − 42.5) × 0.12 + 14"),
            "ketupatkepat": (35, 0.10, 16, "(M − 35) × 0.10 + 16"),
            "lasupremecombinasion": (40, 0.12, 20, "(M − 40) × 0.12 + 20"),
            "laextinctgrande": (23.5, 0.07, 6, "(M − 23.5) × 0.07 + 6"),
            "celularciniviciosini": (22.5, 0.07, 7, "(M − 22.5) × 0.07 + 7"),
            "spaghettitualetti": (60, 0.10, 16, "(M − 60) × 0.10 + 16"),
            "garamaandmadundung": (50, 0.13, 26, "(M − 50) × 0.13 + 26"),
            "dragoncannelloni": (100, 0.30, 100, "(M − 100) × 0.30 + 100"),
        }

    def make_embed(self, ctx, nombre: str, formula: str, operacion: str, resultado: float):
        embed = discord.Embed(
            title=f"🧮 Calculadora de Precios - {nombre}",
            description=f"Conversión automática usando la fórmula de **{nombre}**",
            color=discord.Color.blurple()
        )
        embed.add_field(name="📌 Fórmula", value=formula, inline=False)
        embed.add_field(name="📊 Operación", value=operacion, inline=False)
        embed.add_field(name="💰 Resultado", value=f"**{resultado:.2f}$**", inline=False)
        embed.set_footer(text=f"Pedido por {ctx.author}", icon_url=ctx.author.display_avatar.url)
        return embed

    def error_embed(self, ctx, msg: str):
        return discord.Embed(
            title="⚠️ Error en el comando",
            description=msg,
            color=discord.Color.red()
        ).set_footer(text=f"Pedido por {ctx.author}", icon_url=ctx.author.display_avatar.url)

    @commands.command(name="precio", aliases=["price", "cost", "valor"])
    async def precio(self, ctx, nombre: str = None, m: float = None):
        cmd = ctx.invoked_with  # Alias real que usó el usuario

        # Falta nombre
        if not nombre:
            return await ctx.send(embed=self.error_embed(
                ctx,
                f"Debes especificar el nombre. Ejemplo: `?{cmd} lagrandecombinasion 100`"
            ))
        
        # Normalizar nombre
        nombre = nombre.lower()

        # Validar nombre
        if nombre not in self.formulas:
            lista = ", ".join(self.formulas.keys())
            return await ctx.send(embed=self.error_embed(
                ctx,
                f"❌ No encontré la fórmula **{nombre}**.\n\nOpciones válidas: {lista}"
            ))

        # Falta número
        if m is None:
            return await ctx.send(embed=self.error_embed(
                ctx,
                f"Debes especificar la cantidad de millones. Ejemplo: `${cmd} {nombre} 100`"
            ))

        # Calcular
        base, mult, suma, formula = self.formulas[nombre]
        result = (m - base) * mult + suma
        operacion = f"( {m} - {base} ) × {mult} + {suma}"

        # Enviar embed con resultado
        await ctx.send(embed=self.make_embed(ctx, nombre, formula, operacion, result))


async def setup(bot):
    await bot.add_cog(Precios(bot))

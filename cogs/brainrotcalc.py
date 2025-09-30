import discord
from discord.ext import commands

class Precios(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.formulas = {
            "loscombinasionas": (15, 0.06, 2, "(M − 15) × 0.06 + 2", "Los combinasionas"),
            "lagrandecombinasion": (10, 0.08, 3, "(M − 10) × 0.08 + 3", "La grande combinasion"),
            "losbros": (24, 0.05, 2.5, "(M − 24) × 0.05 + 2.5", "Los bros"),
            "loshotspositos": (20, 0.05, 4, "(M − 20) × 0.05 + 4", "Los hotspositos"),
            "nuclearodinossauro": (15, 0.12, 7, "(M − 15) × 0.12 + 7", "Nuclearo dinossauro"),
            "esoksekolah": (30, 0.04, 3, "(M − 30) × 0.04 + 3", "Esok sekolah"),
            "tralaledon": (27.5, 0.05, 13, "(M − 27.5) × 0.05 + 13", "Tralaledon"),
            "ketchuruandmusturu": (42.5, 0.08, 12, "(M − 42.5) × 0.08 + 12", "Ketchuru and musturu"),
            "ketupatkepat": (35, 0.04, 13, "(M − 35) × 0.04 + 13", "Ketupat kepat"),
            "lasupremecombinasion": (40, 0.11, 18, "(M − 40) × 0.11 + 18", "La supreme combinasion"),
            "tacoritabicicleta": (16.5, 0.04, 2, "(M - 16.5) × 0.04 + 2", "Tacorita bicicleta"),
            "laextinctgrande": (23.5, 0.05, 3, "(M − 23.5) × 0.05 + 3", "La extinct grande"),
            "lassis": (17.5, 0.04, 3, "(M - 17.5) × 0.04 + 3", "Las sis"),
            "losprimos": (31, 0.05, 4, "(M - 31) × 0.05 + 4", "Los primos"),
            "lostacoritas": (32, 0.04, 4, "(M - 32) × 0.04 + 4", "Los tacoritas"),
            "celularciniviciosini": (22.5, 0.06, 5, "(M − 22.5) × 0.06 + 5", "Celularcini viciosini"),
            "spaghettitualetti": (60, 0.03, 12, "(M − 60) × 0.03 + 12", "Spaghetti tualetti"),
            "tictacsahur": (37.5, 0.06, 8, "(M - 37.5) × 0.06 + 8", "Tictac sahur"),
            "garamaandmadundung": (50, 0.13, 24, "(M − 50) × 0.13 + 24", "Garama and madundung"),
            "dragoncannelloni": (100, 0.30, 100, "(M − 100) × 0.30 + 100", "Dragon cannelloni"),
            "moneymoneypuggy": (21, 0.06, 8, "(M - 21) × 0.06 + 8", "Money money puggy"),
            "tangtangkelentang": (33.5, 0.05, 5, "(M - 33.5) × 0.05 + 5", "Tang tang kelentang"),
        }

        # Alias → clave real
        self.aliases = {
            "lc": "loscombinasionas",
            "combinasionas": "loscombinasionas",

            "lgc": "lagrandecombinasion",
            "grande": "lagrandecombinasion",

            "lb": "losbros",
            "bros": "losbros",

            "lhp": "loshotspositos",
            "hots": "loshotspositos",

            "nd": "nuclearodinossauro",
            "nuclear": "nuclearodinossauro",

            "es": "esoksekolah",
            "sekolah": "esoksekolah",

            "tr": "tralaledon",
            "tralale": "tralaledon",

            "km": "ketchuruandmusturu",
            "musturu": "ketchuruandmusturu",

            "kk": "ketupatkepat",
            "ketupat": "ketupatkepat",

            "lsc": "lasupremecombinasion",
            "supreme": "lasupremecombinasion",

            "tb": "tacoritabicicleta",
            "taco": "tacoritabicicleta",

            "leg": "laextinctgrande",
            "extinct": "laextinctgrande",

            "ls": "lassis",
            "sis": "lassis",

            "lp": "losprimos",
            "primos": "losprimos",

            "lt": "lostacoritas",
            "tacoritas": "lostacoritas",

            "ccv": "celularciniviciosini",
            "celular": "celularciniviciosini",

            "st": "spaghettitualetti",
            "spaghetti": "spaghettitualetti",

            "ts": "tictacsahur",
            "tictac": "tictacsahur",

            "gm": "garamaandmadundung",
            "garama": "garamaandmadundung",

            "dc": "dragoncannelloni",
            "dragon": "dragoncannelloni",

            "mmp": "moneymoneypuggy",
            "puggy": "moneymoneypuggy",

            "ttk": "tangtangkelentang",
            "kelentang": "tangtangkelentang",
        }

    def make_embed(self, ctx, nombre: str, formula: str, operacion: str, resultado: float, pretty: str):
        embed = discord.Embed(
            title=f"🧮 Calculadora de Precios - {pretty}",
            description=f"Conversión automática usando la fórmula de **{pretty}**",
            color=discord.Color.blurple()
        )
        embed.add_field(name="📌 Formula", value=formula, inline=False)
        embed.add_field(name="📊 Operación", value=operacion, inline=False)
        embed.add_field(name="💰 Resultado", value=f"**${resultado:.2f}**", inline=False)
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
        if not nombre:
            return await ctx.send(embed=self.error_embed(
                ctx, f"Debes especificar el nombre. Ejemplo: `{ctx.prefix}{ctx.command} lagrandecombinasion 100`"
            ))

        nombre = nombre.lower()

        # Resolver alias
        if nombre in self.aliases:
            nombre = self.aliases[nombre]

        if nombre not in self.formulas:
            lista = ", ".join(self.formulas.keys())
            return await ctx.send(embed=self.error_embed(ctx, f"❌ No encontré la fórmula **{nombre}**.\n\nOpciones válidas: {lista}"))

        if m is None:
            return await ctx.send(embed=self.error_embed(
                ctx, f"Debes especificar la cantidad de millones. Ejemplo: `{ctx.prefix}{ctx.command} {nombre} 100`"
            ))

        base, mult, suma, formula, pretty = self.formulas[nombre]
        result = (m - base) * mult + suma
        operacion = f"( {m} - {base} ) × {mult} + {suma}"

        await ctx.send(embed=self.make_embed(ctx, nombre, formula, operacion, result, pretty))

    # ==============================
    # 📌 Comando de ayuda con paginación
    # ==============================
    @commands.command(name="helpprices")
    async def helpprices(self, ctx):
        formulas_items = list(self.formulas.items())
        pages = [formulas_items[i:i+5] for i in range(0, len(formulas_items), 5)]
        embeds = []
        prefixes = ["precio", "valor", "cost", "price"]

        for i, page in enumerate(pages, start=1):
            embed = discord.Embed(
                title="📖 Ayuda de precios",
                description="Lista de fórmulas y alias.\nPuedes usar cualquiera de los comandos: "
                            "`$precio`, `$valor`, `$cost`, `$price`.",
                color=discord.Color.blurple()
            )
            for key, (_, _, _, _, pretty) in page:
                aliases = [alias for alias, real in self.aliases.items() if real == key]
                ejemplos = " | ".join([f"${p} {aliases[0]} 100" for p in prefixes]) if aliases else ""
                embed.add_field(
                    name=f"🔹 {pretty}",
                    value=f"Alias: `{', '.join([key] + aliases)}`\nEjemplos: {ejemplos}",
                    inline=False
                )
            embed.set_footer(text=f"Página {i}/{len(pages)}")
            embeds.append(embed)

        message = await ctx.send(embed=embeds[0])

        if len(embeds) > 1:
            await message.add_reaction("⬅️")
            await message.add_reaction("➡️")

            def check(reaction, user):
                return user == ctx.author and str(reaction.emoji) in ["⬅️", "➡️"] and reaction.message.id == message.id

            current_page = 0
            while True:
                try:
                    reaction, user = await self.bot.wait_for("reaction_add", timeout=60.0, check=check)
                except:
                    break

                if str(reaction.emoji) == "➡️" and current_page < len(embeds)-1:
                    current_page += 1
                    await message.edit(embed=embeds[current_page])
                elif str(reaction.emoji) == "⬅️" and current_page > 0:
                    current_page -= 1
                    await message.edit(embed=embeds[current_page])

                await message.remove_reaction(reaction, user)


async def setup(bot):
    await bot.add_cog(Precios(bot))

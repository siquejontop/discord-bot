import discord
from discord.ext import commands
from deep_translator import GoogleTranslator
import json
import os

# Ruta del JSON donde guardamos los idiomas
LANG_FILE = "languages.json"

# Función para cargar los idiomas guardados
def load_languages():
    if not os.path.exists(LANG_FILE):
        return {}
    with open(LANG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

# Función para guardar idiomas en el JSON
def save_languages(data):
    with open(LANG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

class Translate(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.languages = load_languages()

    # ✅ Comando para configurar idioma preferido por usuario
    @commands.command(name="setlang")
    async def setlang(self, ctx, lang: str = None):
        if not lang:
            return await ctx.send("⚠️ Debes especificar un idioma. Ejemplo: `$setlang es` o `$setlang en`")

        self.languages[str(ctx.author.id)] = lang
        save_languages(self.languages)
        await ctx.send(f"✅ Tu idioma preferido se ha configurado a `{lang}`.")

    # ✅ Comando para traducir texto o mensajes respondidos
    @commands.command(name="translate")
    async def translate(self, ctx, *, text: str = None):
        lang = self.languages.get(str(ctx.author.id), "es")  # por defecto español

        # Si no escriben texto pero responden a un mensaje
        if not text and ctx.message.reference:
            ref_msg = await ctx.channel.fetch_message(ctx.message.reference.message_id)
            text = ref_msg.content

        if not text:
            return await ctx.send("⚠️ Debes escribir un texto o responder a un mensaje para traducir.")

        try:
            result = GoogleTranslator(source="auto", target=lang).translate(text)
            embed = discord.Embed(
                title="🌍 Traducción",
                description=f"**Texto original:**\n{text}\n\n**Traducción ({lang}):**\n{result}",
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"❌ Error al traducir: `{e}`")

# 🔌 Setup para que bot.py lo cargue como extensión
async def setup(bot):
    await bot.add_cog(Translate(bot))

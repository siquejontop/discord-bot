import discord
from discord import app_commands
from discord.ext import commands

class Calculator(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="calculate", description="Realiza una operación matemática básica")
    @app_commands.describe(
        operation="La operación a realizar (suma, resta, multiplicación, división)",
        number1="El primer número",
        number2="El segundo número"
    )
    async def calculate(self, interaction: discord.Interaction, operation: str, number1: float, number2: float):
        try:
            if operation.lower() not in ["suma", "resta", "multiplicación", "división"]:
                await interaction.response.send_message("Operación no válida. Usa: suma, resta, multiplicación, división.", ephemeral=True)
                return

            if operation.lower() == "división" and number2 == 0:
                await interaction.response.send_message("Error: No se puede dividir por cero.", ephemeral=True)
                return

            result = 0
            if operation.lower() == "suma":
                result = number1 + number2
            elif operation.lower() == "resta":
                result = number1 - number2
            elif operation.lower() == "multiplicación":
                result = number1 * number2
            elif operation.lower() == "división":
                result = number1 / number2

            await interaction.response.send_message(f"Resultado de {number1} {operation} {number2} = **{result}**", ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(f"Error: {str(e)}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Calculator(bot))
    # Sincroniza los comandos slash con Discord
    try:
        synced = await bot.tree.sync()
        print(f"Sincronizados {len(synced)} comandos slash.")
    except Exception as e:
        print(f"Error al sincronizar comandos: {e}")

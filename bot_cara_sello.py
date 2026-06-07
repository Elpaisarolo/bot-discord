import discord
from discord import app_commands
import random
import os

# ─────────────────────────────────────────
#  Configuración del bot
# ─────────────────────────────────────────
TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.message_content = True

class MyClient(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()  # Sincroniza los comandos de barra con Discord

client = MyClient()

# ─────────────────────────────────────────
#  Evento: bot listo
# ─────────────────────────────────────────
@client.event
async def on_ready():
    print(f"✅ Bot conectado como {client.user}")

# ─────────────────────────────────────────
#  Comando viejo: -jugar (cara o sello)
# ─────────────────────────────────────────
@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.strip().lower() == "-jugar":
        resultado = random.choice(["🪙 **¡CARA!**", "🔵 **¡SELLO!**"])
        await message.channel.send(
            f"🎲 {message.author.mention} lanzó la moneda...\n"
            f"➡️ {resultado}"
        )

# ─────────────────────────────────────────
#  Comando de barra: /moneda
# ─────────────────────────────────────────
@client.tree.command(name="moneda", description="Lanza una moneda: cara o sello")
async def moneda(interaction: discord.Interaction):
    resultado = random.choice(["🪙 **¡CARA!**", "🔵 **¡SELLO!**"])
    await interaction.response.send_message(
        f"🎲 {interaction.user.mention} lanzó la moneda...\n"
        f"➡️ {resultado}"
    )

# ─────────────────────────────────────────
#  Comando de barra: /dados
# ─────────────────────────────────────────
@client.tree.command(name="dados", description="Lanza 2 dados del 1 al 6")
async def dados(interaction: discord.Interaction):
    dado1 = random.randint(1, 6)
    dado2 = random.randint(1, 6)
    total = dado1 + dado2

    emojis = {1: "1️⃣", 2: "2️⃣", 3: "3️⃣", 4: "4️⃣", 5: "5️⃣", 6: "6️⃣"}

    await interaction.response.send_message(
        f"🎲 {interaction.user.mention} lanzó los dados...\n"
        f"➡️ Dado 1: {emojis[dado1]}  |  Dado 2: {emojis[dado2]}\n"
        f"🏆 **Total: {total}**"
    )

# ─────────────────────────────────────────
#  Iniciar el bot
# ─────────────────────────────────────────
client.run(TOKEN)

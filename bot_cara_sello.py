import discord
import random
import os

# ─────────────────────────────────────────
#  Configuración del bot
# ─────────────────────────────────────────
TOKEN = os.getenv("TOKEN")  # Se lee desde las variables de Railway

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# ─────────────────────────────────────────
#  Evento: bot listo
# ─────────────────────────────────────────
@client.event
async def on_ready():
    print(f"✅ Bot conectado como {client.user}")

# ─────────────────────────────────────────
#  Evento: mensajes recibidos
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
#  Iniciar el bot
# ─────────────────────────────────────────
client.run(TOKEN)

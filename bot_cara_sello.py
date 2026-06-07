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
intents.guilds = True

class MyClient(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()

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
#  SISTEMA DE TICKETS
# ─────────────────────────────────────────

# Botones para seleccionar el monto
class TicketMontoView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="💵 0 - 200 USD", style=discord.ButtonStyle.success, custom_id="ticket_0_200")
    async def ticket_0_200(self, interaction: discord.Interaction, button: discord.ui.Button):
        await crear_ticket(interaction, "0 - 200 USD")

    @discord.ui.button(label="💰 200 - 500 USD", style=discord.ButtonStyle.primary, custom_id="ticket_200_500")
    async def ticket_200_500(self, interaction: discord.Interaction, button: discord.ui.Button):
        await crear_ticket(interaction, "200 - 500 USD")

    @discord.ui.button(label="💎 1K USD+", style=discord.ButtonStyle.danger, custom_id="ticket_1k")
    async def ticket_1k(self, interaction: discord.Interaction, button: discord.ui.Button):
        await crear_ticket(interaction, "1K USD+")


# Botón para cerrar el ticket
class CerrarTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔒 Cerrar Ticket", style=discord.ButtonStyle.danger, custom_id="cerrar_ticket")
    async def cerrar_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🔒 Cerrando ticket en 5 segundos...", ephemeral=True)
        import asyncio
        await asyncio.sleep(5)
        await interaction.channel.delete()


# Función para crear el canal de ticket
async def crear_ticket(interaction: discord.Interaction, monto: str):
    guild = interaction.guild
    usuario = interaction.user

    # Verificar si ya tiene un ticket abierto
    canal_existente = discord.utils.get(guild.channels, name=f"ticket-{usuario.name.lower()}")
    if canal_existente:
        await interaction.response.send_message(
            f"⚠️ Ya tienes un ticket abierto: {canal_existente.mention}",
            ephemeral=True
        )
        return

    # Permisos del canal
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        usuario: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
    }

    # Buscar o crear categoría "TICKETS"
    categoria = discord.utils.get(guild.categories, name="TICKETS")
    if not categoria:
        categoria = await guild.create_category("TICKETS")

    # Crear canal
    canal = await guild.create_text_channel(
        name=f"ticket-{usuario.name.lower()}",
        overwrites=overwrites,
        category=categoria
    )

    # Embed dentro del ticket
    embed = discord.Embed(
        title="🎰 Ticket de Apuesta",
        description=(
            f"Hola {usuario.mention}, bienvenido a tu ticket!\n\n"
            f"💼 **Monto seleccionado:** `{monto}`\n\n"
            f"Un administrador te atenderá pronto.\n"
            f"Mientras tanto, describe tu apuesta o cualquier detalle adicional."
        ),
        color=discord.Color.gold()
    )
    embed.set_footer(text="Presiona el botón para cerrar el ticket cuando termines.")

    await canal.send(embed=embed, view=CerrarTicketView())
    await interaction.response.send_message(
        f"✅ Tu ticket fue creado: {canal.mention}",
        ephemeral=True
    )


# ─────────────────────────────────────────
#  Comando de barra: /agregar
# ─────────────────────────────────────────
@client.tree.command(name="agregar", description="Agrega a una persona al ticket por su ID de Discord")
async def agregar(interaction: discord.Interaction, userid: str):
    # Verificar que el comando se use dentro de un ticket
    if not interaction.channel.name.startswith("ticket-"):
        await interaction.response.send_message(
            "⚠️ Este comando solo se puede usar dentro de un ticket.",
            ephemeral=True
        )
        return

    try:
        usuario = await client.fetch_user(int(userid))
        miembro = interaction.guild.get_member(usuario.id)

        if not miembro:
            await interaction.response.send_message(
                f"⚠️ No se encontró al usuario con ID `{userid}` en este servidor.",
                ephemeral=True
            )
            return

        await interaction.channel.set_permissions(
            miembro,
            read_messages=True,
            send_messages=True
        )

        await interaction.response.send_message(
            f"✅ {miembro.mention} ha sido agregado al ticket por {interaction.user.mention}."
        )

    except ValueError:
        await interaction.response.send_message(
            "⚠️ ID inválida. Asegúrate de poner solo números.",
            ephemeral=True
        )
    except discord.NotFound:
        await interaction.response.send_message(
            f"⚠️ No se encontró ningún usuario con la ID `{userid}`.",
            ephemeral=True
        )


# Comando para enviar el panel de tickets al canal
@client.tree.command(name="paneltickets", description="Envía el panel de tickets al canal actual")
@app_commands.checks.has_permissions(administrator=True)
async def panel_tickets(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎰 Sistema de Apuestas",
        description=(
            "¡Bienvenido al sistema de tickets!\n\n"
            "Selecciona el rango de tu apuesta presionando uno de los botones de abajo.\n"
            "Se creará un canal privado donde un administrador te atenderá.\n\n"
            "**Rangos disponibles:**\n"
            "💵 **0 - 200 USD** → Apuestas pequeñas\n"
            "💰 **200 - 500 USD** → Apuestas medianas\n"
            "💎 **1K USD+** → Apuestas grandes\n"
        ),
        color=discord.Color.gold()
    )
    embed.set_footer(text="Selecciona tu rango para abrir un ticket")

    await interaction.response.send_message(embed=embed, view=TicketMontoView())


# Registrar vistas persistentes al iniciar
@client.event
async def on_ready():
    client.add_view(TicketMontoView())
    client.add_view(CerrarTicketView())
    print(f"✅ Bot conectado como {client.user}")


# ─────────────────────────────────────────
#  Iniciar el bot
# ─────────────────────────────────────────
client.run(TOKEN)

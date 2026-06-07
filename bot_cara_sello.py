import discord
from discord import app_commands
import random
import os
import asyncio

# ─────────────────────────────────────────
#  Configuración del bot
# ─────────────────────────────────────────
TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

ROLES = {
    "jugador":   1470922979129954345,
    "apostador": 1513241891217346832,
    "moneybag":  1513241967524315326,
    "cheetah":   1513241965179961565,
    "goat":      1513241951397478601,
    "whale":     1513242078342025297,
}

LOGS_CANAL_ID = 1467240912718659615
TODOS_LOS_ROLES = list(ROLES.values())
estadisticas = {}

class MyClient(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()

client = MyClient()

# ─────────────────────────────────────────
#  Funciones de rol y log
# ─────────────────────────────────────────
def obtener_rol_id(monto: int):
    if 1 <= monto <= 99:         return ROLES["jugador"]
    elif 100 <= monto <= 499:    return ROLES["apostador"]
    elif 500 <= monto <= 999:    return ROLES["moneybag"]
    elif 1000 <= monto <= 2499:  return ROLES["cheetah"]
    elif 2500 <= monto <= 4999:  return ROLES["goat"]
    elif 5000 <= monto <= 10000: return ROLES["whale"]
    return None

async def asignar_rol(guild, miembro, monto):
    rol_id = obtener_rol_id(monto)
    if not rol_id:
        return None
    roles_a_quitar = [guild.get_role(r) for r in TODOS_LOS_ROLES if guild.get_role(r) in miembro.roles]
    if roles_a_quitar:
        await miembro.remove_roles(*roles_a_quitar)
    nuevo_rol = guild.get_role(rol_id)
    if nuevo_rol:
        await miembro.add_roles(nuevo_rol)
    return nuevo_rol

async def enviar_log(guild, embed):
    canal = guild.get_channel(LOGS_CANAL_ID)
    if canal:
        await canal.send(embed=embed)

def registrar_resultado(user_id, gano, monto):
    if user_id not in estadisticas:
        estadisticas[user_id] = {"ganadas": 0, "perdidas": 0, "total_apostado": 0}
    if gano:
        estadisticas[user_id]["ganadas"] += 1
    else:
        estadisticas[user_id]["perdidas"] += 1
    estadisticas[user_id]["total_apostado"] += monto

# ─────────────────────────────────────────
#  Modal: cerrar ticket con ganador y monto
# ─────────────────────────────────────────
class CerrarModal(discord.ui.Modal, title="🔒 Cerrar Ticket"):
    tipo = discord.ui.TextInput(
        label="Tipo de cierre",
        placeholder="Escribe: apuesta  |  sin-ganador  |  mm",
        required=True,
        max_length=20
    )
    ganador_id = discord.ui.TextInput(
        label="ID del ganador (solo si hubo apuesta)",
        placeholder="Ej: 123456789012345678",
        required=False,
        max_length=30
    )
    monto = discord.ui.TextInput(
        label="Monto apostado en USD (solo si hubo apuesta)",
        placeholder="Ej: 500",
        required=False,
        max_length=10
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        guild = interaction.guild
        canal = interaction.channel
        tipo = self.tipo.value.strip().lower()
        ganador_id = self.ganador_id.value.strip()
        monto_str = self.monto.value.strip()
        monto_int = int(monto_str) if monto_str.isdigit() else 0

        # ── Caso: solo middleman ──
        if tipo == "mm":
            embed_log = discord.Embed(
                title="🤝 Ticket MM Cerrado",
                description=(
                    f"📁 **Ticket:** {canal.name}\n"
                    f"✅ Servicio de MM completado sin apuesta\n"
                    f"🔒 Cerrado por {interaction.user.mention}"
                ),
                color=discord.Color.blue()
            )
            await enviar_log(guild, embed_log)
            embed_cierre = discord.Embed(
                title="🔒 Ticket Cerrado",
                description="✅ Servicio de middleman completado.\nEste canal se eliminará en 5 segundos.",
                color=discord.Color.blue()
            )
            await canal.send(embed=embed_cierre)
            await asyncio.sleep(5)
            await canal.delete()
            return

        # ── Caso: sin ganador ──
        if tipo == "sin-ganador":
            embed_log = discord.Embed(
                title="❌ Ticket Cerrado - Sin Ganador",
                description=(
                    f"📁 **Ticket:** {canal.name}\n"
                    f"💵 **Monto:** ${monto_int} USD\n"
                    f"❌ No hubo ganador\n"
                    f"🔒 Cerrado por {interaction.user.mention}"
                ),
                color=discord.Color.orange()
            )
            await enviar_log(guild, embed_log)
            embed_cierre = discord.Embed(
                title="🔒 Ticket Cerrado",
                description=f"❌ No hubo ganador.\n💵 Monto: ${monto_int} USD\nEste canal se eliminará en 5 segundos.",
                color=discord.Color.orange()
            )
            await canal.send(embed=embed_cierre)
            await asyncio.sleep(5)
            await canal.delete()
            return

        # ── Caso: apuesta con ganador ──
        if tipo == "apuesta":
            if not ganador_id:
                await interaction.followup.send("⚠️ Debes poner la ID del ganador para tipo 'apuesta'.", ephemeral=True)
                return
            try:
                ganador = guild.get_member(int(ganador_id))
                if not ganador:
                    ganador = await guild.fetch_member(int(ganador_id))
            except:
                await interaction.followup.send("⚠️ No se encontró al ganador con esa ID.", ephemeral=True)
                return

            perdedor = None
            async for msg in canal.history(limit=100):
                if msg.author != client.user and msg.author.id != ganador.id and not msg.author.bot:
                    perdedor = msg.author
                    break

            registrar_resultado(ganador.id, True, monto_int)
            if perdedor:
                registrar_resultado(perdedor.id, False, monto_int)

            nuevo_rol = await asignar_rol(guild, ganador, monto_int)

            embed_log = discord.Embed(
                title="📢 ¡Nuevo Ganador!",
                description=(
                    f"🏆 {ganador.mention} ganó la apuesta\n"
                    f"💵 **Monto:** ${monto_int} USD\n"
                    f"🎖️ **Rol asignado:** {nuevo_rol.mention if nuevo_rol else 'N/A'}\n"
                    f"📁 **Ticket:** {canal.name}\n"
                    f"🔒 Cerrado por {interaction.user.mention}"
                ),
                color=discord.Color.green()
            )
            await enviar_log(guild, embed_log)

            embed_cierre = discord.Embed(
                title="🔒 Ticket Cerrado",
                description=(
                    f"✅ Apuesta finalizada\n"
                    f"🏆 **Ganador:** {ganador.mention}\n"
                    f"💵 **Monto:** ${monto_int} USD\n\n"
                    f"Este canal se eliminará en 5 segundos."
                ),
                color=discord.Color.green()
            )
            await canal.send(embed=embed_cierre)
            await asyncio.sleep(5)
            await canal.delete()
            return

        # ── Tipo no reconocido ──
        await interaction.followup.send("⚠️ Tipo inválido. Escribe: `apuesta`, `sin-ganador` o `mm`.", ephemeral=True)


# ─────────────────────────────────────────
#  Botón cerrar ticket
# ─────────────────────────────────────────
class CerrarTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔒 Cerrar Ticket", style=discord.ButtonStyle.danger, custom_id="cerrar_ticket")
    async def cerrar_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("⚠️ Solo los administradores pueden cerrar tickets.", ephemeral=True)
            return
        await interaction.response.send_modal(CerrarModal())


# ─────────────────────────────────────────
#  Sistema de tickets
# ─────────────────────────────────────────
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

async def crear_ticket(interaction: discord.Interaction, monto: str):
    guild = interaction.guild
    usuario = interaction.user

    canal_existente = discord.utils.get(guild.channels, name=f"ticket-{usuario.name.lower()}")
    if canal_existente:
        await interaction.response.send_message(f"⚠️ Ya tienes un ticket abierto: {canal_existente.mention}", ephemeral=True)
        return

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        usuario: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
    }

    categoria = discord.utils.get(guild.categories, name="TICKETS")
    if not categoria:
        categoria = await guild.create_category("TICKETS")

    canal = await guild.create_text_channel(
        name=f"ticket-{usuario.name.lower()}",
        overwrites=overwrites,
        category=categoria
    )

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
    embed.set_footer(text="El admin cerrará el ticket al finalizar la apuesta.")
    await canal.send(embed=embed, view=CerrarTicketView())
    await interaction.response.send_message(f"✅ Tu ticket fue creado: {canal.mention}", ephemeral=True)


# ─────────────────────────────────────────
#  Evento: bot listo
# ─────────────────────────────────────────
@client.event
async def on_ready():
    client.add_view(TicketMontoView())
    client.add_view(CerrarTicketView())
    print(f"✅ Bot conectado como {client.user}")

# ─────────────────────────────────────────
#  Comando viejo: -jugar
# ─────────────────────────────────────────
@client.event
async def on_message(message):
    if message.author == client.user:
        return
    if message.content.strip().lower() == "-jugar":
        resultado = random.choice(["🪙 **¡CARA!**", "🔵 **¡SELLO!**"])
        await message.channel.send(f"🎲 {message.author.mention} lanzó la moneda...\n➡️ {resultado}")

# ─────────────────────────────────────────
#  Comando: /moneda
# ─────────────────────────────────────────
@client.tree.command(name="moneda", description="Lanza una moneda: cara o sello")
async def moneda(interaction: discord.Interaction):
    resultado = random.choice(["🪙 **¡CARA!**", "🔵 **¡SELLO!**"])
    await interaction.response.send_message(f"🎲 {interaction.user.mention} lanzó la moneda...\n➡️ {resultado}")

# ─────────────────────────────────────────
#  Comando: /dados
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
#  Comando: /estadisticas
# ─────────────────────────────────────────
@client.tree.command(name="estadisticas", description="Ver tus estadísticas de juego")
async def estadisticas_cmd(interaction: discord.Interaction):
    user_id = interaction.user.id
    if user_id not in estadisticas or estadisticas[user_id]["ganadas"] + estadisticas[user_id]["perdidas"] == 0:
        await interaction.response.send_message("📊 Aún no tienes estadísticas. ¡Juega primero!", ephemeral=True)
        return
    stats = estadisticas[user_id]
    total = stats["ganadas"] + stats["perdidas"]
    winrate = round((stats["ganadas"] / total) * 100, 1)
    embed = discord.Embed(title=f"📊 Estadísticas de {interaction.user.display_name}", color=discord.Color.gold())
    embed.add_field(name="✅ Ganadas", value=stats["ganadas"], inline=True)
    embed.add_field(name="❌ Perdidas", value=stats["perdidas"], inline=True)
    embed.add_field(name="🎯 Winrate", value=f"{winrate}%", inline=True)
    embed.add_field(name="💵 Total apostado", value=f"${stats['total_apostado']} USD", inline=False)
    await interaction.response.send_message(embed=embed)

# ─────────────────────────────────────────
#  Comando: /ranking
# ─────────────────────────────────────────
@client.tree.command(name="ranking", description="Ver el ranking de los mejores jugadores")
async def ranking(interaction: discord.Interaction):
    if not estadisticas:
        await interaction.response.send_message("🏆 Aún no hay jugadores en el ranking.", ephemeral=True)
        return
    ordenado = sorted(estadisticas.items(), key=lambda x: x[1]["ganadas"], reverse=True)[:10]
    embed = discord.Embed(title="🏆 Ranking de Ganadores", color=discord.Color.gold())
    medallas = ["🥇", "🥈", "🥉"]
    for i, (user_id, stats) in enumerate(ordenado):
        try:
            usuario = await client.fetch_user(user_id)
            nombre = usuario.display_name
        except:
            nombre = f"Usuario {user_id}"
        medalla = medallas[i] if i < 3 else f"#{i+1}"
        total = stats["ganadas"] + stats["perdidas"]
        winrate = round((stats["ganadas"] / total) * 100, 1) if total > 0 else 0
        embed.add_field(
            name=f"{medalla} {nombre}",
            value=f"✅ {stats['ganadas']} ganadas | 💵 ${stats['total_apostado']} USD | 🎯 {winrate}%",
            inline=False
        )
    await interaction.response.send_message(embed=embed)

# ─────────────────────────────────────────
#  Comando: /agregar
# ─────────────────────────────────────────
@client.tree.command(name="agregar", description="Agrega a una persona al ticket por su ID de Discord")
async def agregar(interaction: discord.Interaction, userid: str):
    if not interaction.channel.name.startswith("ticket-"):
        await interaction.response.send_message("⚠️ Este comando solo se puede usar dentro de un ticket.", ephemeral=True)
        return
    try:
        usuario = await client.fetch_user(int(userid))
        miembro = interaction.guild.get_member(usuario.id)
        if not miembro:
            await interaction.response.send_message(f"⚠️ No se encontró al usuario con ID `{userid}` en este servidor.", ephemeral=True)
            return
        await interaction.channel.set_permissions(miembro, read_messages=True, send_messages=True)
        await interaction.response.send_message(f"✅ {miembro.mention} ha sido agregado al ticket por {interaction.user.mention}.")
    except ValueError:
        await interaction.response.send_message("⚠️ ID inválida. Asegúrate de poner solo números.", ephemeral=True)
    except discord.NotFound:
        await interaction.response.send_message(f"⚠️ No se encontró ningún usuario con la ID `{userid}`.", ephemeral=True)

# ─────────────────────────────────────────
#  Comando: /paneltickets
# ─────────────────────────────────────────
@client.tree.command(name="paneltickets", description="Envía el panel de tickets al canal actual")
@app_commands.checks.has_permissions(administrator=True)
async def panel_tickets(interaction: discord.Interaction):
    await interaction.response.defer()
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
    await interaction.followup.send(embed=embed, view=TicketMontoView())

# ─────────────────────────────────────────
#  Iniciar el bot
# ─────────────────────────────────────────
client.run(TOKEN)

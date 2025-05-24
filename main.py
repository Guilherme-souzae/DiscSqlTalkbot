import discord
from discord.ext import commands
import sqlite3
import random
from datetime import datetime

from exceptions import AlreadyRegisteredClientError, InvalidFlagError, NotRegisteredClientError, NotRegisteredQuotesError, FlagLimitError

# bot initialization and global stuff
with open('token.txt', 'r') as file:
    TOKEN = file.read().strip()

PREFIX = 'ps!'

VALID_FLAGS = ["greeting", "default"]

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)

# bot functions

#bot help
@bot.command()
async def help(ctx):
    embed = discord.Embed(
        title="📜 PetSpeak Bot Help",
        description="Lista de comandos disponíveis:",
        color=discord.Color.green()
    )

    embed.add_field(
        name=f"{PREFIX}register <nome> <url_da_imagem>",
        value="Cria um novo pet com o nome e imagem fornecidos.",
        inline=False
    )
    embed.add_field(
        name=f"{PREFIX}teachquote <flag> <frase>",
        value=f"Ensina uma frase ao seu pet para uma flag específica. Flags válidas: {', '.join(f'`{flag}`' for flag in VALID_FLAGS)}.",
        inline=False
    )
    embed.add_field(
        name=f"{PREFIX}yap <flag>",
        value="Faz o pet falar uma frase registrada da flag fornecida.",
        inline=False
    )
    embed.add_field(
        name=f"{PREFIX}help",
        value="Mostra os atributos do pet.",
        inline=False
    )
    embed.add_field(
        name=f"{PREFIX}togglesleep",
        value="Alterna o pet entre dormindo e acordado.",
        inline=False
    )
    embed.add_field(
        name=f"{PREFIX}help",
        value="Mostra esta mensagem de ajuda.",
        inline=False
    )

    await ctx.send(embed=embed)

# bot register new pet
@bot.command()
async def register(ctx, name: str, imgUrl: str):
    userId = ctx.author.id

    try:
        checkIfUserIsEmpty(userId)

        with sqlite3.connect('database.db') as db:
            cursor = db.cursor()
            cursor.execute("INSERT INTO Pet (idDiscord, name, imgUrl, energy, isSleeping, lastTime) VALUES (?, ?, ?, ?, ?, ?)", (userId, name, imgUrl, 100, 0, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            db.commit()

        await ctx.send(f"{name} is alive!")
    except AlreadyRegisteredClientError as e:
        await ctx.send(f"Error: {e}")

# bot teach new quote
@bot.command()
async def teachquote(ctx, flag: str, *, quote: str):
    userId = ctx.author.id

    try:
        checkIfUserIsRegistered(userId)
        checkValidFlag(flag)
        checkFlagLimit(userId, flag)

        with sqlite3.connect('database.db') as db:
            cursor = db.cursor()
            cursor.execute("INSERT INTO Quotes (flag, quote, Pet_idDiscord) VALUES (?, ?, ?)", (flag, quote, userId))
            db.commit()
            await ctx.send("Quote learned!")

    except NotRegisteredClientError as e:
        await ctx.send(f"Error: {e}")
    except InvalidFlagError as e:
        await ctx.send(f"Error: {e}")
    except FlagLimitError as e:
        await ctx.send(f"Error: {e}")

# bot say a quote
@bot.command()
async def yap(ctx, flag: str = 'default'):
    userId = ctx.author.id

    try:
        checkIfUserIsRegistered(userId)
        checkValidFlag(flag)

        with sqlite3.connect('database.db') as db:
            cursor = db.cursor()

            # Pega as quotes do usuário
            cursor.execute("SELECT quote FROM Quotes WHERE Pet_idDiscord = ? AND flag = ?", (userId, flag))
            quotes = cursor.fetchall()
            checkExistingQuote(quotes)

            # Pega os dados do pet
            cursor.execute("SELECT name, imgUrl FROM Pet WHERE idDiscord = ?", (userId,))
            row = cursor.fetchone()
            name, imgUrl = row[0], row[1]

        quote = random.choice(quotes)[0]

        embed = discord.Embed(
            title=name,
            description=quote,
            color=discord.Color.blue()
        )
        embed.set_image(url=imgUrl)
        await ctx.send(embed=embed)

    except NotRegisteredClientError as e:
        await ctx.send(f"Error: {e}")
    except InvalidFlagError as e:
        await ctx.send(f"Error: {e}")
    except NotRegisteredQuotesError as e:
        await ctx.send(f"Error: {e}")

# check bot atributes
@bot.command()
async def status(ctx):
    userId = ctx.author.id

    try:
        checkIfUserIsRegistered(userId)

        with sqlite3.connect('database.db') as db:
            cursor = db.cursor()

            cursor.execute("SELECT name, imgUrl, energy, lastTime, isSleeping FROM Pet WHERE idDiscord = ?", (userId,))
            row = cursor.fetchone()

            name, imgUrl, energy, lastTimeStr, isSleeping = row

            lastTime = datetime.strptime(lastTimeStr, "%Y-%m-%d %H:%M:%S")
            now = datetime.now()

            diff_minutes = (now - lastTime).total_seconds() / 60

            energy_loss_per_minute = 0.2
            energy_gain_per_minute = 0.3

            if isSleeping == 1:
                energy_change = diff_minutes * energy_gain_per_minute
            else:
                energy_change = -diff_minutes * energy_loss_per_minute

            new_energy = max(0, min(energy + energy_change, 100))

            cursor.execute("UPDATE Pet SET energy = ?, lastTime = ? WHERE idDiscord = ?", (new_energy, now.strftime("%Y-%m-%d %H:%M:%S"), userId))
            db.commit()

            cursor.execute("SELECT quote FROM Quotes WHERE Pet_idDiscord = ? AND flag = ?", (userId, VALID_FLAGS[0]))
            quotes = cursor.fetchall()
            checkExistingQuote(quotes)

            quote = random.choice(quotes)[0]

        if energy_change >= 0:
            energy_msg = f"🔋 Energia ganha desde a última vez: {energy_change:.1f}"
        else:
            energy_msg = f"🔋 Energia perdida desde a última vez: {abs(energy_change):.1f}"

        embed = discord.Embed(
            title=f"{name} - Status",
            description=f"{quote}\n\nEnergia atual: {new_energy:.1f} / 100\n{energy_msg}",
            color=discord.Color.blue()
        )
        embed.set_image(url=imgUrl)
        await ctx.send(embed=embed)

    except NotRegisteredClientError as e:
        await ctx.send(f"Error: {e}")
    except NotRegisteredQuotesError as e:
        await ctx.send(f"Error: {e}")

# toggle bot sleep state
@bot.command()
async def togglesleep(ctx):
    userId = ctx.author.id

    try:
        checkIfUserIsRegistered(userId)

        with sqlite3.connect('database.db') as db:
            cursor = db.cursor()

            cursor.execute("SELECT isSleeping FROM Pet WHERE idDiscord = ?", (userId,))
            result = cursor.fetchone()

            isSleeping = result[0]

            if isSleeping == 0:
                cursor.execute("UPDATE Pet SET isSleeping = ? WHERE idDiscord = ?", (1, userId))
                db.commit()
                await ctx.send("O pet está dormindo")
            elif isSleeping == 1:
                cursor.execute("UPDATE Pet SET isSleeping = ? WHERE idDiscord = ?", (0, userId))
                db.commit()
                await ctx.send("O pet acordou")

    except NotRegisteredClientError as e:
        await ctx.send(f"Error: {e}")


# exceptions checking
def checkIfUserIsRegistered(userId):
    with sqlite3.connect('database.db') as db:
        cursor = db.cursor()
        cursor.execute("SELECT 1 FROM Pet WHERE idDiscord = ?", (userId,))
        if cursor.fetchone() is None:
            raise NotRegisteredClientError("This user is not registered.")

def checkIfUserIsEmpty(userId):
    with sqlite3.connect('database.db') as db:
        cursor = db.cursor()
        cursor.execute("SELECT 1 FROM Pet WHERE idDiscord = ?", (userId,))
        if cursor.fetchone() is not None:
            raise AlreadyRegisteredClientError("This user is already registered.")

def checkValidFlag(flag):
    if flag not in VALID_FLAGS:
        raise InvalidFlagError("This quote type is invalid.")

def checkExistingQuote(quotes):
    if not quotes:
        raise NotRegisteredQuotesError("No quotes registered for this type.")

def checkFlagLimit(userId, flag):
    LIMIT = 3

    with sqlite3.connect('database.db') as db:
        cursor = db.cursor()
        cursor.execute("SELECT COUNT(*) FROM Quotes WHERE Pet_idDiscord = ? AND flag = ?", (userId, flag))
        count = cursor.fetchone()[0]
    
    if count >= LIMIT:
        raise FlagLimitError("You can't learn more quotes from this type.")

# main functions
if __name__ == "__main__":

    # database initialization
    with sqlite3.connect('database.db') as db:
        cursor = db.cursor()
        with open('creation.sql', 'r', encoding='utf-8') as file:
            sql_script = file.read()
            cursor.executescript(sql_script)
        db.commit()

    # Run the bot
    bot.run(TOKEN)
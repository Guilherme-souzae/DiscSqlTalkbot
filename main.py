import discord
from discord.ext import commands
import sqlite3
import random

from exceptions import AlreadyRegisteredClientError, InvalidFlagError, NotRegisteredClientError, NotRegisteredQuotesError, FlagLimitError

# bot initialization
with open('token.txt', 'r') as file:
    TOKEN = file.read().strip()

PREFIX = 'ps!'

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)

# bot functions
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
        value="Ensina uma frase ao seu pet para uma flag específica. Flags válidas: `greeting`, `default`.",
        inline=False
    )
    embed.add_field(
        name=f"{PREFIX}yap <flag>",
        value="Faz o pet falar uma frase registrada da flag fornecida.",
        inline=False
    )
    embed.add_field(
        name=f"{PREFIX}help",
        value="Mostra esta mensagem de ajuda.",
        inline=False
    )

    await ctx.send(embed=embed)

@bot.command()
async def register(ctx, name: str, imgUrl: str):
    userId = ctx.author.id

    try:
        checkIfUserIsEmpty(userId)

        with sqlite3.connect('database.db') as db:
            cursor = db.cursor()
            cursor.execute("INSERT INTO Pet (idDiscord, name, imgUrl) VALUES (?, ?, ?)", (userId, name, imgUrl))
            db.commit()

        await ctx.send(f"{name} is alive!")
    except AlreadyRegisteredClientError as e:
        await ctx.send(f"Error: {e}")

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

@bot.command()
async def yap(ctx, flag: str = 'default'):
    userId = ctx.author.id

    try:
        checkIfUserIsRegistered(userId)
        checkValidFlag(flag)

        with sqlite3.connect('database.db') as db:
            cursor = db.cursor()

            cursor.execute("SELECT quote FROM Quotes WHERE Pet_idDiscord = ? AND flag = ?", (userId, flag))
            quotes = cursor.fetchall()

            checkExistingQuote(quotes)

            cursor.execute("SELECT name FROM Pet WHERE idDiscord = ?", (userId,))
            name = cursor.fetchone()[0]

            cursor.execute("SELECT imgUrl FROM Pet WHERE idDiscord = ?", (userId,))
            imgUrl = cursor.fetchone()[0]

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

# utility functions
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
    VALID_FLAGS = ["greeting", "default"]
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
import os 
import discord
from discord.ext import commands
from dotenv import load_dotenv
import certifi

# ensure Python uses certifi's CA bundle for SSL
os.environ.setdefault("SSL_CERT_FILE", certifi.where())

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.message_content = True  # Enable the message content intent

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.command()
async def ping(ctx):
    await ctx.send('Pong!')

@bot.event
async def on_ready():
    await bot.tree.sync()  # Sync commands with Discord
    print(f'{bot.user} is online!')


bot.run(TOKEN)
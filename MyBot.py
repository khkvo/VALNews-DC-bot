import os 
import certifi
os.environ.setdefault("SSL_CERT_FILE", certifi.where())
import discord
from discord.ext import commands
from dotenv import load_dotenv
from services.vlr_client import VLRClient
vlr = VLRClient()  # defaults to https://vlrggapi.vercel.app
import json 
import io

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.message_content = True  # Enable the message content intent

bot = commands.Bot(command_prefix='!', intents=intents)

# Test Command
@bot.command()
async def ping(ctx):
    await ctx.send(f"Pong! {ctx.author.mention}")

async def _send_json(ctx, data, filename): #temporary function to send JSON data
    payload = json.dumps(data, indent=2, ensure_ascii=False)
    if len(payload) > 2000:
        bio = io.BytesIO(payload.encode('utf-8'))
        bio.seek(0)
        await ctx.send(file=discord.File(bio, filename=filename))
    else:
        await ctx.send(f"```json\n{payload}\n```")


@bot.command()
@commands.is_owner()
async def shutdown(ctx):
    await ctx.send("Shutting down...")
    try:
        await vlr.close()
    except Exception:
        pass
    await bot.close()

@bot.command() 
async def vlr_news(ctx): #command for news, fetches from VLR API and sends latest article URL in Discord chat.
    await ctx.send("Fetching latest VLR news article...")
    await ctx.typing()
    try:
        data = await vlr.get("news") # fetch news from VLR API
    except Exception as e:
        await ctx.send(f"Error fetching news: {e}")
        return

    segments = (data or {}).get("data", {}).get("segments", {})
    if not segments:
        await ctx.send("No news found.")
        return
    latest = segments[0]
    url = latest.get("url_path", "")
     
    if url:
        await ctx.send(url)
    else:
        await ctx.send("Could not find a URL for the latest news article.")


@bot.event
async def on_ready():
    await bot.tree.sync()  # Sync commands with Discord
    print(f'{bot.user} is online!')


bot.run(TOKEN)
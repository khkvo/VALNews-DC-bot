import os 
import certifi
os.environ.setdefault("SSL_CERT_FILE", certifi.where())
from dotenv import load_dotenv
import discord
from discord.ext import commands
from discord.ext import tasks
from services.vlr_client import VLRClient
vlr = VLRClient()  # defaults to https://vlrggapi.vercel.app
import json 
import io

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
CONFIG_FILE = "config.json"

news_channels_config = {}
last_known_article_url = None

def load_config():
    global news_channels_config
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            news_channels_config = json.load(f)

intents = discord.Intents.default()
intents.message_content = True  # Enable the message content intent

bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

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
@commands.has_permissions(manage_channels=True)
@commands.guild_only()
async def set_news_channel(ctx, channel: discord.TextChannel = None):
    """Sets the channel for VLR news updates. Defaults to the current channel."""
    if channel is None:
        channel = ctx.channel
    
    news_channels_config[str(ctx.guild.id)] = channel.id
    with open(CONFIG_FILE, 'w') as f:
        json.dump(news_channels_config, f, indent=4)
    
    await ctx.send(f"✅ VLR.gg news will now be posted in {channel.mention}.")

@bot.command()
@commands.has_permissions(manage_channels=True)
@commands.guild_only()
async def remove_news_channel(ctx):
    """Stops posting VLR news updates in this server."""
    guild_id = str(ctx.guild.id)
    if guild_id in news_channels_config:
        del news_channels_config[guild_id]
        with open(CONFIG_FILE, 'w') as f:
            json.dump(news_channels_config, f, indent=4)
        await ctx.send("✅ VLR.gg news updates have been disabled for this server.")
    else:
        await ctx.send("⚠️ VLR.gg news updates are not configured for this server.")

@bot.command()
async def help(ctx):
    help_text = """
**Available Commands:**
`!ping` - Test command to check if the bot is responsive.
`!vlr_news` - Fetches and displays the latest VLR.gg news article.
`!set_news_channel [#channel]` - Sets the specified channel (or current channel
    for VLR news updates. Requires Manage Channels permission.
`!remove_news_channel` - Disables VLR news updates for this server. Requires Manage Channels permission.
`!shutdown` - Shuts down the bot (Owner only).
"""
    await ctx.send(help_text)

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


@tasks.loop(minutes=10) #task to check for new articles every 10 minutes
async def check_for_new_articles():
    global last_known_article_url
    try:
        data = await vlr.get("news")
        segments = (data or {}).get("data", {}).get("segments", [])
        if not segments:
            print("Article check: No news segments found.")
            return

        latest_article = segments[0]
        new_url = latest_article.get("url_path", "")

        # On the first run, just set the initial URL without sending a message
        if last_known_article_url is None:
            last_known_article_url = new_url
            print(f"Initial article set to: {new_url}")
            return

        if new_url and new_url != last_known_article_url:
            print(f"New article found: {new_url}")
            last_known_article_url = new_url # Update last known URL immediately
            
            # Iterate over a copy of the values in case the config changes during iteration
            for channel_id in list(news_channels_config.values()):
                channel = bot.get_channel(channel_id)
                if channel:
                    await channel.send(f"**New VLR.gg Article Posted!**\n{new_url}")

    except Exception as e:
        print(f"Error during scheduled article check: {e}")


@bot.event
async def on_ready():
    load_config()
    check_for_new_articles.start()
    print(f'{bot.user} is online!')


bot.run(TOKEN)
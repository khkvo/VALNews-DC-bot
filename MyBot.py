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
import sys
import asyncio

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
CONFIG_FILE = "config.json"

news_channels_config = {}
last_known_article_url = None
config_lock = asyncio.Lock()

def load_config():
    global news_channels_config
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            news_channels_config = json.load(f)

def _save_config():
    """Saves the current configuration to the JSON file."""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(news_channels_config, f, indent=4)

intents = discord.Intents.default()
intents.message_content = True  # Enable the message content intent

bot = commands.Bot(command_prefix='!vlrnews ', intents=intents, help_command=None)

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
async def help(ctx):
    embed = discord.Embed(
        title="Bot Commands",
        description="Here are the available commands:",
        color=discord.Color.blue()
    )
    embed.add_field(name="`!vlrnews ping`", value="Test command to check if the bot is responsive.", inline=False)
    embed.add_field(name="`!vlrnews vlr_news`", value="Fetches and displays the latest VLR.gg news article.", inline=False)
    embed.add_field(name="`!vlrnews set_news_channel [#channel]`", value="Sets the channel for VLR news updates. Defaults to the current channel. (Requires *Manage Channels* permission).", inline=False)
    embed.add_field(name="`!vlrnews setup_reactions <@role> [#channel]`", value="Creates a message for users to react to for news pings. (Requires *Manage Roles* & *Manage Channels* permissions).", inline=False)
    embed.add_field(name="`!vlrnews remove_news_channel`", value="Disables VLR news updates for this server. (Requires *Manage Channels* permission).", inline=False)
    
    if await bot.is_owner(ctx.author):
        embed.add_field(name="Owner Commands", value="`!vlrnews shutdown`, `!vlrnews restart`", inline=False)

    await ctx.send(embed=embed)

@bot.command()
@commands.is_owner()
async def shutdown(ctx):
    await ctx.send("Shutting down...")
    try:
        await vlr.close()
    except Exception:
        pass
    sys.exit()

@bot.command()
@commands.is_owner()
async def restart(ctx):
    await ctx.send("Restarting bot...")
    try:
        await vlr.close()
    except Exception:
        pass
    await bot.close()
    os.execv(sys.executable, ['python'] + sys.argv)

@bot.command()
@commands.has_permissions(manage_channels=True)
@commands.guild_only()
async def set_news_channel(ctx, channel: discord.TextChannel = None):
    """Sets the channel for VLR news updates. Defaults to the current channel."""
    if channel is None:
        channel = ctx.channel

    async with config_lock:
        guild_id = str(ctx.guild.id)
        
        # Data migration: Check for old config format (int) and upgrade to new format (dict)
        if guild_id in news_channels_config and isinstance(news_channels_config[guild_id], int):
            print(f"Migrating old config for guild {guild_id}")
            old_channel_id = news_channels_config[guild_id]
            news_channels_config[guild_id] = {"channel_id": old_channel_id}
        elif guild_id not in news_channels_config:
            news_channels_config[guild_id] = {}

        if news_channels_config.get(guild_id, {}).get("channel_id") == channel.id:
            await ctx.send(f"⚠️ VLR.gg news is already being posted in {channel.mention}.")
            return

        # Test if we can send a message to the target channel
        try:
            await channel.send("✅ This channel has been configured for VLR.gg news updates.", delete_after=10)
        except discord.Forbidden:
            await ctx.send(f"❌ I don't have permission to send messages in {channel.mention}. Please check my permissions.")
            return

        news_channels_config[guild_id]["channel_id"] = channel.id
        _save_config()
        await ctx.send(f"✅ VLR.gg news will now be posted in {channel.mention}.")

@bot.command()
@commands.has_permissions(manage_roles=True, manage_channels=True)
@commands.guild_only()
async def setup_reactions(ctx, role: discord.Role, channel: discord.TextChannel = None):
    """Sets up a reaction message to opt-in for news pings."""
    if channel is None:
        channel = ctx.channel

    # Check if bot can manage roles and send messages
    if not ctx.guild.me.guild_permissions.manage_roles:
        await ctx.send("❌ I need the `Manage Roles` permission to assign roles.")
        return
    if not channel.permissions_for(ctx.guild.me).send_messages:
        await ctx.send(f"❌ I don't have permission to send messages in {channel.mention}.")
        return

    embed = discord.Embed(
        title="VLR.gg News Notifications",
        description=f"React with ✅ to get the {role.mention} role and be notified of new articles.",
        color=discord.Color.blurple()
    )
    reaction_message = await channel.send(embed=embed)
    await reaction_message.add_reaction("✅")

    async with config_lock:
        guild_id = str(ctx.guild.id)
        if guild_id not in news_channels_config:
            news_channels_config[guild_id] = {}
        news_channels_config[guild_id]["reaction_role"] = {
            "message_id": reaction_message.id,
            "role_id": role.id
        }
        _save_config()
    
    await ctx.send(f"✅ Reaction role setup complete in {channel.mention}.", delete_after=10)

@bot.command()
@commands.has_permissions(manage_channels=True)
@commands.guild_only()
async def remove_news_channel(ctx):
    """Stops posting VLR news updates in this server."""
    async with config_lock:
        guild_id = str(ctx.guild.id)

        # Data migration: Check for old config format (int) and upgrade to new format (dict)
        if guild_id in news_channels_config and isinstance(news_channels_config[guild_id], int):
            print(f"Migrating old config for guild {guild_id}")
            old_channel_id = news_channels_config[guild_id]
            news_channels_config[guild_id] = {"channel_id": old_channel_id}

        guild_config = news_channels_config.get(guild_id, {})
        if "channel_id" in guild_config:
            # We only remove the channel, not the reaction role setup
            del guild_config["channel_id"]
            _save_config()
            await ctx.send("✅ VLR.gg news updates have been disabled for this server.")
        else:
            await ctx.send("⚠️ A news channel is not configured for this server.")


@bot.command() 
async def vlr_news(ctx): #command for news, fetches from VLR API and sends latest article URL in Discord chat.
    msg = await ctx.send(f"Fetching the latest VLR news article for {ctx.author.mention}...")
    await ctx.typing()
    try:
        data = await vlr.get("news") # fetch news from VLR API
    except Exception as e:
        await msg.edit(content=f"Sorry {ctx.author.mention}, I ran into an error: {e}")
        return

    segments = (data or {}).get("data", {}).get("segments", [])
    if not segments:
        await msg.edit(content=f"Sorry {ctx.author.mention}, I couldn't find any news articles.")
        return
    latest_article = segments[0]
    url = latest_article.get("url_path", "")
     
    if url:
        embed = discord.Embed(
            title=latest_article.get("title", "Latest VLR.gg Article"),
            url=url,
            description=latest_article.get("description", "The latest article from VLR.gg."),
            color=discord.Color.red()
        )
        embed.set_footer(text=f"Author: {latest_article.get('author', 'N/A')} • {latest_article.get('date', '')}")
        
        # Edit the original message to include the embed
        await msg.edit(content=f"Here is the latest article, {ctx.author.mention}:", embed=embed)
    else:
        await msg.edit(content=f"Sorry {ctx.author.mention}, I found an article but couldn't get its URL.", embed=None)


@tasks.loop(minutes=60) #task to check for new articles every hour
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
            
            async with config_lock:
                for guild_id, config in news_channels_config.items():
                    channel_id = config.get("channel_id")
                    if not channel_id:
                        continue

                    channel = bot.get_channel(channel_id)
                    if channel:
                        # Default to the role_id from the old system for backward compatibility
                        role_id = config.get("role_id") 
                        # New system check
                        if "reaction_role" in config:
                            role_id = config["reaction_role"].get("role_id")

                        role_mention = ""
                        if role_id:
                            # In case the role was deleted, we fetch it safely
                            role = channel.guild.get_role(role_id)
                            if role:
                                role_mention = f"{role.mention}"

                        # Create a nice embed for the announcement
                        embed = discord.Embed(
                            title=latest_article.get("title", "New VLR.gg Article"),
                            url=new_url,
                            description=latest_article.get("description", "A new article has been posted on VLR.gg."),
                            color=discord.Color.red() # A color that fits the Valorant theme
                        )
                        embed.set_footer(text=f"Author: {latest_article.get('author', 'N/A')} • {latest_article.get('date', '')}")

                        # Send the role mention outside the embed for a clean ping
                        await channel.send(content=role_mention, embed=embed)

    except Exception as e:
        print(f"Error during scheduled article check: {e}")

@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    # Ignore reactions from the bot itself
    if payload.user_id == bot.user.id:
        return

    # Check if the reaction is on a configured message
    guild_id = str(payload.guild_id)
    config = news_channels_config.get(guild_id, {}).get("reaction_role")
    if not config or payload.message_id != config.get("message_id"):
        return

    # Check if the emoji is correct
    if str(payload.emoji) == "✅":
        guild = bot.get_guild(payload.guild_id)
        role = guild.get_role(config.get("role_id"))
        if role and payload.member:
            await payload.member.add_roles(role, reason="Opted in for VLR news")

@bot.event
async def on_raw_reaction_remove(payload: discord.RawReactionActionEvent):
    guild_id = str(payload.guild_id)
    config = news_channels_config.get(guild_id, {}).get("reaction_role")
    if not config or payload.message_id != config.get("message_id"):
        return

    if str(payload.emoji) == "✅":
        guild = bot.get_guild(payload.guild_id)
        member = guild.get_member(payload.user_id)
        role = guild.get_role(config.get("role_id"))
        if role and member:
            await member.remove_roles(role, reason="Opted out of VLR news")

@bot.event
async def on_ready():
    load_config()
    check_for_new_articles.start()
    print(f'{bot.user} is online!')


bot.run(TOKEN)
import discord
from discord.ext import commands
from collector_cog import Collector

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} ({bot.user.id})")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands.")
    except Exception as e:
        print("Command sync error:", e)


@bot.event
async def setup_hook():
    await bot.add_cog(Collector(bot))



bot.run("DISCORD_TOKEN")

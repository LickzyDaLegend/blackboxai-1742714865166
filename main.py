import discord
from discord.ext import commands, tasks
import json
import os
import logging
from datetime import datetime
import asyncio
import motor.motor_asyncio
from typing import Optional, Dict, List

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('discord_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('discord_bot')

# Load configuration
try:
    with open('config.json', 'r') as config_file:
        config = json.load(config_file)
except FileNotFoundError:
    logger.error("config.json not found!")
    exit(1)
except json.JSONDecodeError:
    logger.error("config.json is invalid!")
    exit(1)

# Initialize status index
status_index = 0

class CustomBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mongo = None
        self.config = config
        self.premium_users = set()
        self.badge_cache = {}
        self.uptime = None

    async def setup_hook(self):
        """Setup additional features when the bot starts"""
        self.uptime = datetime.utcnow()
        
        # Connect to MongoDB
        try:
            # Skip MongoDB connection for now since it's not critical for core functionality
            logger.warning("Skipping MongoDB connection - will run with reduced functionality")
            
            # Load all cogs
            await self.load_extensions()
            
        except Exception as e:
            logger.error(f"Error in setup: {e}")

    async def on_ready(self):
        """Called when the bot is ready"""
        logger.info(f'Logged in as {self.user.name}')
        # Start status rotation after bot is ready
        self.rotate_status.start()

    @tasks.loop(minutes=5)
    async def rotate_status(self):
        """Rotate the bot's status every 5 minutes"""
        global status_index
        if not config['rotating_status']:
            return
        
        status = config['rotating_status'][status_index]
        try:
            await self.change_presence(
                activity=discord.Game(name=status),
                status=discord.Status.online
            )
            status_index = (status_index + 1) % len(config['rotating_status'])
        except Exception as e:
            logger.error(f"Failed to update status: {e}")

    async def load_extensions(self):
        """Load all cogs from the cogs directory"""
        cogs_dir = 'cogs'
        
        if not os.path.exists(cogs_dir):
            os.makedirs(cogs_dir)
            logger.info(f"Created {cogs_dir} directory")
        
        for filename in os.listdir(cogs_dir):
            if filename.endswith('.py'):
                cog_name = f'cogs.{filename[:-3]}'
                try:
                    await self.load_extension(cog_name)
                    logger.info(f'Loaded extension {cog_name}')
                except Exception as e:
                    logger.error(f'Failed to load extension {cog_name}: {e}')

    async def on_command_error(self, ctx, error):
        """Global error handler for command errors"""
        if isinstance(error, commands.CommandNotFound):
            return
        
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("You don't have permission to use this command!")
            return
        
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"Missing required argument: {error.param.name}")
            return
        
        if isinstance(error, commands.BadArgument):
            await ctx.send("Invalid argument provided!")
            return
        
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"This command is on cooldown. Try again in {error.retry_after:.2f}s")
            return
        
        if isinstance(error, commands.NoPrivateMessage):
            await ctx.send("This command cannot be used in private messages!")
            return
        
        # Log unexpected errors
        logger.error(f'Command error in {ctx.command}: {error}')
        await ctx.send("An unexpected error occurred! The error has been logged.")

    def run(self):
        """Run the bot with the token from config"""
        try:
            super().run(config['token'], reconnect=True)
        except discord.LoginFailure:
            logger.error("Failed to login. Check your token in config.json")
        except Exception as e:
            logger.error(f"Failed to run bot: {e}")

# Set up intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True
intents.guilds = True
intents.messages = True

# Create bot instance
bot = CustomBot(
    command_prefix=commands.when_mentioned_or(config['prefix']),
    intents=intents,
    case_insensitive=True,
    strip_after_prefix=True
)

if __name__ == "__main__":
    bot.run()

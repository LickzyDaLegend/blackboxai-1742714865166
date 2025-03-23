import discord
from discord.ext import commands
import platform
import psutil
import time
from datetime import datetime
from typing import Optional

from utils.logger import Logger

logger = Logger.get_logger()

class Utility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.start_time = datetime.utcnow()

    @commands.command()
    async def ping(self, ctx):
        """Get the bot's latency"""
        start_time = time.perf_counter()
        message = await ctx.send("Pinging...")
        end_time = time.perf_counter()
        
        duration = (end_time - start_time) * 1000
        websocket_latency = round(self.bot.latency * 1000)
        
        embed = discord.Embed(title="🏓 Pong!", color=discord.Color.green())
        embed.add_field(name="Bot Latency", value=f"{duration:.2f}ms")
        embed.add_field(name="WebSocket Latency", value=f"{websocket_latency}ms")
        embed.set_footer(text="Developed By Lickzy")
        
        await message.edit(content=None, embed=embed)

    @commands.command()
    async def uptime(self, ctx):
        """Get the bot's uptime"""
        current_time = datetime.utcnow()
        uptime = current_time - self.start_time
        
        days = uptime.days
        hours, remainder = divmod(uptime.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        embed = discord.Embed(
            title="⏱️ Bot Uptime",
            description=f"{days}d {hours}h {minutes}m {seconds}s",
            color=discord.Color.blue()
        )
        embed.set_footer(text="Developed By Lickzy")
        await ctx.send(embed=embed)

    @commands.command(name="botinfo")
    async def botinfo(self, ctx):
        """Get detailed information about the bot"""
        embed = discord.Embed(
            title="🤖 Bot Information",
            description="Made for Mystic Falls",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )

        # Developer info
        embed.add_field(
            name="👨‍💻 Developer",
            value="Lickzy",
            inline=True
        )

        # Bot latency
        embed.add_field(
            name="📡 Latency",
            value=f"{round(self.bot.latency * 1000)}ms",
            inline=True
        )

        # Uptime
        current_time = datetime.utcnow()
        uptime = current_time - self.start_time
        days = uptime.days
        hours, remainder = divmod(uptime.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        embed.add_field(
            name="⏱️ Uptime",
            value=f"{days}d {hours}h {minutes}m {seconds}s",
            inline=True
        )

        # System info
        embed.add_field(
            name="📊 System",
            value=f"Python: {platform.python_version()}\n"
                  f"Discord.py: {discord.__version__}",
            inline=False
        )
        
        # Bot stats
        total_members = sum(guild.member_count for guild in self.bot.guilds)
        embed.add_field(
            name="📈 Stats",
            value=f"Servers: {len(self.bot.guilds)}\n"
                  f"Members: {total_members}\n"
                  f"Commands: {len(self.bot.commands)}",
            inline=True
        )
        
        # Memory usage
        process = psutil.Process()
        memory_usage = process.memory_info().rss / 1024 / 1024  # Convert to MB
        embed.add_field(
            name="💾 Memory",
            value=f"Used: {memory_usage:.2f} MB",
            inline=True
        )
        
        # Add bot owner info if available
        if self.bot.config.get('owner_ids'):
            owner_mentions = []
            for owner_id in self.bot.config['owner_ids']:
                owner = self.bot.get_user(owner_id)
                if owner:
                    owner_mentions.append(owner.mention)
            
            if owner_mentions:
                embed.add_field(
                    name="👑 Owners",
                    value="\n".join(owner_mentions),
                    inline=False
                )
        
        embed.set_footer(text="Developed By Lickzy")
        await ctx.send(embed=embed)

    @commands.command()
    async def invite(self, ctx):
        """Get the bot's invite link"""
        permissions = discord.Permissions(
            administrator=True,  # For full functionality
            # Add specific permissions if you don't want to use administrator
        )
        
        invite_url = discord.utils.oauth_url(
            self.bot.user.id,
            permissions=permissions,
            scopes=["bot", "applications.commands"]
        )
        
        embed = discord.Embed(
            title="🔗 Invite Bot",
            description=f"Click [here]({invite_url}) to invite the bot to your server!",
            color=discord.Color.blue()
        )
        embed.set_footer(text="Developed By Lickzy")
        await ctx.send(embed=embed)

    @commands.command()
    async def serverinfo(self, ctx):
        """Get information about the current server"""
        guild = ctx.guild
        
        # Get member counts
        total_members = guild.member_count
        human_members = len([m for m in guild.members if not m.bot])
        bot_members = len([m for m in guild.members if m.bot])
        
        # Get channel counts
        text_channels = len(guild.text_channels)
        voice_channels = len(guild.voice_channels)
        categories = len(guild.categories)
        
        embed = discord.Embed(
            title=f"Server Information - {guild.name}",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        
        # General info
        embed.add_field(
            name="📊 General",
            value=f"Owner: {guild.owner.mention}\n"
                  f"Created: <t:{int(guild.created_at.timestamp())}:R>\n"
                  f"Region: {str(guild.region).title()}\n"
                  f"Boost Level: {guild.premium_tier}",
            inline=False
        )
        
        # Member stats
        embed.add_field(
            name="👥 Members",
            value=f"Total: {total_members}\n"
                  f"Humans: {human_members}\n"
                  f"Bots: {bot_members}",
            inline=True
        )
        
        # Channel stats
        embed.add_field(
            name="📚 Channels",
            value=f"Text: {text_channels}\n"
                  f"Voice: {voice_channels}\n"
                  f"Categories: {categories}",
            inline=True
        )
        
        # Role info
        embed.add_field(
            name="🎭 Roles",
            value=f"Count: {len(guild.roles)}\n"
                  f"Highest: {guild.roles[-1].mention}",
            inline=True
        )
        embed.set_footer(text="Developed By Lickzy")
        await ctx.send(embed=embed)

    @commands.command()
    async def userinfo(self, ctx, member: Optional[discord.Member] = None):
        """Get information about a user"""
        member = member or ctx.author
        
        embed = discord.Embed(
            title=f"User Information - {member}",
            color=member.color,
            timestamp=datetime.utcnow()
        )
        
        if member.avatar:
            embed.set_thumbnail(url=member.avatar.url)
        
        # General info
        embed.add_field(
            name="📊 General",
            value=f"ID: {member.id}\n"
                  f"Created: <t:{int(member.created_at.timestamp())}:R>\n"
                  f"Joined: <t:{int(member.joined_at.timestamp())}:R>\n"
                  f"Bot: {'Yes' if member.bot else 'No'}",
            inline=False
        )
        
        # Roles
        roles = [role.mention for role in reversed(member.roles[1:])]  # Exclude @everyone
        embed.add_field(
            name=f"🎭 Roles ({len(roles)})",
            value=" ".join(roles) if roles else "None",
            inline=False
        )
        
        # Permissions
        key_permissions = []
        if member.guild_permissions.administrator:
            key_permissions.append("Administrator")
        if member.guild_permissions.manage_guild:
            key_permissions.append("Manage Server")
        if member.guild_permissions.manage_roles:
            key_permissions.append("Manage Roles")
        if member.guild_permissions.manage_channels:
            key_permissions.append("Manage Channels")
        if member.guild_permissions.manage_messages:
            key_permissions.append("Manage Messages")
        if member.guild_permissions.kick_members:
            key_permissions.append("Kick Members")
        if member.guild_permissions.ban_members:
            key_permissions.append("Ban Members")
        
        if key_permissions:
            embed.add_field(
                name="🔑 Key Permissions",
                value="\n".join(key_permissions),
                inline=False
            )
        
        # Check if user has premium
        if hasattr(self.bot, 'premium_users') and member.id in self.bot.premium_users:
            embed.add_field(
                name="💎 Premium Status",
                value="Active",
                inline=True
            )
        
        # Get user badges
        if hasattr(self.bot, 'badge_cache'):
            user_badges = self.bot.badge_cache.get(member.id, [])
            if user_badges:
                badge_text = " ".join(badge['emoji'] for badge in user_badges)
                embed.add_field(
                    name="🏆 Badges",
                    value=badge_text,
                    inline=True
                )
        embed.set_footer(text="Developed By Lickzy")
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Utility(bot))
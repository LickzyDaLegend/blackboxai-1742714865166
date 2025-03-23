import discord
from discord.ext import commands
import json
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Set
from collections import defaultdict, deque

from utils.logger import Logger, SecurityLogger
from utils.database import SecurityManager

logger = Logger.get_logger()

class Security(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        with open('config.json', 'r') as f:
            self.config = json.load(f)
        
        # Anti-spam settings
        self.message_history = defaultdict(lambda: deque(maxlen=10))
        self.spam_cooldown = commands.CooldownMapping.from_cooldown(
            5, 5, commands.BucketType.member
        )
        
        # Anti-raid settings
        self.join_history = deque(maxlen=100)
        self.raid_detection_window = timedelta(seconds=10)
        self.raid_join_threshold = 10
        
        # Cached settings
        self.whitelist = set()
        self.ignored_channels = set()
        self.muted_users = set()
        
        # Load settings
        self.security_settings = self.config.get('security', {})
        self.anti_spam_enabled = self.security_settings.get('anti_spam', {}).get('enabled', True)
        self.anti_raid_enabled = self.security_settings.get('anti_raid', {}).get('enabled', True)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Handle member joins and raid detection"""
        if not self.anti_raid_enabled:
            return

        current_time = datetime.utcnow()
        self.join_history.append((member, current_time))
        
        # Check for raid
        recent_joins = [j for j, t in self.join_history 
                       if current_time - t <= self.raid_detection_window]
        
        if len(recent_joins) >= self.raid_join_threshold:
            await self._handle_raid(member.guild, recent_joins)

    async def _handle_raid(self, guild: discord.Guild, suspicious_members: List[discord.Member]):
        """Handle detected raid"""
        try:
            # Log raid detection
            await SecurityLogger.log_security_event(
                guild,
                "RAID_DETECTED",
                f"Detected {len(suspicious_members)} joins in quick succession"
            )
            
            # Enable server lockdown
            await self._lockdown_server(guild, True)
            
            # Take action against suspicious members
            for member in suspicious_members:
                if not member.bot and not member.id in self.whitelist:
                    try:
                        await member.kick(reason="Raid detection - Automatic action")
                        await SecurityManager.log_security_event(
                            guild.id,
                            "RAID_KICK",
                            member.id,
                            "Member kicked due to raid detection"
                        )
                    except discord.Forbidden:
                        logger.warning(f"Failed to kick potential raider {member.id}")
            
        except Exception as e:
            logger.error(f"Error handling raid: {e}")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Handle message spam detection"""
        if not self.anti_spam_enabled or not message.guild:
            return
            
        if message.author.bot or message.author.id in self.whitelist:
            return
            
        if message.channel.id in self.ignored_channels:
            return

        # Check for spam
        bucket = self.spam_cooldown.get_bucket(message)
        retry_after = bucket.update_rate_limit()
        
        if retry_after:
            await self._handle_spam(message)
            return

        # Check message content
        await self._check_message_content(message)

    async def _handle_spam(self, message: discord.Message):
        """Handle detected spam"""
        try:
            # Delete spam message
            await message.delete()
            
            # Warn or mute repeat offenders
            spam_count = len(self.message_history[message.author.id])
            if spam_count >= 3 and message.author.id not in self.muted_users:
                # Mute user
                muted_role = discord.utils.get(message.guild.roles, name="Muted")
                if muted_role:
                    await message.author.add_roles(muted_role)
                    self.muted_users.add(message.author.id)
                    
                    # Log mute action
                    await SecurityLogger.log_security_event(
                        message.guild,
                        "SPAM_MUTE",
                        f"{message.author} was muted for spam"
                    )
                    
                    # Remove mute after 10 minutes
                    await asyncio.sleep(600)
                    if message.author.id in self.muted_users:
                        await message.author.remove_roles(muted_role)
                        self.muted_users.remove(message.author.id)
            
        except Exception as e:
            logger.error(f"Error handling spam: {e}")

    async def _check_message_content(self, message: discord.Message):
        """Check message content for suspicious patterns"""
        content = message.content.lower()
        
        # Check for mass mentions
        if len(message.mentions) > self.security_settings.get('max_mentions', 5):
            await message.delete()
            await SecurityLogger.log_security_event(
                message.guild,
                "MASS_MENTION",
                f"{message.author} used mass mentions"
            )
            return
            
        # Check for invite links
        if "discord.gg/" in content and not message.author.guild_permissions.manage_guild:
            await message.delete()
            await SecurityLogger.log_security_event(
                message.guild,
                "INVITE_LINK",
                f"{message.author} posted an invite link"
            )
            return

    async def _lockdown_server(self, guild: discord.Guild, lock: bool = True):
        """Lock/unlock all channels in the server"""
        try:
            for channel in guild.channels:
                if isinstance(channel, discord.TextChannel):
                    await channel.set_permissions(
                        guild.default_role,
                        send_messages=not lock
                    )
            
            action = "Lockdown" if lock else "Unlock"
            await SecurityLogger.log_security_event(
                guild,
                f"SERVER_{action}",
                f"Server {action.lower()} {'enabled' if lock else 'disabled'}"
            )
            
        except Exception as e:
            logger.error(f"Error during server lockdown: {e}")

    @commands.group(invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def security(self, ctx):
        """Security command group"""
        embed = discord.Embed(
            title="Security Settings",
            description="Current security configuration",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="Anti-Spam",
            value=f"{'✅' if self.anti_spam_enabled else '❌'} Enabled",
            inline=True
        )
        embed.add_field(
            name="Anti-Raid",
            value=f"{'✅' if self.anti_raid_enabled else '❌'} Enabled",
            inline=True
        )
        embed.add_field(
            name="Whitelisted Users",
            value=str(len(self.whitelist)),
            inline=True
        )
        
        embed.set_footer(text="Developed By Lickzy")
        await ctx.send(embed=embed)

    @security.command(name="antispam")
    @commands.has_permissions(administrator=True)
    async def toggle_antispam(self, ctx, state: bool):
        """Toggle anti-spam system"""
        self.anti_spam_enabled = state
        self.security_settings['anti_spam']['enabled'] = state
        
        with open('config.json', 'w') as f:
            json.dump(self.config, f, indent=4)
            
        await ctx.send(f"Anti-spam has been {'enabled' if state else 'disabled'}.")

    @security.command(name="antiraid")
    @commands.has_permissions(administrator=True)
    async def toggle_antiraid(self, ctx, state: bool):
        """Toggle anti-raid system"""
        self.anti_raid_enabled = state
        self.security_settings['anti_raid']['enabled'] = state
        
        with open('config.json', 'w') as f:
            json.dump(self.config, f, indent=4)
            
        await ctx.send(f"Anti-raid has been {'enabled' if state else 'disabled'}.")

    @security.command(name="whitelist")
    @commands.has_permissions(administrator=True)
    async def whitelist_user(self, ctx, user: discord.Member):
        """Add/remove a user from the security whitelist"""
        if user.id in self.whitelist:
            self.whitelist.remove(user.id)
            await ctx.send(f"Removed {user.mention} from the security whitelist.")
        else:
            self.whitelist.add(user.id)
            await ctx.send(f"Added {user.mention} to the security whitelist.")

    @security.command(name="ignore")
    @commands.has_permissions(administrator=True)
    async def ignore_channel(self, ctx, channel: discord.TextChannel = None):
        """Add/remove a channel from security checks"""
        channel = channel or ctx.channel
        
        if channel.id in self.ignored_channels:
            self.ignored_channels.remove(channel.id)
            await ctx.send(f"Removed {channel.mention} from ignored channels.")
        else:
            self.ignored_channels.add(channel.id)
            await ctx.send(f"Added {channel.mention} to ignored channels.")

    @security.command(name="lockdown")
    @commands.has_permissions(administrator=True)
    async def lockdown(self, ctx, state: bool):
        """Lock/unlock the server"""
        await self._lockdown_server(ctx.guild, state)
        await ctx.send(f"Server has been {'locked' if state else 'unlocked'}.")

async def setup(bot):
    await bot.add_cog(Security(bot))
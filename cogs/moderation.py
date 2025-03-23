import discord
from discord.ext import commands
from typing import Optional, Union
import asyncio
from datetime import datetime, timedelta

from utils.logger import ModLogger, Logger
from utils.database import WarningManager

logger = Logger.get_logger()

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.snipe_message = {}
        self.edit_snipe_message = {}
        self.ignored_channels = set()

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        """Store deleted messages for snipe command"""
        if not message.guild or message.author.bot:
            return
        if message.channel.id in self.ignored_channels:
            return
        self.snipe_message[message.channel.id] = {
            'content': message.content,
            'author': message.author,
            'timestamp': datetime.utcnow()
        }

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        """Store edited messages for editsnipe command"""
        if not before.guild or before.author.bot:
            return
        if before.channel.id in self.ignored_channels:
            return
        self.edit_snipe_message[before.channel.id] = {
            'before': before.content,
            'after': after.content,
            'author': before.author,
            'timestamp': datetime.utcnow()
        }

    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member, *, reason: Optional[str] = "No reason provided"):
        """Ban a member from the server"""
        try:
            if member.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
                await ctx.send("You cannot ban someone with a higher or equal role!")
                return

            await member.ban(reason=f"Banned by {ctx.author}: {reason}")
            await ModLogger.log_mod_action(ctx, "ban", member, reason)
            
            embed = discord.Embed(
                title="Member Banned",
                description=f"{member.mention} has been banned",
                color=discord.Color.red()
            )
            embed.add_field(name="Reason", value=reason)
            embed.set_footer(text="Developed By Lickzy")
            
            await ctx.send(embed=embed)
            
        except discord.Forbidden:
            await ctx.send("I don't have permission to ban that member!")
        except Exception as e:
            logger.error(f"Error in ban command: {e}")
            await ctx.send("An error occurred while trying to ban the member.")

    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx, user_id: int, *, reason: Optional[str] = "No reason provided"):
        """Unban a user by their ID"""
        try:
            banned_users = [entry async for entry in ctx.guild.bans()]
            user = discord.Object(id=user_id)
            
            if not any(entry.user.id == user_id for entry in banned_users):
                await ctx.send("This user is not banned!")
                return
                
            await ctx.guild.unban(user, reason=f"Unbanned by {ctx.author}: {reason}")
            await ModLogger.log_mod_action(ctx, "unban", user, reason)
            
            embed = discord.Embed(
                title="User Unbanned",
                description=f"User ID: {user_id} has been unbanned",
                color=discord.Color.green()
            )
            embed.add_field(name="Reason", value=reason)
            embed.set_footer(text="Developed By Lickzy")
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in unban command: {e}")
            await ctx.send("An error occurred while trying to unban the user.")

    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason: Optional[str] = "No reason provided"):
        """Kick a member from the server"""
        try:
            if member.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
                await ctx.send("You cannot kick someone with a higher or equal role!")
                return

            await member.kick(reason=f"Kicked by {ctx.author}: {reason}")
            await ModLogger.log_mod_action(ctx, "kick", member, reason)
            
            embed = discord.Embed(
                title="Member Kicked",
                description=f"{member.mention} has been kicked",
                color=discord.Color.orange()
            )
            embed.add_field(name="Reason", value=reason)
            embed.set_footer(text="Developed By Lickzy")
            
            await ctx.send(embed=embed)
            
        except discord.Forbidden:
            await ctx.send("I don't have permission to kick that member!")
        except Exception as e:
            logger.error(f"Error in kick command: {e}")
            await ctx.send("An error occurred while trying to kick the member.")

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def warn(self, ctx, member: discord.Member, *, reason: str):
        """Warn a member"""
        try:
            success = await WarningManager.add_warning(
                ctx.guild.id, 
                member.id,
                reason,
                ctx.author.id
            )
            
            if success:
                await ModLogger.log_mod_action(ctx, "warn", member, reason)
                
                embed = discord.Embed(
                    title="Member Warned",
                    description=f"{member.mention} has been warned",
                    color=discord.Color.yellow()
                )
                embed.add_field(name="Reason", value=reason)
                embed.set_footer(text="Developed By Lickzy")
                
                await ctx.send(embed=embed)
            else:
                await ctx.send("Failed to add warning to the database.")
                
        except Exception as e:
            logger.error(f"Error in warn command: {e}")
            await ctx.send("An error occurred while trying to warn the member.")

    @commands.command(name="warnings")
    @commands.has_permissions(manage_messages=True)
    async def list_warnings(self, ctx, member: discord.Member):
        """List all warnings for a member"""
        try:
            warnings = await WarningManager.get_warnings(ctx.guild.id, member.id)
            
            if not warnings:
                await ctx.send(f"{member.mention} has no warnings.")
                return
                
            embed = discord.Embed(
                title=f"Warnings for {member}",
                color=discord.Color.yellow()
            )
            
            for i, warning in enumerate(warnings, 1):
                mod = ctx.guild.get_member(warning['mod_id'])
                mod_name = mod.name if mod else "Unknown Moderator"
                timestamp = warning['timestamp'].strftime("%Y-%m-%d %H:%M:%S")
                
                embed.add_field(
                    name=f"Warning #{i}",
                    value=f"Reason: {warning['reason']}\n"
                          f"By: {mod_name}\n"
                          f"Date: {timestamp}",
                    inline=False
                )
                
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in list_warnings command: {e}")
            await ctx.send("An error occurred while trying to fetch warnings.")

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def purge(self, ctx, amount: int):
        """Purge a specified number of messages"""
        try:
            if amount <= 0:
                await ctx.send("Please specify a positive number of messages to delete!")
                return
                
            deleted = await ctx.channel.purge(limit=amount + 1)  # +1 to include command message
            await ModLogger.log_mod_action(ctx, "purge", ctx.channel, f"Purged {len(deleted)-1} messages")
            
            confirm_message = await ctx.send(f"Purged {len(deleted)-1} messages!")
            await asyncio.sleep(3)
            await confirm_message.delete()
            
        except discord.Forbidden:
            await ctx.send("I don't have permission to delete messages!")
        except Exception as e:
            logger.error(f"Error in purge command: {e}")
            await ctx.send("An error occurred while trying to purge messages.")

    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def lock(self, ctx, channel: Optional[discord.TextChannel] = None):
        """Lock a channel"""
        channel = channel or ctx.channel
        try:
            await channel.set_permissions(ctx.guild.default_role, send_messages=False)
            await ModLogger.log_mod_action(ctx, "lock", channel)
            
            embed = discord.Embed(
                title="Channel Locked",
                description=f"{channel.mention} has been locked",
                color=discord.Color.red()
            )
            embed.set_footer(text=f"Locked by {ctx.author}")
            
            await ctx.send(embed=embed)
            
        except discord.Forbidden:
            await ctx.send("I don't have permission to manage channel permissions!")
        except Exception as e:
            logger.error(f"Error in lock command: {e}")
            await ctx.send("An error occurred while trying to lock the channel.")

    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def unlock(self, ctx, channel: Optional[discord.TextChannel] = None):
        """Unlock a channel"""
        channel = channel or ctx.channel
        try:
            await channel.set_permissions(ctx.guild.default_role, send_messages=None)
            await ModLogger.log_mod_action(ctx, "unlock", channel)
            
            embed = discord.Embed(
                title="Channel Unlocked",
                description=f"{channel.mention} has been unlocked",
                color=discord.Color.green()
            )
            embed.set_footer(text=f"Unlocked by {ctx.author}")
            
            await ctx.send(embed=embed)
            
        except discord.Forbidden:
            await ctx.send("I don't have permission to manage channel permissions!")
        except Exception as e:
            logger.error(f"Error in unlock command: {e}")
            await ctx.send("An error occurred while trying to unlock the channel.")

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def snipe(self, ctx):
        """Show the last deleted message in the channel"""
        message_data = self.snipe_message.get(ctx.channel.id)
        
        if not message_data:
            await ctx.send("There are no deleted messages to snipe!")
            return
            
        embed = discord.Embed(
            description=message_data['content'],
            color=discord.Color.red(),
            timestamp=message_data['timestamp']
        )
        embed.set_author(
            name=message_data['author'].name,
            icon_url=message_data['author'].avatar.url if message_data['author'].avatar else None
        )
        embed.set_footer(text="Developed By Lickzy")
        await ctx.send(embed=embed)

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def editsnipe(self, ctx):
        """Show the last edited message in the channel"""
        message_data = self.edit_snipe_message.get(ctx.channel.id)
        
        if not message_data:
            await ctx.send("There are no edited messages to snipe!")
            return
            
        embed = discord.Embed(
            color=discord.Color.blue(),
            timestamp=message_data['timestamp']
        )
        embed.add_field(name="Before", value=message_data['before'], inline=False)
        embed.add_field(name="After", value=message_data['after'], inline=False)
        embed.set_author(
            name=message_data['author'].name,
            icon_url=message_data['author'].avatar.url if message_data['author'].avatar else None
        )
        embed.set_footer(text="Developed By Lickzy")
        await ctx.send(embed=embed)

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def ignore(self, ctx, channel: discord.TextChannel = None):
        """Ignore a channel for message logging"""
        channel = channel or ctx.channel
        if channel.id in self.ignored_channels:
            self.ignored_channels.remove(channel.id)
            await ctx.send(f"Unignored {channel.mention} for message logging.")
        else:
            self.ignored_channels.add(channel.id)
            await ctx.send(f"Now ignoring {channel.mention} for message logging.")

    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def lockall(self, ctx):
        """Lock all channels in the server"""
        success = 0
        failed = 0
        
        for channel in ctx.guild.text_channels:
            try:
                await channel.set_permissions(ctx.guild.default_role, send_messages=False)
                success += 1
            except:
                failed += 1
                
        embed = discord.Embed(
            title="Server Lockdown",
            description=f"Successfully locked {success} channels.\nFailed to lock {failed} channels.",
            color=discord.Color.red()
        )
        embed.set_footer(text="Developed By Lickzy")
        await ctx.send(embed=embed)

    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def unlockall(self, ctx):
        """Unlock all channels in the server"""
        success = 0
        failed = 0
        
        for channel in ctx.guild.text_channels:
            try:
                await channel.set_permissions(ctx.guild.default_role, send_messages=None)
                success += 1
            except:
                failed += 1
                
        embed = discord.Embed(
            title="Server Unlocked",
            description=f"Successfully unlocked {success} channels.\nFailed to unlock {failed} channels.",
            color=discord.Color.green()
        )
        embed.set_footer(text="Developed By Lickzy")
        await ctx.send(embed=embed)

    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def hide(self, ctx, channel: discord.TextChannel = None):
        """Hide a channel"""
        channel = channel or ctx.channel
        try:
            await channel.set_permissions(ctx.guild.default_role, view_channel=False)
            embed = discord.Embed(
                title="Channel Hidden",
                description=f"{channel.mention} has been hidden",
                color=discord.Color.blue()
            )
            embed.set_footer(text="Developed By Lickzy")
            await ctx.send(embed=embed)
        except:
            await ctx.send("Failed to hide the channel!")

    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def unhide(self, ctx, channel: discord.TextChannel = None):
        """Unhide a channel"""
        channel = channel or ctx.channel
        try:
            await channel.set_permissions(ctx.guild.default_role, view_channel=None)
            embed = discord.Embed(
                title="Channel Unhidden",
                description=f"{channel.mention} has been unhidden",
                color=discord.Color.blue()
            )
            embed.set_footer(text="Developed By Lickzy")
            await ctx.send(embed=embed)
        except:
            await ctx.send("Failed to unhide the channel!")

    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def hideall(self, ctx):
        """Hide all channels"""
        success = 0
        failed = 0
        
        for channel in ctx.guild.text_channels:
            try:
                await channel.set_permissions(ctx.guild.default_role, view_channel=False)
                success += 1
            except:
                failed += 1
                
        embed = discord.Embed(
            title="All Channels Hidden",
            description=f"Successfully hidden {success} channels.\nFailed to hide {failed} channels.",
            color=discord.Color.blue()
        )
        embed.set_footer(text="Developed By Lickzy")
        await ctx.send(embed=embed)

    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def unhideall(self, ctx):
        """Unhide all channels"""
        success = 0
        failed = 0
        
        for channel in ctx.guild.text_channels:
            try:
                await channel.set_permissions(ctx.guild.default_role, view_channel=None)
                success += 1
            except:
                failed += 1
                
        embed = discord.Embed(
            title="All Channels Unhidden",
            description=f"Successfully unhidden {success} channels.\nFailed to unhide {failed} channels.",
            color=discord.Color.blue()
        )
        embed.set_footer(text="Developed By Lickzy")
        await ctx.send(embed=embed)

    @commands.command()
    @commands.has_permissions(manage_roles=True)
    async def role(self, ctx, member: discord.Member, *, role: discord.Role):
        """Add or remove a role from a member"""
        try:
            if role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
                await ctx.send("You can't manage roles higher than your own!")
                return
                
            if role in member.roles:
                await member.remove_roles(role)
                action = "removed from"
            else:
                await member.add_roles(role)
                action = "added to"
                
            embed = discord.Embed(
                title="Role Updated",
                description=f"{role.mention} has been {action} {member.mention}",
                color=role.color
            )
            embed.set_footer(text="Developed By Lickzy")
            await ctx.send(embed=embed)
            
        except discord.Forbidden:
            await ctx.send("I don't have permission to manage that role!")
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def mute(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        """Mute a member"""
        muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
        
        if not muted_role:
            try:
                muted_role = await ctx.guild.create_role(
                    name="Muted",
                    reason="To use for muting",
                    permissions=discord.Permissions(
                        send_messages=False,
                        speak=False
                    )
                )
                
                for channel in ctx.guild.channels:
                    await channel.set_permissions(muted_role, send_messages=False, speak=False)
            except discord.Forbidden:
                await ctx.send("I don't have permission to create a muted role!")
                return
                
        try:
            if muted_role in member.roles:
                await ctx.send(f"{member.mention} is already muted!")
                return
                
            await member.add_roles(muted_role, reason=reason)
            embed = discord.Embed(
                title="Member Muted",
                description=f"{member.mention} has been muted",
                color=discord.Color.red()
            )
            embed.add_field(name="Reason", value=reason)
            embed.set_footer(text="Developed By Lickzy")
            await ctx.send(embed=embed)
            
        except discord.Forbidden:
            await ctx.send("I don't have permission to mute that member!")
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def unmute(self, ctx, member: discord.Member):
        """Unmute a member"""
        muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
        
        if not muted_role:
            await ctx.send("There is no muted role to remove!")
            return
            
        try:
            await member.remove_roles(muted_role)
            embed = discord.Embed(
                title="Member Unmuted",
                description=f"{member.mention} has been unmuted",
                color=discord.Color.green()
            )
            embed.set_footer(text="Developed By Lickzy")
            await ctx.send(embed=embed)
            
        except discord.Forbidden:
            await ctx.send("I don't have permission to unmute that member!")
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def mediachannel(self, ctx, channel: discord.TextChannel = None):
        """Set a channel to only allow media content"""
        channel = channel or ctx.channel
        
        try:
            def check_media(m):
                return bool(m.attachments) or bool(m.embeds)
            
            await channel.set_permissions(ctx.guild.default_role, send_messages=True)
            await ctx.send(f"Set {channel.mention} to media-only mode. Messages without media will be deleted.")
            
        except discord.Forbidden:
            await ctx.send("I don't have permission to manage that channel!")
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    @commands.command()
    @commands.has_permissions(manage_nicknames=True)
    async def nickname(self, ctx, member: discord.Member, *, new_nick: str = None):
        """Change a member's nickname"""
        try:
            old_nick = member.nick or member.name
            await member.edit(nick=new_nick)
            
            embed = discord.Embed(
                title="Nickname Changed",
                color=discord.Color.blue()
            )
            embed.add_field(name="Member", value=member.mention, inline=False)
            embed.add_field(name="Old Nickname", value=old_nick, inline=True)
            embed.add_field(name="New Nickname", value=new_nick or "Reset to username", inline=True)
            embed.set_footer(text="Developed By Lickzy")
            await ctx.send(embed=embed)
            
        except discord.Forbidden:
            await ctx.send("I don't have permission to change that member's nickname!")
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def unbanall(self, ctx):
        """Unban all members"""
        try:
            banned_users = [entry async for entry in ctx.guild.bans()]
            unbanned_count = 0
            
            for ban_entry in banned_users:
                await ctx.guild.unban(ban_entry.user)
                unbanned_count += 1
                
            embed = discord.Embed(
                title="Mass Unban",
                description=f"Successfully unbanned {unbanned_count} members",
                color=discord.Color.green()
            )
            embed.set_footer(text="Developed By Lickzy")
            await ctx.send(embed=embed)
            
        except discord.Forbidden:
            await ctx.send("I don't have permission to unban members!")
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

async def setup(bot):
    await bot.add_cog(Moderation(bot))

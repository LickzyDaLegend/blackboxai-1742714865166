import discord
from discord.ext import commands
import json
from datetime import datetime
from typing import Optional, List, Dict

from utils.logger import Logger
from utils.database import BadgeManager

logger = Logger.get_logger()

class Badges(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        with open('config.json', 'r') as f:
            self.config = json.load(f)
            
        # Define available badges
        self.available_badges = {
            "developer": {
                "name": "Bot Developer",
                "emoji": "👨‍💻",
                "description": "Official bot developer",
                "color": 0x1abc9c
            },
            "admin": {
                "name": "Bot Admin",
                "emoji": "⚡",
                "description": "Official bot administrator",
                "color": 0xe74c3c
            },
            "owner": {
                "name": "Bot Owner",
                "emoji": "👑",
                "description": "Official bot owner",
                "color": 0xf1c40f
            },
            "premium": {
                "name": "Premium User",
                "emoji": "💎",
                "description": "Premium bot user",
                "color": 0x9b59b6
            },
            "supporter": {
                "name": "Early Supporter",
                "emoji": "🎗️",
                "description": "Supported the bot since early days",
                "color": 0x2ecc71
            },
            "bug_hunter": {
                "name": "Bug Hunter",
                "emoji": "🐛",
                "description": "Found and reported critical bugs",
                "color": 0xe67e22
            },
            "contributor": {
                "name": "Contributor",
                "emoji": "🛠️",
                "description": "Contributed to bot development",
                "color": 0x3498db
            }
        }

    def is_authorized(self, user_id: int) -> bool:
        """Check if a user is authorized to manage badges"""
        return (
            user_id in self.config.get('owner_ids', []) or
            user_id in self.config.get('admin_ids', []) or
            user_id in self.config.get('developer_ids', [])
        )

    @commands.group(invoke_without_command=True)
    async def badge(self, ctx):
        """Badge system commands"""
        await ctx.send("Available commands: list, info, view, grant, revoke")

    @badge.command(name="list")
    async def badge_list(self, ctx):
        """List all available badges"""
        embed = discord.Embed(
            title="Available Badges",
            description="Here are all the badges that can be earned:",
            color=discord.Color.blue()
        )
        
        for badge_id, badge_info in self.available_badges.items():
            embed.add_field(
                name=f"{badge_info['emoji']} {badge_info['name']}",
                value=f"{badge_info['description']}\nID: `{badge_id}`",
                inline=True
            )
        
        await ctx.send(embed=embed)

    @badge.command(name="info")
    async def badge_info(self, ctx, badge_id: str):
        """Get detailed information about a badge"""
        if badge_id not in self.available_badges:
            await ctx.send("Invalid badge ID!")
            return
            
        badge = self.available_badges[badge_id]
        embed = discord.Embed(
            title=f"{badge['emoji']} {badge['name']}",
            description=badge['description'],
            color=badge['color']
        )
        
        embed.add_field(name="Badge ID", value=f"`{badge_id}`")
        await ctx.send(embed=embed)

    @badge.command(name="view")
    async def badge_view(self, ctx, user: Optional[discord.Member] = None):
        """View badges of a user"""
        user = user or ctx.author
        
        try:
            user_badges = await BadgeManager.get_user_badges(user.id)
            
            if not user_badges:
                await ctx.send(f"{user.mention} doesn't have any badges!")
                return
                
            embed = discord.Embed(
                title=f"Badges for {user}",
                color=discord.Color.gold()
            )
            
            for badge_data in user_badges:
                badge_id = badge_data['badge_name']
                if badge_id in self.available_badges:
                    badge = self.available_badges[badge_id]
                    awarded_by = self.bot.get_user(badge_data['awarded_by'])
                    awarded_by_text = str(awarded_by) if awarded_by else "Unknown"
                    
                    embed.add_field(
                        name=f"{badge['emoji']} {badge['name']}",
                        value=f"Awarded by: {awarded_by_text}\n"
                              f"Date: {badge_data['awarded_at'].strftime('%Y-%m-%d')}",
                        inline=False
                    )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error viewing badges: {e}")
            await ctx.send("An error occurred while viewing badges.")

    @badge.command(name="grant")
    async def badge_grant(self, ctx, user: discord.Member, badge_id: str):
        """Grant a badge to a user"""
        if not self.is_authorized(ctx.author.id):
            await ctx.send("You don't have permission to grant badges!")
            return
            
        if badge_id not in self.available_badges:
            await ctx.send("Invalid badge ID!")
            return
            
        try:
            success = await BadgeManager.add_badge(
                user.id,
                badge_id,
                ctx.author.id
            )
            
            if success:
                badge = self.available_badges[badge_id]
                embed = discord.Embed(
                    title="Badge Granted",
                    description=f"Granted {badge['emoji']} {badge['name']} to {user.mention}!",
                    color=badge['color']
                )
                await ctx.send(embed=embed)
            else:
                await ctx.send("Failed to grant badge.")
                
        except Exception as e:
            logger.error(f"Error granting badge: {e}")
            await ctx.send("An error occurred while granting the badge.")

    @badge.command(name="revoke")
    async def badge_revoke(self, ctx, user: discord.Member, badge_id: str):
        """Revoke a badge from a user"""
        if not self.is_authorized(ctx.author.id):
            await ctx.send("You don't have permission to revoke badges!")
            return
            
        if badge_id not in self.available_badges:
            await ctx.send("Invalid badge ID!")
            return
            
        try:
            success = await BadgeManager.remove_badge(user.id, badge_id)
            
            if success:
                badge = self.available_badges[badge_id]
                embed = discord.Embed(
                    title="Badge Revoked",
                    description=f"Revoked {badge['emoji']} {badge['name']} from {user.mention}!",
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed)
            else:
                await ctx.send("Failed to revoke badge.")
                
        except Exception as e:
            logger.error(f"Error revoking badge: {e}")
            await ctx.send("An error occurred while revoking the badge.")

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Display member badges in welcome message"""
        try:
            user_badges = await BadgeManager.get_user_badges(member.id)
            if user_badges:
                badge_text = " ".join(
                    self.available_badges[badge['badge_name']]['emoji']
                    for badge in user_badges
                    if badge['badge_name'] in self.available_badges
                )
                
                if badge_text:
                    embed = discord.Embed(
                        title="Member Joined",
                        description=f"Welcome {member.mention}!\nBadges: {badge_text}",
                        color=discord.Color.green()
                    )
                    
                    # Send to system channel if set
                    if member.guild.system_channel:
                        await member.guild.system_channel.send(embed=embed)
                        
        except Exception as e:
            logger.error(f"Error displaying member badges: {e}")

async def setup(bot):
    await bot.add_cog(Badges(bot))
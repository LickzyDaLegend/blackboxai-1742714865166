import discord
from discord.ext import commands
from datetime import datetime, timedelta
from typing import Optional
import asyncio

from utils.logger import Logger

logger = Logger.get_logger()

class Premium(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def grant_premium(self, ctx, member: discord.Member, days: Optional[int] = 30):
        """Grant premium status to a user"""
        try:
            # Get premium collection
            premium_collection = self.bot.mongo.discord_bot.premium_users
            
            # Calculate end date
            end_date = datetime.utcnow() + timedelta(days=days)
            
            # Add or update premium status
            await premium_collection.update_one(
                {'user_id': member.id},
                {
                    '$set': {
                        'user_id': member.id,
                        'granted_by': ctx.author.id,
                        'granted_at': datetime.utcnow(),
                        'end_date': end_date
                    }
                },
                upsert=True
            )
            
            # Add to bot's premium users set
            self.bot.premium_users.add(member.id)
            
            embed = discord.Embed(
                title="Premium Status Granted",
                description=f"Premium status has been granted to {member.mention}",
                color=discord.Color.gold(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="Duration", value=f"{days} days")
            embed.add_field(name="Expires", value=f"<t:{int(end_date.timestamp())}:R>")
            embed.set_footer(text="Developed By Lickzy")
            
            await ctx.send(embed=embed)
            
            # DM the user
            try:
                user_embed = discord.Embed(
                    title="🌟 Premium Status Activated!",
                    description="You have been granted premium status!",
                    color=discord.Color.gold()
                )
                user_embed.add_field(name="Duration", value=f"{days} days")
                user_embed.add_field(name="Expires", value=f"<t:{int(end_date.timestamp())}:R>")
                user_embed.add_field(
                    name="Features",
                    value="• Custom Colors\n• Advanced Stats\n• Extended Logs\n• Multiple Giveaways\n• Priority Support",
                    inline=False
                )
                user_embed.set_footer(text="Developed By Lickzy")
                
                await member.send(embed=user_embed)
            except:
                logger.warning(f"Could not DM user {member.id} about premium status")
            
        except Exception as e:
            logger.error(f"Error granting premium: {e}")
            await ctx.send("An error occurred while granting premium status.")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def revoke_premium(self, ctx, member: discord.Member):
        """Revoke premium status from a user"""
        try:
            # Get premium collection
            premium_collection = self.bot.mongo.discord_bot.premium_users
            
            # Remove from database
            result = await premium_collection.delete_one({'user_id': member.id})
            
            if result.deleted_count > 0:
                # Remove from bot's premium users set
                self.bot.premium_users.discard(member.id)
                
                embed = discord.Embed(
                    title="Premium Status Revoked",
                    description=f"Premium status has been revoked from {member.mention}",
                    color=discord.Color.red(),
                    timestamp=datetime.utcnow()
                )
                embed.set_footer(text="Developed By Lickzy")
                
                await ctx.send(embed=embed)
                
                # DM the user
                try:
                    user_embed = discord.Embed(
                        title="Premium Status Ended",
                        description="Your premium status has been revoked.",
                        color=discord.Color.red()
                    )
                    user_embed.set_footer(text="Developed By Lickzy")
                    
                    await member.send(embed=user_embed)
                except:
                    logger.warning(f"Could not DM user {member.id} about premium status revocation")
                    
            else:
                await ctx.send(f"{member.mention} does not have premium status.")
            
        except Exception as e:
            logger.error(f"Error revoking premium: {e}")
            await ctx.send("An error occurred while revoking premium status.")

    @commands.command()
    async def premium_status(self, ctx, member: Optional[discord.Member] = None):
        """Check premium status of a user"""
        member = member or ctx.author
        
        try:
            # Get premium collection
            premium_collection = self.bot.mongo.discord_bot.premium_users
            
            # Get premium status
            premium_data = await premium_collection.find_one({'user_id': member.id})
            
            if premium_data:
                end_date = premium_data['end_date']
                granted_at = premium_data['granted_at']
                granted_by = self.bot.get_user(premium_data['granted_by'])
                
                embed = discord.Embed(
                    title="Premium Status",
                    description=f"Premium status for {member.mention}",
                    color=discord.Color.gold(),
                    timestamp=datetime.utcnow()
                )
                embed.add_field(
                    name="Status",
                    value="Active ✅" if end_date > datetime.utcnow() else "Expired ❌",
                    inline=True
                )
                embed.add_field(
                    name="Granted By",
                    value=granted_by.mention if granted_by else "Unknown",
                    inline=True
                )
                embed.add_field(
                    name="Granted At",
                    value=f"<t:{int(granted_at.timestamp())}:R>",
                    inline=True
                )
                embed.add_field(
                    name="Expires",
                    value=f"<t:{int(end_date.timestamp())}:R>",
                    inline=True
                )
                embed.set_footer(text="Developed By Lickzy")
                
            else:
                embed = discord.Embed(
                    title="Premium Status",
                    description=f"{member.mention} does not have premium status.",
                    color=discord.Color.red()
                )
                embed.set_footer(text="Developed By Lickzy")
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error checking premium status: {e}")
            await ctx.send("An error occurred while checking premium status.")

async def setup(bot):
    await bot.add_cog(Premium(bot))
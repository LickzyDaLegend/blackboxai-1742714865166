import discord
from discord.ext import commands, tasks
import asyncio
from datetime import datetime, timedelta
import random
from typing import Optional, List, Dict
import json

from utils.logger import Logger, GiveawayLogger
from utils.database import GiveawayManager

logger = Logger.get_logger()

class Giveaways(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        with open('config.json', 'r') as f:
            self.config = json.load(f)
        self.active_giveaways = {}
        self.check_giveaways.start()

    def cog_unload(self):
        self.check_giveaways.cancel()

    @tasks.loop(seconds=30)
    async def check_giveaways(self):
        """Check and end expired giveaways"""
        try:
            current_time = datetime.utcnow()
            giveaways = await GiveawayManager.get_active_giveaways()
            
            for giveaway in giveaways:
                if current_time >= giveaway['end_time']:
                    await self.end_giveaway(giveaway['_id'])
                    
        except Exception as e:
            logger.error(f"Error checking giveaways: {e}")

    @check_giveaways.before_loop
    async def before_check_giveaways(self):
        """Wait for bot to be ready before starting loop"""
        await self.bot.wait_until_ready()

    async def end_giveaway(self, giveaway_id: str):
        """End a giveaway and select winners"""
        try:
            giveaway = await GiveawayManager.get_giveaway(giveaway_id)
            if not giveaway or not giveaway['active']:
                return

            channel = self.bot.get_channel(giveaway['channel_id'])
            if not channel:
                return

            try:
                message = await channel.fetch_message(giveaway['message_id'])
            except discord.NotFound:
                return

            # Get participants from reactions
            try:
                reaction = next(r for r in message.reactions if r.emoji == '🎉')
                users = [user async for user in reaction.users() if not user.bot]
            except (StopIteration, discord.NotFound):
                users = []

            # Select winners
            winner_count = min(len(users), giveaway['winner_count']) if users else 0
            winners = random.sample(users, winner_count) if winner_count > 0 else []

            # Update giveaway embed
            embed = message.embeds[0]
            embed.color = discord.Color.red() if not winners else discord.Color.green()
            
            if winners:
                winners_text = ", ".join(w.mention for w in winners)
                embed.description = f"🎉 Winners: {winners_text}\n\nPrize: {giveaway['prize']}"
            else:
                embed.description = f"Giveaway ended\nNo valid participants!\n\nPrize: {giveaway['prize']}"

            embed.set_footer(text="Developed By Lickzy")
            await message.edit(embed=embed)

            # Send winner announcement
            if winners:
                await channel.send(
                    f"🎉 Congratulations {', '.join(w.mention for w in winners)}! "
                    f"You won: **{giveaway['prize']}**"
                )

            # Log giveaway end
            await GiveawayLogger.log_giveaway_action(
                channel.guild,
                "ended",
                f"Giveaway for {giveaway['prize']} has ended. Winners: {len(winners)}"
            )

            # Update database
            await GiveawayManager.end_giveaway(giveaway_id)
            
        except Exception as e:
            logger.error(f"Error ending giveaway: {e}")

    @commands.group(invoke_without_command=True)
    @commands.has_permissions(manage_messages=True)
    async def giveaway(self, ctx):
        """Giveaway command group"""
        await ctx.send("Available commands: create, end, reroll, list")

    @giveaway.command(name="create")
    @commands.has_permissions(manage_messages=True)
    async def giveaway_create(self, ctx):
        """Create a new giveaway"""
        # Check if user has premium for multiple giveaways
        active_giveaways = await GiveawayManager.get_active_giveaways()
        if len(active_giveaways) >= 1 and not hasattr(ctx.author, 'premium'):
            await ctx.send("You need premium to run multiple giveaways!")
            return

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        try:
            # Get prize
            await ctx.send("What is the prize for this giveaway?")
            msg = await self.bot.wait_for('message', check=check, timeout=60)
            prize = msg.content

            # Get duration
            await ctx.send("How long should the giveaway last? (e.g. 1h, 1d, 1w)")
            msg = await self.bot.wait_for('message', check=check, timeout=60)
            
            duration = msg.content.lower()
            time_convert = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}
            time_unit = duration[-1]
            try:
                time_value = int(duration[:-1])
                seconds = time_value * time_convert[time_unit]
            except:
                await ctx.send("Invalid duration format! Use s/m/h/d/w (e.g. 1h, 1d)")
                return

            # Get winner count
            await ctx.send("How many winners should there be?")
            msg = await self.bot.wait_for('message', check=check, timeout=60)
            try:
                winner_count = int(msg.content)
                if winner_count < 1:
                    raise ValueError
            except:
                await ctx.send("Please provide a valid number of winners!")
                return

            # Create giveaway embed
            end_time = datetime.utcnow() + timedelta(seconds=seconds)
            embed = discord.Embed(
                title="🎉 Giveaway",
                description=f"React with 🎉 to enter!\n\n"
                          f"Prize: **{prize}**\n"
                          f"Winners: **{winner_count}**\n"
                          f"Ends: <t:{int(end_time.timestamp())}:R>",
                color=discord.Color.blue()
            )
            embed.set_footer(text="Developed By Lickzy")

            # Send giveaway message
            giveaway_msg = await ctx.send(embed=embed)
            await giveaway_msg.add_reaction("🎉")

            # Save to database
            await GiveawayManager.create_giveaway(
                ctx.guild.id,
                ctx.channel.id,
                giveaway_msg.id,
                prize,
                end_time,
                winner_count
            )

            # Log giveaway creation
            await GiveawayLogger.log_giveaway_action(
                ctx.guild,
                "created",
                f"New giveaway for {prize} created by {ctx.author}"
            )

        except asyncio.TimeoutError:
            await ctx.send("Giveaway creation timed out!")
        except Exception as e:
            logger.error(f"Error creating giveaway: {e}")
            await ctx.send("An error occurred while creating the giveaway!")

    @giveaway.command(name="end")
    @commands.has_permissions(manage_messages=True)
    async def giveaway_end(self, ctx, message_id: int):
        """End a giveaway early"""
        try:
            giveaway = await GiveawayManager.get_giveaway_by_message(message_id)
            if not giveaway:
                await ctx.send("Giveaway not found!")
                return

            await self.end_giveaway(giveaway['_id'])
            await ctx.send("Giveaway ended!")
            
        except Exception as e:
            logger.error(f"Error ending giveaway: {e}")
            await ctx.send("An error occurred while ending the giveaway!")

    @giveaway.command(name="reroll")
    @commands.has_permissions(manage_messages=True)
    async def giveaway_reroll(self, ctx, message_id: int):
        """Reroll a giveaway's winners"""
        try:
            message = await ctx.channel.fetch_message(message_id)
            if not message:
                await ctx.send("Message not found!")
                return

            # Get participants
            reaction = next((r for r in message.reactions if r.emoji == '🎉'), None)
            if not reaction:
                await ctx.send("No reactions found on this giveaway!")
                return

            users = [user async for user in reaction.users() if not user.bot]
            if not users:
                await ctx.send("No valid participants found!")
                return

            # Select new winner
            winner = random.choice(users)
            
            await ctx.send(f"🎉 New winner: {winner.mention}! Congratulations!")
            
            # Log reroll
            await GiveawayLogger.log_giveaway_action(
                ctx.guild,
                "rerolled",
                f"Giveaway {message_id} was rerolled. New winner: {winner}"
            )
            
        except Exception as e:
            logger.error(f"Error rerolling giveaway: {e}")
            await ctx.send("An error occurred while rerolling the giveaway!")

    @giveaway.command(name="list")
    @commands.has_permissions(manage_messages=True)
    async def giveaway_list(self, ctx):
        """List all active giveaways"""
        try:
            giveaways = await GiveawayManager.get_active_giveaways()
            
            if not giveaways:
                await ctx.send("No active giveaways!")
                return

            embed = discord.Embed(
                title="Active Giveaways",
                color=discord.Color.blue()
            )

            for giveaway in giveaways:
                channel = self.bot.get_channel(giveaway['channel_id'])
                if channel:
                    embed.add_field(
                        name=giveaway['prize'],
                        value=f"Channel: {channel.mention}\n"
                              f"Winners: {giveaway['winner_count']}\n"
                              f"Ends: <t:{int(giveaway['end_time'].timestamp())}:R>\n"
                              f"Message ID: {giveaway['message_id']}",
                        inline=False
                    )

            embed.set_footer(text="Developed By Lickzy")
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error listing giveaways: {e}")
            await ctx.send("An error occurred while listing giveaways!")

async def setup(bot):
    await bot.add_cog(Giveaways(bot))
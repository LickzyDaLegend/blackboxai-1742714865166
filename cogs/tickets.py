import discord
from discord.ext import commands
import json
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, List

from utils.logger import Logger, TicketLogger
from utils.database import TicketManager

logger = Logger.get_logger()

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Create Ticket",
        style=discord.ButtonStyle.green,
        emoji="🎫",
        custom_id="create_ticket"
    )
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        
        # Check if user already has an open ticket
        existing_ticket = await TicketManager.get_user_ticket(
            interaction.guild_id,
            interaction.user.id
        )
        
        if existing_ticket:
            await interaction.followup.send(
                "You already have an open ticket!",
                ephemeral=True
            )
            return

        try:
            # Get ticket category
            category = discord.utils.get(
                interaction.guild.categories,
                name="Tickets"
            )
            
            if not category:
                category = await interaction.guild.create_category("Tickets")

            # Create ticket channel
            channel_name = f"ticket-{interaction.user.name}"
            overwrites = {
                interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
            }
            
            channel = await interaction.guild.create_text_channel(
                channel_name,
                category=category,
                overwrites=overwrites
            )

            # Create ticket embed
            embed = discord.Embed(
                title="Ticket Created",
                description=(
                    f"Welcome {interaction.user.mention}!\n\n"
                    "Please describe your issue and wait for a staff member to assist you.\n"
                    "Use the buttons below to manage your ticket."
                ),
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            embed.set_footer(text="Developed By Lickzy")

            # Create ticket management view
            view = TicketManageView()
            message = await channel.send(embed=embed, view=view)
            await message.pin()

            # Save ticket to database
            await TicketManager.create_ticket(
                interaction.guild_id,
                channel.id,
                interaction.user.id,
                "support"
            )

            # Log ticket creation
            await TicketLogger.log_ticket_action(
                interaction.guild,
                "created",
                channel.id,
                f"Ticket created by {interaction.user}"
            )

            await interaction.followup.send(
                f"Ticket created! Check {channel.mention}",
                ephemeral=True
            )

        except Exception as e:
            logger.error(f"Error creating ticket: {e}")
            await interaction.followup.send(
                "An error occurred while creating your ticket!",
                ephemeral=True
            )

class TicketManageView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Close",
        style=discord.ButtonStyle.red,
        emoji="🔒",
        custom_id="close_ticket"
    )
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        
        try:
            # Update ticket status
            await TicketManager.close_ticket(
                interaction.guild_id,
                interaction.channel.id
            )

            # Log ticket closure
            await TicketLogger.log_ticket_action(
                interaction.guild,
                "closed",
                interaction.channel.id,
                f"Ticket closed by {interaction.user}"
            )

            # Send closure message
            embed = discord.Embed(
                title="Ticket Closed",
                description=f"Ticket closed by {interaction.user.mention}",
                color=discord.Color.red(),
                timestamp=datetime.utcnow()
            )
            embed.set_footer(text="Developed By Lickzy")
            await interaction.message.edit(embed=embed, view=TicketCloseView())

            # Archive channel
            await interaction.channel.edit(
                name=f"closed-{interaction.channel.name}",
                category=discord.utils.get(interaction.guild.categories, name="Closed Tickets")
            )

        except Exception as e:
            logger.error(f"Error closing ticket: {e}")
            await interaction.followup.send("An error occurred while closing the ticket!")

    @discord.ui.button(
        label="Claim",
        style=discord.ButtonStyle.blurple,
        emoji="✋",
        custom_id="claim_ticket"
    )
    async def claim_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        
        try:
            # Check if user is staff
            if not interaction.user.guild_permissions.manage_channels:
                await interaction.followup.send(
                    "You don't have permission to claim tickets!",
                    ephemeral=True
                )
                return

            # Update ticket in database
            await TicketManager.update_ticket(
                interaction.guild_id,
                interaction.channel.id,
                {'claimed_by': interaction.user.id}
            )

            # Update channel permissions
            await interaction.channel.set_permissions(
                interaction.user,
                read_messages=True,
                send_messages=True
            )

            # Send claim message
            embed = discord.Embed(
                title="Ticket Claimed",
                description=f"Ticket claimed by {interaction.user.mention}",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            embed.set_footer(text="Developed By Lickzy")
            await interaction.channel.send(embed=embed)

            # Log ticket claim
            await TicketLogger.log_ticket_action(
                interaction.guild,
                "claimed",
                interaction.channel.id,
                f"Ticket claimed by {interaction.user}"
            )

        except Exception as e:
            logger.error(f"Error claiming ticket: {e}")
            await interaction.followup.send("An error occurred while claiming the ticket!")

class TicketCloseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Delete",
        style=discord.ButtonStyle.red,
        emoji="🗑️",
        custom_id="delete_ticket"
    )
    async def delete_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        
        try:
            # Check if user has permission
            if not interaction.user.guild_permissions.manage_channels:
                await interaction.followup.send(
                    "You don't have permission to delete tickets!",
                    ephemeral=True
                )
                return

            # Log ticket deletion
            await TicketLogger.log_ticket_action(
                interaction.guild,
                "deleted",
                interaction.channel.id,
                f"Ticket deleted by {interaction.user}"
            )

            # Delete channel
            await interaction.channel.delete()

        except Exception as e:
            logger.error(f"Error deleting ticket: {e}")
            await interaction.followup.send("An error occurred while deleting the ticket!")

class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        with open('config.json', 'r') as f:
            self.config = json.load(f)

    @commands.group(invoke_without_command=True)
    @commands.has_permissions(manage_channels=True)
    async def ticket(self, ctx):
        """Ticket system commands"""
        await ctx.send("Available commands: setup, panel, add, remove")

    @ticket.command(name="setup")
    @commands.has_permissions(administrator=True)
    async def ticket_setup(self, ctx):
        """Setup the ticket system"""
        try:
            # Create categories
            categories = ["Tickets", "Closed Tickets"]
            for category_name in categories:
                category = discord.utils.get(ctx.guild.categories, name=category_name)
                if not category:
                    await ctx.guild.create_category(category_name)

            await ctx.send("Ticket system setup complete!")

        except Exception as e:
            logger.error(f"Error setting up ticket system: {e}")
            await ctx.send("An error occurred while setting up the ticket system!")

    @ticket.command(name="panel")
    @commands.has_permissions(manage_channels=True)
    async def ticket_panel(self, ctx):
        """Create a ticket panel"""
        try:
            embed = discord.Embed(
                title="🎫 Create a Ticket",
                description=(
                    "Click the button below to create a support ticket.\n"
                    "Please do not create multiple tickets for the same issue."
                ),
                color=discord.Color.blue()
            )
            embed.set_footer(text="Developed By Lickzy")

            view = TicketView()
            await ctx.send(embed=embed, view=view)

        except Exception as e:
            logger.error(f"Error creating ticket panel: {e}")
            await ctx.send("An error occurred while creating the ticket panel!")

    @ticket.command(name="add")
    @commands.has_permissions(manage_channels=True)
    async def ticket_add(self, ctx, user: discord.Member):
        """Add a user to the current ticket"""
        if not ctx.channel.name.startswith(("ticket-", "closed-")):
            await ctx.send("This command can only be used in ticket channels!")
            return

        try:
            await ctx.channel.set_permissions(user, read_messages=True, send_messages=True)
            
            embed = discord.Embed(
                title="User Added",
                description=f"{user.mention} has been added to the ticket",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            embed.set_footer(text="Developed By Lickzy")
            await ctx.send(embed=embed)

            # Log user addition
            await TicketLogger.log_ticket_action(
                ctx.guild,
                "user_added",
                ctx.channel.id,
                f"{user} was added to the ticket by {ctx.author}"
            )

        except Exception as e:
            logger.error(f"Error adding user to ticket: {e}")
            await ctx.send("An error occurred while adding the user!")

    @ticket.command(name="remove")
    @commands.has_permissions(manage_channels=True)
    async def ticket_remove(self, ctx, user: discord.Member):
        """Remove a user from the current ticket"""
        if not ctx.channel.name.startswith(("ticket-", "closed-")):
            await ctx.send("This command can only be used in ticket channels!")
            return

        try:
            await ctx.channel.set_permissions(user, overwrite=None)
            
            embed = discord.Embed(
                title="User Removed",
                description=f"{user.mention} has been removed from the ticket",
                color=discord.Color.red(),
                timestamp=datetime.utcnow()
            )
            embed.set_footer(text="Developed By Lickzy")
            await ctx.send(embed=embed)

            # Log user removal
            await TicketLogger.log_ticket_action(
                ctx.guild,
                "user_removed",
                ctx.channel.id,
                f"{user} was removed from the ticket by {ctx.author}"
            )

        except Exception as e:
            logger.error(f"Error removing user from ticket: {e}")
            await ctx.send("An error occurred while removing the user!")

async def setup(bot):
    await bot.add_cog(Tickets(bot))
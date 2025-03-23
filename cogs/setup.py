import discord
from discord.ext import commands
import json
import logging
from typing import Optional

logger = logging.getLogger('discord_bot')

class Setup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        with open('config.json', 'r') as f:
            self.config = json.load(f)

    def cog_check(self, ctx):
        """Check if user is bot owner"""
        return ctx.author.id in self.config.get('owner_ids', [])

    @commands.group(invoke_without_command=True)
    async def setup(self, ctx):
        """Setup command group"""
        if ctx.invoked_subcommand is None:
            await ctx.send("Please use `setup init` to initialize the bot setup.")

    @setup.command(name="init")
    async def setup_init(self, ctx):
        """Initialize bot setup"""
        try:
            # Create Mystics Logs category
            category = await ctx.guild.create_category(
                "Mystics Logs",
                position=0,
                reason="Bot setup initialization"
            )

            # Set category permissions
            await category.set_permissions(
                ctx.guild.default_role,
                read_messages=False,
                send_messages=False
            )
            await category.set_permissions(
                ctx.guild.me,
                read_messages=True,
                send_messages=True,
                manage_channels=True
            )

            # Create log channels
            log_channels = [
                "giveaway-logs",
                "ticket-logs",
                "security-logs",
                "mod-logs",
                "owner-logs"
            ]

            created_channels = {}
            for channel_name in log_channels:
                channel = await ctx.guild.create_text_channel(
                    channel_name,
                    category=category,
                    topic=f"Logs for {channel_name.replace('-', ' ').title()}",
                    reason="Bot setup initialization"
                )
                created_channels[channel_name] = channel.id
                logger.info(f"Created {channel_name} channel: {channel.id}")

            # Update config with new channel IDs
            self.config['log_channels'] = created_channels
            with open('config.json', 'w') as f:
                json.dump(self.config, f, indent=4)

            # Create success embed
            embed = discord.Embed(
                title="✅ Setup Complete",
                description="Successfully created all required channels and updated configuration.",
                color=discord.Color.green()
            )
            
            for channel_name, channel_id in created_channels.items():
                embed.add_field(
                    name=channel_name.replace('-', ' ').title(),
                    value=f"<#{channel_id}>",
                    inline=True
                )

            embed.set_footer(text="Developed By Lickzy")
            await ctx.send(embed=embed)

            # Log to owner-logs
            owner_logs = ctx.guild.get_channel(created_channels['owner-logs'])
            if owner_logs:
                log_embed = discord.Embed(
                    title="🔧 Bot Setup Initialized",
                    description=f"Setup completed by {ctx.author.mention}",
                    color=discord.Color.blue(),
                    timestamp=ctx.message.created_at
                )
                log_embed.set_footer(text="Developed By Lickzy")
                await owner_logs.send(embed=log_embed)
                logger.info(f"Setup completed by {ctx.author}")

        except discord.Forbidden:
            logger.error("Missing permissions to create channels")
            await ctx.send("❌ I don't have permission to create channels!")
        except Exception as e:
            logger.error(f"Error in setup: {e}")
            await ctx.send(f"❌ An error occurred: {str(e)}")

    @setup.command(name="status")
    async def setup_status(self, ctx):
        """Check setup status"""
        embed = discord.Embed(
            title="🔍 Setup Status",
            color=discord.Color.blue()
        )

        # Check category
        category = discord.utils.get(ctx.guild.categories, name="Mystics Logs")
        embed.add_field(
            name="Mystics Logs Category",
            value="✅ Found" if category else "❌ Missing",
            inline=False
        )

        # Check log channels
        if category:
            for channel_name in ["giveaway-logs", "ticket-logs", "security-logs", "mod-logs", "owner-logs"]:
                channel = discord.utils.get(category.text_channels, name=channel_name)
                embed.add_field(
                    name=channel_name.replace('-', ' ').title(),
                    value="✅ Found" if channel else "❌ Missing",
                    inline=True
                )

        embed.set_footer(text="Developed By Lickzy")
        await ctx.send(embed=embed)

    @setup.command(name="repair")
    async def setup_repair(self, ctx):
        """Repair missing channels"""
        category = discord.utils.get(ctx.guild.categories, name="Mystics Logs")
        if not category:
            await ctx.send("❌ Mystics Logs category not found. Please run `setup init` first.")
            return

        missing_channels = []
        for channel_name in ["giveaway-logs", "ticket-logs", "security-logs", "mod-logs", "owner-logs"]:
            if not discord.utils.get(category.text_channels, name=channel_name):
                missing_channels.append(channel_name)

        if not missing_channels:
            await ctx.send("✅ All channels are present. No repair needed.")
            return

        try:
            for channel_name in missing_channels:
                channel = await ctx.guild.create_text_channel(
                    channel_name,
                    category=category,
                    topic=f"Logs for {channel_name.replace('-', ' ').title()}",
                    reason="Bot setup repair"
                )
                logger.info(f"Repaired {channel_name} channel: {channel.id}")

            embed = discord.Embed(
                title="🔧 Setup Repair Complete",
                description=f"Repaired {len(missing_channels)} missing channels",
                color=discord.Color.green()
            )
            embed.add_field(
                name="Repaired Channels",
                value="\n".join(f"✅ {channel}" for channel in missing_channels),
                inline=False
            )
            embed.set_footer(text="Developed By Lickzy")
            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Error in setup repair: {e}")
            await ctx.send(f"❌ An error occurred: {str(e)}")

async def setup(bot):
    await bot.add_cog(Setup(bot))
import logging
import os
from datetime import datetime
import discord
from typing import Optional, Union

class Logger:
    _instance = None
    _logger = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Logger, cls).__new__(cls)
            cls._setup_logger()
        return cls._instance

    @classmethod
    def _setup_logger(cls):
        """Setup the logger with both file and console handlers"""
        # Create logs directory if it doesn't exist
        if not os.path.exists('logs'):
            os.makedirs('logs')

        # Create logger
        cls._logger = logging.getLogger('discord_bot')
        cls._logger.setLevel(logging.INFO)

        # Create formatters
        console_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # Create console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(console_formatter)

        # Create file handler
        file_handler = logging.FileHandler(
            filename=f'logs/discord_{datetime.now().strftime("%Y%m%d")}.log',
            encoding='utf-8',
            mode='a'
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(file_formatter)

        # Add handlers
        cls._logger.addHandler(console_handler)
        cls._logger.addHandler(file_handler)

    @classmethod
    def get_logger(cls):
        """Get the logger instance"""
        if cls._logger is None:
            cls._setup_logger()
        return cls._logger

class ModLogger:
    @staticmethod
    async def log_mod_action(ctx, action: str, target: Union[discord.Member, discord.User, discord.TextChannel], reason: Optional[str] = None):
        """Log moderation actions to both console and mod-logs channel"""
        logger = Logger.get_logger()
        
        # Create log message
        log_message = f"{ctx.author} ({ctx.author.id}) {action} "
        if isinstance(target, (discord.Member, discord.User)):
            log_message += f"{target} ({target.id})"
        else:
            log_message += f"#{target.name}"
        if reason:
            log_message += f" | Reason: {reason}"

        # Log to console/file
        logger.info(log_message)

        # Log to mod-logs channel
        try:
            # Get mod-logs channel from config
            mod_logs = discord.utils.get(ctx.guild.text_channels, name="mod-logs")
            if mod_logs:
                embed = discord.Embed(
                    title=f"Moderation Action: {action.title()}",
                    description=log_message,
                    color=ModLogger._get_action_color(action),
                    timestamp=datetime.utcnow()
                )
                
                # Add target info
                if isinstance(target, (discord.Member, discord.User)):
                    embed.add_field(
                        name="Target User",
                        value=f"{target.mention}\n{target.id}",
                        inline=True
                    )
                else:
                    embed.add_field(
                        name="Target Channel",
                        value=f"{target.mention}\n{target.id}",
                        inline=True
                    )

                # Add moderator info
                embed.add_field(
                    name="Moderator",
                    value=f"{ctx.author.mention}\n{ctx.author.id}",
                    inline=True
                )

                # Add reason if provided
                if reason:
                    embed.add_field(
                        name="Reason",
                        value=reason,
                        inline=False
                    )

                embed.set_footer(text="Developed By Lickzy")
                await mod_logs.send(embed=embed)

        except Exception as e:
            logger.error(f"Failed to log to mod-logs channel: {e}")

    @staticmethod
    def _get_action_color(action: str) -> int:
        """Get color for different moderation actions"""
        colors = {
            'ban': discord.Color.red(),
            'unban': discord.Color.green(),
            'kick': discord.Color.orange(),
            'warn': discord.Color.gold(),
            'mute': discord.Color.dark_grey(),
            'unmute': discord.Color.light_grey(),
            'lock': discord.Color.dark_red(),
            'unlock': discord.Color.dark_green(),
            'purge': discord.Color.blue()
        }
        return colors.get(action.lower(), discord.Color.blurple())

class SecurityLogger:
    @staticmethod
    async def log_security_event(ctx, event_type: str, details: str):
        """Log security events to both console and security-logs channel"""
        logger = Logger.get_logger()
        
        # Create log message
        log_message = f"Security Event: {event_type} | {details}"
        
        # Log to console/file
        logger.info(log_message)

        # Log to security-logs channel
        try:
            security_logs = discord.utils.get(ctx.guild.text_channels, name="security-logs")
            if security_logs:
                embed = discord.Embed(
                    title=f"Security Event: {event_type}",
                    description=details,
                    color=discord.Color.red(),
                    timestamp=datetime.utcnow()
                )
                embed.set_footer(text="Developed By Lickzy")
                await security_logs.send(embed=embed)

        except Exception as e:
            logger.error(f"Failed to log to security-logs channel: {e}")

class GiveawayLogger:
    @staticmethod
    async def log_giveaway_action(ctx, action: str, details: str):
        """Log giveaway actions to both console and giveaway-logs channel"""
        logger = Logger.get_logger()
        
        # Create log message
        log_message = f"Giveaway {action}: {details}"
        
        # Log to console/file
        logger.info(log_message)

        # Log to giveaway-logs channel
        try:
            giveaway_logs = discord.utils.get(ctx.guild.text_channels, name="giveaway-logs")
            if giveaway_logs:
                embed = discord.Embed(
                    title=f"Giveaway {action}",
                    description=details,
                    color=discord.Color.gold(),
                    timestamp=datetime.utcnow()
                )
                embed.set_footer(text="Developed By Lickzy")
                await giveaway_logs.send(embed=embed)

        except Exception as e:
            logger.error(f"Failed to log to giveaway-logs channel: {e}")

class TicketLogger:
    @staticmethod
    async def log_ticket_action(ctx, action: str, ticket_id: int, details: str):
        """Log ticket actions to both console and ticket-logs channel"""
        logger = Logger.get_logger()
        
        # Create log message
        log_message = f"Ticket {action} (ID: {ticket_id}): {details}"
        
        # Log to console/file
        logger.info(log_message)

        # Log to ticket-logs channel
        try:
            ticket_logs = discord.utils.get(ctx.guild.text_channels, name="ticket-logs")
            if ticket_logs:
                embed = discord.Embed(
                    title=f"Ticket {action}",
                    description=f"Ticket ID: {ticket_id}\n{details}",
                    color=discord.Color.blue(),
                    timestamp=datetime.utcnow()
                )
                embed.set_footer(text="Developed By Lickzy")
                await ticket_logs.send(embed=embed)

        except Exception as e:
            logger.error(f"Failed to log to ticket-logs channel: {e}")
import discord
from discord.ext import commands
from typing import Dict, List, Optional

class HelpDropdown(discord.ui.Select):
    def __init__(self, help_data: Dict[str, List[str]], bot):
        self.help_data = help_data
        self.bot = bot
        
        options = [
            discord.SelectOption(
                label=category.title(),
                description=f"View {category.lower()} commands",
                emoji=self._get_category_emoji(category)
            ) for category in help_data.keys()
        ]
        
        super().__init__(
            placeholder="Select a category...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="help_dropdown"
        )

    def _get_category_emoji(self, category: str) -> str:
        """Get emoji for category"""
        emojis = {
            'moderation': '🛡️',
            'utility': '🔧',
            'setup': '⚙️',
            'tickets': '🎫',
            'giveaways': '🎉',
            'security': '🔒',
            'premium': '💎',
            'badges': '🏆'
        }
        return emojis.get(category.lower(), '❓')

    async def callback(self, interaction: discord.Interaction):
        """Handle dropdown selection"""
        selected = self.values[0].lower()
        commands_list = self.help_data.get(selected, [])
        
        embed = discord.Embed(
            title=f"{self._get_category_emoji(selected)} {selected.title()} Commands",
            color=discord.Color.blue(),
            timestamp=interaction.created_at
        )
        
        for cmd_name in commands_list:
            cmd = self.bot.get_command(cmd_name)
            if cmd and not cmd.hidden:
                signature = f"{cmd.name} {cmd.signature}" if cmd.signature else cmd.name
                description = cmd.help or "No description available."
                embed.add_field(
                    name=f"`{self.bot.command_prefix}{signature}`",
                    value=description,
                    inline=False
                )
        
        embed.set_footer(text="Developed By Lickzy")
        await interaction.response.edit_message(embed=embed, view=self.view)

class HelpView(discord.ui.View):
    def __init__(self, help_data: Dict[str, List[str]], bot):
        super().__init__(timeout=180)  # 3 minute timeout
        self.add_item(HelpDropdown(help_data, bot))

    async def on_timeout(self):
        """Disable the dropdown when the view times out"""
        for item in self.children:
            item.disabled = True

class HelpMenu(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.help_data = {}

    def _generate_help_data(self) -> Dict[str, List[str]]:
        """Generate help data from bot commands"""
        help_data = {
            'Moderation': [],
            'Utility': [],
            'Setup': [],
            'Tickets': [],
            'Giveaways': [],
            'Security': [],
            'Premium': [],
            'Badges': []
        }
        
        for command in self.bot.commands:
            if command.hidden:
                continue
                
            # Get cog name or 'Utility' as default
            category = command.cog.qualified_name if command.cog else 'Utility'
            
            # Add command to appropriate category
            if category in help_data:
                help_data[category].append(command.name)
            else:
                help_data['Utility'].append(command.name)
        
        # Remove empty categories
        return {k: v for k, v in help_data.items() if v}

    @commands.command(name='helpme')
    async def show_help(self, ctx, command_name: Optional[str] = None):
        """Show help menu with dropdown or command info"""
        if command_name:
            # Show specific command help
            command = self.bot.get_command(command_name)
            if not command or command.hidden:
                await ctx.send(f"Command `{command_name}` not found!")
                return
                
            embed = discord.Embed(
                title=f"Command: {command.name}",
                description=command.help or "No description available.",
                color=discord.Color.blue()
            )
            
            if command.aliases:
                embed.add_field(
                    name="Aliases",
                    value=", ".join(f"`{alias}`" for alias in command.aliases),
                    inline=False
                )
                
            usage = f"{ctx.prefix}{command.name}"
            if command.signature:
                usage += f" {command.signature}"
            embed.add_field(name="Usage", value=f"`{usage}`", inline=False)
            
            if isinstance(command, commands.Group):
                subcommands = []
                for subcmd in command.commands:
                    signature = f"{subcmd.name} {subcmd.signature}" if subcmd.signature else subcmd.name
                    subcommands.append(f"`{signature}`: {subcmd.help or 'No description'}")
                
                if subcommands:
                    embed.add_field(
                        name="Subcommands",
                        value="\n".join(subcommands),
                        inline=False
                    )
            
            embed.set_footer(text="Developed By Lickzy")
            await ctx.send(embed=embed)
            return
            
        # Show category selection menu
        self.help_data = self._generate_help_data()
        
        embed = discord.Embed(
            title="🔍 Help Menu",
            description="Select a category below to view available commands",
            color=discord.Color.blue()
        )
        
        # Add statistics
        total_commands = sum(len(cmds) for cmds in self.help_data.values())
        total_categories = len(self.help_data)
        
        embed.add_field(
            name="📊 Statistics",
            value=f"Categories: {total_categories}\nCommands: {total_commands}",
            inline=False
        )
        
        embed.set_footer(text="Developed By Lickzy")
        view = HelpView(self.help_data, self.bot)
        await ctx.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(HelpMenu(bot))
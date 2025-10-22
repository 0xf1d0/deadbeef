import os
from discord.ext import commands
from discord import app_commands, Interaction, Embed, Color
from sqlalchemy import select

from db import AsyncSessionLocal, init_db
from db.models import Category
from ui.cybertools import (
    ToolExplorerView,
    SearchModal,
    ToolSuggestionModal
)
from utils import ROLE_MANAGER, ROLE_NOTABLE


class CyberTools(commands.Cog):
    """Cog for managing cybersecurity tools."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.admin_channel_id = int(os.getenv("ADMIN_CHANNEL_ID", "0"))
    
    async def cog_load(self):
        """Initialize database when cog loads."""
        await init_db()
    
    @app_commands.command(name="tools", description="Browse cybersecurity tools by category.")
    async def tools(self, interaction: Interaction):
        """Browse tools by category."""
        async with AsyncSessionLocal() as session:
            # Fetch all categories
            result = await session.execute(select(Category))
            categories = result.scalars().all()
            
            if not categories:
                embed = Embed(
                    title="🔧 Cybersecurity Tool Explorer",
                    description="No categories available yet. Please contact an administrator.",
                    color=Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            # Create embed
            embed = Embed(
                title="🔧 Cybersecurity Tool Explorer",
                description="Select a category to explore tools:",
                color=Color.blue()
            )
            
            # Add categories info
            category_list = "\n".join([f"• **{cat.name}** - {len(cat.tools)} tool(s)" for cat in categories])
            embed.add_field(name="Available Categories", value=category_list, inline=False)
            
            # Create view with category selector
            view = ToolExplorerView(session, categories)
            
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @app_commands.command(name="search", description="Search for a cybersecurity tool.")
    async def search(self, interaction: Interaction):
        """Search for tools by name."""
        async with AsyncSessionLocal() as session:
            modal = SearchModal(session)
            await interaction.response.send_modal(modal)
    
    @app_commands.command(name="suggest_tool", description="Suggest a new cybersecurity tool.")
    async def suggest_tool(self, interaction: Interaction):
        """Submit a tool suggestion."""
        async with AsyncSessionLocal() as session:
            modal = ToolSuggestionModal(session, self.admin_channel_id)
            await interaction.response.send_modal(modal)
    
    @app_commands.command(
        name="manage_tools",
        description="Tool management dashboard (Admin only)."
    )
    @app_commands.checks.has_any_role(ROLE_MANAGER.id, ROLE_NOTABLE.id)
    async def manage_tools(self, interaction: Interaction):
        """Open tool management dashboard."""
        from ui.cybertools import CyberToolsAdminPanel
        
        view = CyberToolsAdminPanel(self.bot)
        embed = Embed(
            title="🔐 Tool Management Dashboard",
            description="Select an action from the menu below to manage cybersecurity tools and categories.",
            color=Color.gold()
        )
        embed.add_field(
            name="Available Actions",
            value="• Manage tools and categories\n"
                  "• Review pending suggestions\n"
                  "• View statistics",
            inline=False
        )
        embed.set_footer(text="Use the select menu below to get started")
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(CyberTools(bot))


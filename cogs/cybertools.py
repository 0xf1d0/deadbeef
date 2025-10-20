import os
from discord.ext import commands
from discord import app_commands, Interaction, Embed, Color
from sqlalchemy import select

from db import AsyncSessionLocal, init_db
from db.models import Category, Tool, ToolSuggestion
from ui.cybertools import (
    ToolExplorerView,
    SearchModal,
    ToolSuggestionModal,
    AdminPanelView
)


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
            
            await interaction.response.send_message(embed=embed, view=view)
    
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
    
    @app_commands.command(name="admin", description="Admin panel for managing tools and categories.")
    @app_commands.describe(action="Admin action to perform")
    @app_commands.choices(action=[
        app_commands.Choice(name="tools", value="tools"),
        app_commands.Choice(name="suggestions", value="suggestions"),
        app_commands.Choice(name="stats", value="stats")
    ])
    @app_commands.checks.has_permissions(administrator=True)
    async def admin(self, interaction: Interaction, action: str):
        """Admin management panel."""
        if action == "tools":
            view = AdminPanelView()
            embed = Embed(
                title="🔐 Admin Tool Management",
                description="Choose an action to manage tools and categories:",
                color=Color.gold()
            )
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        
        elif action == "suggestions":
            async with AsyncSessionLocal() as session:
                # Fetch pending suggestions
                result = await session.execute(
                    select(ToolSuggestion).where(ToolSuggestion.status == 'pending')
                )
                suggestions = result.scalars().all()
                
                if not suggestions:
                    embed = Embed(
                        title="📋 Tool Suggestions",
                        description="No pending suggestions.",
                        color=Color.green()
                    )
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return
                
                embed = Embed(
                    title="📋 Tool Suggestions",
                    description=f"There are **{len(suggestions)}** pending suggestion(s).",
                    color=Color.orange()
                )
                
                for suggestion in suggestions[:25]:  # Limit to 25
                    user = await self.bot.fetch_user(suggestion.suggester_id)
                    embed.add_field(
                        name=f"ID: {suggestion.id} - {suggestion.tool_name}",
                        value=f"Category: {suggestion.category_suggestion}\n"
                              f"By: {user.mention if user else 'Unknown'}\n"
                              f"[URL]({suggestion.tool_url})",
                        inline=False
                    )
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
        
        elif action == "stats":
            async with AsyncSessionLocal() as session:
                # Get statistics
                categories_result = await session.execute(select(Category))
                categories = categories_result.scalars().all()
                
                tools_result = await session.execute(select(Tool))
                tools = tools_result.scalars().all()
                
                suggestions_result = await session.execute(select(ToolSuggestion))
                suggestions = suggestions_result.scalars().all()
                
                pending_suggestions = len([s for s in suggestions if s.status == 'pending'])
                approved_suggestions = len([s for s in suggestions if s.status == 'approved'])
                denied_suggestions = len([s for s in suggestions if s.status == 'denied'])
                
                embed = Embed(
                    title="📊 Cybersecurity Tools Statistics",
                    description="Overview of the tool database:",
                    color=Color.blue()
                )
                embed.add_field(name="📁 Categories", value=str(len(categories)), inline=True)
                embed.add_field(name="🔧 Tools", value=str(len(tools)), inline=True)
                embed.add_field(name="📝 Total Suggestions", value=str(len(suggestions)), inline=True)
                embed.add_field(name="⏳ Pending", value=str(pending_suggestions), inline=True)
                embed.add_field(name="✅ Approved", value=str(approved_suggestions), inline=True)
                embed.add_field(name="❌ Denied", value=str(denied_suggestions), inline=True)
                
                # Category breakdown
                if categories:
                    category_info = []
                    for cat in categories:
                        tool_count = len(cat.tools)
                        category_info.append(f"• **{cat.name}**: {tool_count} tool(s)")
                    
                    embed.add_field(
                        name="Category Breakdown",
                        value="\n".join(category_info) or "No categories",
                        inline=False
                    )
                
                await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(CyberTools(bot))


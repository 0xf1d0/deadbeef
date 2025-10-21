import discord
from discord import ui, ButtonStyle, TextStyle, Interaction, Embed, SelectOption
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Category, Tool, ToolSuggestion


class CategorySelect(ui.Select):
    """Select menu for choosing a category."""
    
    def __init__(self, categories: List[Category], session: AsyncSession):
        self.db_session = session
        options = [
            SelectOption(
                label=category.name,
                value=str(category.id),
                description=category.description[:100] if category.description else "No description"
            )
            for category in categories
        ]
        super().__init__(
            placeholder="Select a category to view tools...",
            min_values=1,
            max_values=1,
            options=options
        )
    
    async def callback(self, interaction: Interaction):
        category_id = int(self.values[0])
        
        # Fetch category and its tools
        result = await self.db_session.execute(
            select(Category).where(Category.id == category_id)
        )
        category = result.scalar_one_or_none()
        
        if not category:
            await interaction.response.send_message("Category not found.", ephemeral=True)
            return
        
        # Fetch tools for this category
        result = await self.db_session.execute(
            select(Tool).where(Tool.category_id == category_id)
        )
        tools = result.scalars().all()
        
        # Create embed
        embed = Embed(
            title=f"🔧 {category.name}",
            description=category.description or "No description available.",
            color=discord.Color.blue()
        )
        
        if not tools:
            embed.add_field(name="No Tools", value="This category has no tools yet.", inline=False)
            view = ToolExplorerView(self.db_session, [category])
            await interaction.response.edit_message(embed=embed, view=view)
            return
        
        # Create new view with tool buttons
        view = ToolListView(self.db_session, tools, [category])
        
        # Add tools to embed
        tool_list = "\n".join([f"• **{tool.name}**" for tool in tools])
        embed.add_field(name=f"Tools ({len(tools)})", value=tool_list, inline=False)
        
        await interaction.response.edit_message(embed=embed, view=view)


class ToolExplorerView(ui.View):
    """Main view for tool exploration."""
    
    def __init__(self, session: AsyncSession, categories: List[Category]):
        super().__init__(timeout=300)
        self.db_session = session
        self.add_item(CategorySelect(categories, session))


class ToolDetailButton(ui.Button):
    """Button to view tool details."""
    
    def __init__(self, tool: Tool, row: int = 0):
        super().__init__(
            label=f"View: {tool.name}",
            style=ButtonStyle.primary,
            row=row
        )
        self.tool = tool
    
    async def callback(self, interaction: Interaction):
        embed = Embed(
            title=f"🔧 {self.tool.name}",
            description=self.tool.description,
            color=discord.Color.green()
        )
        embed.add_field(name="Category", value=self.tool.category.name, inline=True)
        
        # Create view with URL button
        view = ui.View()
        view.add_item(
            ui.Button(
                label="Visit Website",
                style=ButtonStyle.link,
                url=self.tool.url
            )
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class ToolListView(ui.View):
    """View showing a list of tools with detail buttons."""
    
    def __init__(self, session: AsyncSession, tools: List[Tool], categories: List[Category]):
        super().__init__(timeout=300)
        self.db_session = session
        
        # Add category selector at the top
        self.add_item(CategorySelect(categories, session))
        
        # Add tool detail buttons (max 20 tools, 4 per row)
        for idx, tool in enumerate(tools[:20]):
            row = (idx // 4) + 1  # Start from row 1 (row 0 is for category select)
            if row <= 4:  # Discord allows max 5 rows, we use first for select
                self.add_item(ToolDetailButton(tool, row=row))


class SearchModal(ui.Modal, title="Search for a Tool"):
    """Modal for searching tools."""
    
    query = ui.TextInput(
        label="Tool Name",
        placeholder="Enter tool name...",
        required=True,
        max_length=100
    )
    
    def __init__(self, session: AsyncSession):
        super().__init__()
        self.db_session = session
    
    async def on_submit(self, interaction: Interaction):
        search_term = f"%{self.query.value}%"
        
        # Search for tools
        result = await self.db_session.execute(
            select(Tool).where(Tool.name.ilike(search_term))
        )
        tools = result.scalars().all()
        
        if not tools:
            await interaction.response.send_message(
                f"No tools found matching '{self.query.value}'.",
                ephemeral=True
            )
            return
        
        # Create embed with results
        embed = Embed(
            title=f"🔍 Search Results for '{self.query.value}'",
            description=f"Found {len(tools)} tool(s)",
            color=discord.Color.gold()
        )
        
        # Create view with tool buttons
        view = ui.View(timeout=300)
        for idx, tool in enumerate(tools[:25]):  # Max 25 buttons
            row = idx // 5
            if row < 5:
                view.add_item(ToolDetailButton(tool, row=row))
        
        # Add tool names to embed
        tool_list = "\n".join([f"• **{tool.name}** ({tool.category.name})" for tool in tools[:25]])
        embed.add_field(name="Tools", value=tool_list, inline=False)
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class ToolSuggestionModal(ui.Modal, title="Suggest a New Tool"):
    """Modal for submitting tool suggestions."""
    
    tool_name = ui.TextInput(
        label="Tool Name",
        placeholder="e.g., Nmap",
        required=True,
        max_length=100
    )
    
    tool_url = ui.TextInput(
        label="Tool URL",
        placeholder="https://...",
        required=True,
        max_length=200
    )
    
    category_suggestion = ui.TextInput(
        label="Category Suggestion",
        placeholder="e.g., Network Scanners",
        required=True,
        max_length=100
    )
    
    tool_description = ui.TextInput(
        label="Tool Description",
        placeholder="Describe the tool and its purpose...",
        style=TextStyle.paragraph,
        required=True,
        max_length=1000
    )
    
    def __init__(self, session: AsyncSession, admin_channel_id: Optional[int] = None):
        super().__init__()
        self.db_session = session
        self.admin_channel_id = admin_channel_id
    
    async def on_submit(self, interaction: Interaction):
        # Create suggestion
        suggestion = ToolSuggestion(
            tool_name=self.tool_name.value,
            tool_description=self.tool_description.value,
            tool_url=self.tool_url.value,
            category_suggestion=self.category_suggestion.value,
            suggester_id=interaction.user.id,
            status='pending'
        )
        
        self.db_session.add(suggestion)
        await self.db_session.commit()
        await self.db_session.refresh(suggestion)
        
        # Send confirmation to user
        await interaction.response.send_message(
            "✅ Thank you! Your tool suggestion has been submitted for review.",
            ephemeral=True
        )
        
        # Send notification to admin channel
        if self.admin_channel_id:
            admin_channel = interaction.guild.get_channel(self.admin_channel_id)
            if admin_channel:
                embed = Embed(
                    title="🆕 New Tool Suggestion",
                    description=f"Submitted by {interaction.user.mention}",
                    color=discord.Color.orange()
                )
                embed.add_field(name="Tool Name", value=suggestion.tool_name, inline=False)
                embed.add_field(name="URL", value=suggestion.tool_url, inline=False)
                embed.add_field(name="Category", value=suggestion.category_suggestion, inline=False)
                embed.add_field(name="Description", value=suggestion.tool_description[:1024], inline=False)
                embed.set_footer(text=f"Suggestion ID: {suggestion.id}")
                
                view = SuggestionReviewView(suggestion.id)
                await admin_channel.send(embed=embed, view=view)


class SuggestionReviewView(ui.View):
    """View for reviewing tool suggestions."""
    
    def __init__(self, suggestion_id: int):
        super().__init__(timeout=None)  # Persistent view
        self.suggestion_id = suggestion_id
    
    @ui.button(label="Approve", style=ButtonStyle.green, custom_id="approve")
    async def approve_button(self, interaction: Interaction, button: ui.Button):
        # Import here to avoid circular imports
        from db import AsyncSessionLocal
        
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(ToolSuggestion).where(ToolSuggestion.id == self.suggestion_id)
            )
            suggestion = result.scalar_one_or_none()
            
            if not suggestion:
                await interaction.response.send_message("Suggestion not found.", ephemeral=True)
                return
            
            if suggestion.status != 'pending':
                await interaction.response.send_message(
                    f"This suggestion has already been {suggestion.status}.",
                    ephemeral=True
                )
                return
            
            # Show modal for editing before approval
            modal = ApprovalEditModal(session, suggestion)
            await interaction.response.send_modal(modal)
    
    @ui.button(label="Deny", style=ButtonStyle.red, custom_id="deny")
    async def deny_button(self, interaction: Interaction, button: ui.Button):
        # Import here to avoid circular imports
        from db import AsyncSessionLocal
        
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(ToolSuggestion).where(ToolSuggestion.id == self.suggestion_id)
            )
            suggestion = result.scalar_one_or_none()
            
            if not suggestion:
                await interaction.response.send_message("Suggestion not found.", ephemeral=True)
                return
            
            if suggestion.status != 'pending':
                await interaction.response.send_message(
                    f"This suggestion has already been {suggestion.status}.",
                    ephemeral=True
                )
                return
            
            # Update status
            suggestion.status = 'denied'
            await session.commit()
            
            # Update the message
            embed = interaction.message.embeds[0]
            embed.color = discord.Color.red()
            embed.title = "❌ Tool Suggestion Denied"
            embed.set_footer(text=f"Denied by {interaction.user.name}")
            
            await interaction.response.edit_message(embed=embed, view=None)
            
            # Try to DM the suggester
            try:
                suggester = await interaction.client.fetch_user(suggestion.suggester_id)
                await suggester.send(
                    f"Your tool suggestion **{suggestion.tool_name}** has been denied."
                )
            except:
                pass  # User might have DMs disabled


class ApprovalEditModal(ui.Modal, title="Edit & Approve Tool"):
    """Modal for editing tool details before approval."""
    
    tool_name = ui.TextInput(label="Tool Name", required=True, max_length=100)
    tool_url = ui.TextInput(label="Tool URL", required=True, max_length=200)
    category_name = ui.TextInput(label="Category Name", required=True, max_length=100)
    tool_description = ui.TextInput(
        label="Tool Description",
        style=TextStyle.paragraph,
        required=True,
        max_length=1000
    )
    
    def __init__(self, session: AsyncSession, suggestion: ToolSuggestion):
        super().__init__()
        self.db_session = session
        self.suggestion = suggestion
        
        # Pre-fill with suggestion data
        self.tool_name.default = suggestion.tool_name
        self.tool_url.default = suggestion.tool_url
        self.category_name.default = suggestion.category_suggestion
        self.tool_description.default = suggestion.tool_description
    
    async def on_submit(self, interaction: Interaction):
        # Find or create category
        result = await self.db_session.execute(
            select(Category).where(Category.name == self.category_name.value)
        )
        category = result.scalar_one_or_none()
        
        if not category:
            category = Category(name=self.category_name.value)
            self.db_session.add(category)
            await self.db_session.commit()
            await self.db_session.refresh(category)
        
        # Check if tool name already exists
        result = await self.db_session.execute(
            select(Tool).where(Tool.name == self.tool_name.value)
        )
        existing_tool = result.scalar_one_or_none()
        
        if existing_tool:
            await interaction.response.send_message(
                f"A tool named '{self.tool_name.value}' already exists.",
                ephemeral=True
            )
            return
        
        # Create tool
        tool = Tool(
            name=self.tool_name.value,
            description=self.tool_description.value,
            url=self.tool_url.value,
            category_id=category.id
        )
        self.db_session.add(tool)
        
        # Update suggestion status
        self.suggestion.status = 'approved'
        await self.db_session.commit()
        
        # Update the message
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.green()
        embed.title = "✅ Tool Suggestion Approved"
        embed.set_footer(text=f"Approved by {interaction.user.name}")
        
        await interaction.response.edit_message(embed=embed, view=None)
        
        # Try to DM the suggester
        try:
            suggester = await interaction.client.fetch_user(self.suggestion.suggester_id)
            await suggester.send(
                f"Your tool suggestion **{self.suggestion.tool_name}** has been approved and added to the database!"
            )
        except:
            pass  # User might have DMs disabled


class CyberToolsAdminPanel(ui.View):
    """Admin panel with select menu for tool management."""
    
    def __init__(self, bot):
        super().__init__(timeout=300)
        self.bot = bot
        
        # Create select menu with all admin options
        options = [
            SelectOption(
                label="Manage Tools & Categories",
                description="Add, edit, or delete tools and categories",
                value="manage",
                emoji="🔧"
            ),
            SelectOption(
                label="Review Suggestions",
                description="View and approve/deny tool suggestions",
                value="suggestions",
                emoji="📋"
            ),
            SelectOption(
                label="View Statistics",
                description="Show tool database statistics",
                value="stats",
                emoji="📊"
            ),
        ]
        
        select = ui.Select(
            placeholder="Select an action...",
            options=options,
            custom_id="cybertools_admin_select"
        )
        select.callback = self.action_selected
        self.add_item(select)
    
    async def action_selected(self, interaction: Interaction):
        """Handle admin action selection."""
        from db import AsyncSessionLocal
        
        action = self.children[0].values[0]
        
        if action == "manage":
            # Show tool/category management panel
            view = AdminPanelView()
            embed = Embed(
                title="🔐 Admin Tool Management",
                description="Choose an action to manage tools and categories:",
                color=discord.Color.gold()
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
                        color=discord.Color.green()
                    )
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return
                
                embed = Embed(
                    title="📋 Tool Suggestions",
                    description=f"There are **{len(suggestions)}** pending suggestion(s).",
                    color=discord.Color.orange()
                )
                
                for suggestion in suggestions[:25]:  # Limit to 25
                    try:
                        user = await self.bot.fetch_user(suggestion.suggester_id)
                        user_mention = user.mention if user else 'Unknown'
                    except:
                        user_mention = 'Unknown'
                    
                    embed.add_field(
                        name=f"ID: {suggestion.id} - {suggestion.tool_name}",
                        value=f"Category: {suggestion.category_suggestion}\n"
                              f"By: {user_mention}\n"
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
                
                pending_suggestions = sum(1 for s in suggestions if s.status == 'pending')
                approved_suggestions = sum(1 for s in suggestions if s.status == 'approved')
                denied_suggestions = sum(1 for s in suggestions if s.status == 'denied')
                
                embed = Embed(
                    title="📊 Cybersecurity Tools Statistics",
                    description="Overview of the tool database:",
                    color=discord.Color.blue()
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


class AdminPanelView(ui.View):
    """Main admin panel view."""
    
    def __init__(self):
        super().__init__(timeout=300)
    
    @ui.button(label="Add Tool", style=ButtonStyle.green)
    async def add_tool(self, interaction: Interaction, button: ui.Button):
        from db import AsyncSessionLocal
        
        async with AsyncSessionLocal() as session:
            # Fetch all categories
            result = await session.execute(select(Category))
            categories = result.scalars().all()
            
            if not categories:
                await interaction.response.send_message(
                    "No categories available. Please create a category first.",
                    ephemeral=True
                )
                return
            
            view = AddToolCategorySelect(session, categories)
            embed = Embed(
                title="Add Tool",
                description="Select a category for the new tool:",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @ui.button(label="Edit Tool", style=ButtonStyle.blurple)
    async def edit_tool(self, interaction: Interaction, button: ui.Button):
        from db import AsyncSessionLocal
        
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Category))
            categories = result.scalars().all()
            
            if not categories:
                await interaction.response.send_message(
                    "No categories available.",
                    ephemeral=True
                )
                return
            
            view = EditToolCategorySelect(session, categories)
            embed = Embed(
                title="Edit Tool",
                description="Select a category to view its tools:",
                color=discord.Color.blurple()
            )
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @ui.button(label="Delete Tool", style=ButtonStyle.red)
    async def delete_tool(self, interaction: Interaction, button: ui.Button):
        from db import AsyncSessionLocal
        
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Category))
            categories = result.scalars().all()
            
            if not categories:
                await interaction.response.send_message(
                    "No categories available.",
                    ephemeral=True
                )
                return
            
            view = DeleteToolCategorySelect(session, categories)
            embed = Embed(
                title="Delete Tool",
                description="Select a category to view its tools:",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @ui.button(label="Manage Categories", style=ButtonStyle.grey)
    async def manage_categories(self, interaction: Interaction, button: ui.Button):
        view = CategoryManagementView()
        embed = Embed(
            title="Category Management",
            description="Choose an action:",
            color=discord.Color.greyple()
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class AddToolCategorySelect(ui.View):
    """View for selecting category when adding a tool."""
    
    def __init__(self, session: AsyncSession, categories: List[Category]):
        super().__init__(timeout=300)
        self.db_session = session
        
        options = [
            SelectOption(label=cat.name, value=str(cat.id))
            for cat in categories
        ]
        
        select = ui.Select(placeholder="Select a category...", options=options)
        select.callback = self.category_selected
        self.add_item(select)
        self.categories = {cat.id: cat for cat in categories}
    
    async def category_selected(self, interaction: Interaction):
        category_id = int(self.children[0].values[0])
        category = self.categories[category_id]
        
        modal = AddToolModal(self.db_session, category)
        await interaction.response.send_modal(modal)


class AddToolModal(ui.Modal, title="Add New Tool"):
    """Modal for adding a new tool."""
    
    tool_name = ui.TextInput(label="Tool Name", required=True, max_length=100)
    tool_url = ui.TextInput(label="Tool URL", required=True, max_length=200)
    tool_description = ui.TextInput(
        label="Tool Description",
        style=TextStyle.paragraph,
        required=True,
        max_length=1000
    )
    
    def __init__(self, session: AsyncSession, category: Category):
        super().__init__()
        self.db_session = session
        self.category = category
    
    async def on_submit(self, interaction: Interaction):
        # Check if tool already exists
        result = await self.db_session.execute(
            select(Tool).where(Tool.name == self.tool_name.value)
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            await interaction.response.send_message(
                f"A tool named '{self.tool_name.value}' already exists.",
                ephemeral=True
            )
            return
        
        # Create tool
        tool = Tool(
            name=self.tool_name.value,
            description=self.tool_description.value,
            url=self.tool_url.value,
            category_id=self.category.id
        )
        self.db_session.add(tool)
        await self.db_session.commit()
        
        await interaction.response.send_message(
            f"✅ Tool '{self.tool_name.value}' added to category '{self.category.name}'.",
            ephemeral=True
        )


class EditToolCategorySelect(ui.View):
    """View for selecting category when editing tools."""
    
    def __init__(self, session: AsyncSession, categories: List[Category]):
        super().__init__(timeout=300)
        self.db_session = session
        
        options = [
            SelectOption(label=cat.name, value=str(cat.id))
            for cat in categories
        ]
        
        select = ui.Select(placeholder="Select a category...", options=options)
        select.callback = self.category_selected
        self.add_item(select)
    
    async def category_selected(self, interaction: Interaction):
        category_id = int(self.children[0].values[0])
        
        # Fetch tools in this category
        result = await self.db_session.execute(
            select(Tool).where(Tool.category_id == category_id)
        )
        tools = result.scalars().all()
        
        if not tools:
            await interaction.response.send_message(
                "This category has no tools.",
                ephemeral=True
            )
            return
        
        # Create view with edit buttons for each tool
        view = EditToolListView(self.db_session, tools)
        embed = Embed(
            title="Edit Tool",
            description="Select a tool to edit:",
            color=discord.Color.blurple()
        )
        
        tool_list = "\n".join([f"• **{tool.name}**" for tool in tools])
        embed.add_field(name="Tools", value=tool_list, inline=False)
        
        await interaction.response.edit_message(embed=embed, view=view)


class EditToolListView(ui.View):
    """View showing edit buttons for each tool."""
    
    def __init__(self, session: AsyncSession, tools: List[Tool]):
        super().__init__(timeout=300)
        self.db_session = session
        
        for idx, tool in enumerate(tools[:25]):
            button = ui.Button(
                label=f"Edit: {tool.name[:20]}",
                style=ButtonStyle.blurple,
                row=idx // 5
            )
            button.callback = self.create_edit_callback(tool)
            self.add_item(button)
    
    def create_edit_callback(self, tool: Tool):
        async def callback(interaction: Interaction):
            modal = EditToolModal(self.db_session, tool)
            await interaction.response.send_modal(modal)
        return callback


class EditToolModal(ui.Modal, title="Edit Tool"):
    """Modal for editing a tool."""
    
    tool_name = ui.TextInput(label="Tool Name", required=True, max_length=100)
    tool_url = ui.TextInput(label="Tool URL", required=True, max_length=200)
    tool_description = ui.TextInput(
        label="Tool Description",
        style=TextStyle.paragraph,
        required=True,
        max_length=1000
    )
    
    def __init__(self, session: AsyncSession, tool: Tool):
        super().__init__()
        self.db_session = session
        self.tool = tool
        
        # Pre-fill with existing data
        self.tool_name.default = tool.name
        self.tool_url.default = tool.url
        self.tool_description.default = tool.description
    
    async def on_submit(self, interaction: Interaction):
        # Check if new name conflicts with another tool
        if self.tool_name.value != self.tool.name:
            result = await self.db_session.execute(
                select(Tool).where(Tool.name == self.tool_name.value)
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                await interaction.response.send_message(
                    f"A tool named '{self.tool_name.value}' already exists.",
                    ephemeral=True
                )
                return
        
        # Update tool
        self.tool.name = self.tool_name.value
        self.tool.url = self.tool_url.value
        self.tool.description = self.tool_description.value
        await self.db_session.commit()
        
        await interaction.response.send_message(
            f"✅ Tool '{self.tool_name.value}' has been updated.",
            ephemeral=True
        )


class DeleteToolCategorySelect(ui.View):
    """View for selecting category when deleting tools."""
    
    def __init__(self, session: AsyncSession, categories: List[Category]):
        super().__init__(timeout=300)
        self.db_session = session
        
        options = [
            SelectOption(label=cat.name, value=str(cat.id))
            for cat in categories
        ]
        
        select = ui.Select(placeholder="Select a category...", options=options)
        select.callback = self.category_selected
        self.add_item(select)
    
    async def category_selected(self, interaction: Interaction):
        category_id = int(self.children[0].values[0])
        
        # Fetch tools in this category
        result = await self.db_session.execute(
            select(Tool).where(Tool.category_id == category_id)
        )
        tools = result.scalars().all()
        
        if not tools:
            await interaction.response.send_message(
                "This category has no tools.",
                ephemeral=True
            )
            return
        
        # Create view with delete buttons for each tool
        view = DeleteToolListView(self.db_session, tools)
        embed = Embed(
            title="Delete Tool",
            description="Select a tool to delete:",
            color=discord.Color.red()
        )
        
        tool_list = "\n".join([f"• **{tool.name}**" for tool in tools])
        embed.add_field(name="Tools", value=tool_list, inline=False)
        
        await interaction.response.edit_message(embed=embed, view=view)


class DeleteToolListView(ui.View):
    """View showing delete buttons for each tool."""
    
    def __init__(self, session: AsyncSession, tools: List[Tool]):
        super().__init__(timeout=300)
        self.db_session = session
        
        for idx, tool in enumerate(tools[:25]):
            button = ui.Button(
                label=f"Delete: {tool.name[:20]}",
                style=ButtonStyle.red,
                row=idx // 5
            )
            button.callback = self.create_delete_callback(tool)
            self.add_item(button)
    
    def create_delete_callback(self, tool: Tool):
        async def callback(interaction: Interaction):
            view = ui.View(timeout=60)
            confirm_button = ui.Button(label="Confirm Delete", style=ButtonStyle.danger)
            cancel_button = ui.Button(label="Cancel", style=ButtonStyle.secondary)
            
            async def confirm_callback(confirm_interaction: Interaction):
                await self.db_session.delete(tool)
                await self.db_session.commit()
                await confirm_interaction.response.edit_message(
                    content=f"✅ Tool '{tool.name}' has been deleted.",
                    embed=None,
                    view=None
                )
            
            async def cancel_callback(cancel_interaction: Interaction):
                await cancel_interaction.response.edit_message(
                    content="Deletion cancelled.",
                    embed=None,
                    view=None
                )
            
            confirm_button.callback = confirm_callback
            cancel_button.callback = cancel_callback
            view.add_item(confirm_button)
            view.add_item(cancel_button)
            
            embed = Embed(
                title="⚠️ Confirm Deletion",
                description=f"Are you sure you want to delete **{tool.name}**?\n\nThis action cannot be undone.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        
        return callback


class CategoryManagementView(ui.View):
    """View for managing categories."""
    
    def __init__(self):
        super().__init__(timeout=300)
    
    @ui.button(label="Add Category", style=ButtonStyle.green)
    async def add_category(self, interaction: Interaction, button: ui.Button):
        from db import AsyncSessionLocal
        
        async with AsyncSessionLocal() as session:
            modal = AddCategoryModal(session)
            await interaction.response.send_modal(modal)
    
    @ui.button(label="Edit Category", style=ButtonStyle.blurple)
    async def edit_category(self, interaction: Interaction, button: ui.Button):
        from db import AsyncSessionLocal
        
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Category))
            categories = result.scalars().all()
            
            if not categories:
                await interaction.response.send_message(
                    "No categories available.",
                    ephemeral=True
                )
                return
            
            view = EditCategorySelect(session, categories)
            embed = Embed(
                title="Edit Category",
                description="Select a category to edit:",
                color=discord.Color.blurple()
            )
            await interaction.response.edit_message(embed=embed, view=view)
    
    @ui.button(label="Delete Category", style=ButtonStyle.red)
    async def delete_category(self, interaction: Interaction, button: ui.Button):
        from db import AsyncSessionLocal
        
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Category))
            categories = result.scalars().all()
            
            if not categories:
                await interaction.response.send_message(
                    "No categories available.",
                    ephemeral=True
                )
                return
            
            view = DeleteCategorySelect(session, categories)
            embed = Embed(
                title="Delete Category",
                description="⚠️ Select a category to delete.\n**Warning:** This will also delete all tools in the category!",
                color=discord.Color.red()
            )
            await interaction.response.edit_message(embed=embed, view=view)


class AddCategoryModal(ui.Modal, title="Add New Category"):
    """Modal for adding a new category."""
    
    category_name = ui.TextInput(label="Category Name", required=True, max_length=100)
    category_description = ui.TextInput(
        label="Category Description",
        style=TextStyle.paragraph,
        required=False,
        max_length=500
    )
    
    def __init__(self, session: AsyncSession):
        super().__init__()
        self.db_session = session
    
    async def on_submit(self, interaction: Interaction):
        # Check if category already exists
        result = await self.db_session.execute(
            select(Category).where(Category.name == self.category_name.value)
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            await interaction.response.send_message(
                f"A category named '{self.category_name.value}' already exists.",
                ephemeral=True
            )
            return
        
        # Create category
        category = Category(
            name=self.category_name.value,
            description=self.category_description.value or None
        )
        self.db_session.add(category)
        await self.db_session.commit()
        
        await interaction.response.send_message(
            f"✅ Category '{self.category_name.value}' has been created.",
            ephemeral=True
        )


class EditCategorySelect(ui.View):
    """View for selecting category to edit."""
    
    def __init__(self, session: AsyncSession, categories: List[Category]):
        super().__init__(timeout=300)
        self.db_session = session
        
        options = [
            SelectOption(label=cat.name, value=str(cat.id))
            for cat in categories
        ]
        
        select = ui.Select(placeholder="Select a category...", options=options)
        select.callback = self.category_selected
        self.add_item(select)
        self.categories = {cat.id: cat for cat in categories}
    
    async def category_selected(self, interaction: Interaction):
        category_id = int(self.children[0].values[0])
        category = self.categories[category_id]
        
        modal = EditCategoryModal(self.db_session, category)
        await interaction.response.send_modal(modal)


class EditCategoryModal(ui.Modal, title="Edit Category"):
    """Modal for editing a category."""
    
    category_name = ui.TextInput(label="Category Name", required=True, max_length=100)
    category_description = ui.TextInput(
        label="Category Description",
        style=TextStyle.paragraph,
        required=False,
        max_length=500
    )
    
    def __init__(self, session: AsyncSession, category: Category):
        super().__init__()
        self.db_session = session
        self.category = category
        
        # Pre-fill with existing data
        self.category_name.default = category.name
        self.category_description.default = category.description or ""
    
    async def on_submit(self, interaction: Interaction):
        # Check if new name conflicts
        if self.category_name.value != self.category.name:
            result = await self.db_session.execute(
                select(Category).where(Category.name == self.category_name.value)
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                await interaction.response.send_message(
                    f"A category named '{self.category_name.value}' already exists.",
                    ephemeral=True
                )
                return
        
        # Update category
        self.category.name = self.category_name.value
        self.category.description = self.category_description.value or None
        await self.db_session.commit()
        
        await interaction.response.send_message(
            f"✅ Category '{self.category_name.value}' has been updated.",
            ephemeral=True
        )


class DeleteCategorySelect(ui.View):
    """View for selecting category to delete."""
    
    def __init__(self, session: AsyncSession, categories: List[Category]):
        super().__init__(timeout=300)
        self.db_session = session
        
        options = [
            SelectOption(label=cat.name, value=str(cat.id))
            for cat in categories
        ]
        
        select = ui.Select(placeholder="Select a category...", options=options)
        select.callback = self.category_selected
        self.add_item(select)
        self.categories = {cat.id: cat for cat in categories}
    
    async def category_selected(self, interaction: Interaction):
        category_id = int(self.children[0].values[0])
        category = self.categories[category_id]
        
        # Count tools in category
        result = await self.db_session.execute(
            select(Tool).where(Tool.category_id == category_id)
        )
        tools = result.scalars().all()
        tool_count = len(tools)
        
        view = ui.View(timeout=60)
        confirm_button = ui.Button(label="Confirm Delete", style=ButtonStyle.danger)
        cancel_button = ui.Button(label="Cancel", style=ButtonStyle.secondary)
        
        async def confirm_callback(confirm_interaction: Interaction):
            await self.db_session.delete(category)
            await self.db_session.commit()
            await confirm_interaction.response.edit_message(
                content=f"✅ Category '{category.name}' and its {tool_count} tool(s) have been deleted.",
                embed=None,
                view=None
            )
        
        async def cancel_callback(cancel_interaction: Interaction):
            await cancel_interaction.response.edit_message(
                content="Deletion cancelled.",
                embed=None,
                view=None
            )
        
        confirm_button.callback = confirm_callback
        cancel_button.callback = cancel_callback
        view.add_item(confirm_button)
        view.add_item(cancel_button)
        
        embed = Embed(
            title="⚠️ Confirm Category Deletion",
            description=f"Are you sure you want to delete the category **{category.name}**?\n\n"
                       f"This will also delete **{tool_count} tool(s)** in this category.\n\n"
                       f"**This action cannot be undone.**",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


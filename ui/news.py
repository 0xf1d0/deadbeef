from discord import ui, ButtonStyle, Interaction, Embed, SelectOption, Color
from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import NewsChannel, NewsFeed, SentNewsEntry


class SetupNewsChannelModal(ui.Modal, title="Setup News Channel"):
    """Modal for setting up a news channel."""
    
    channel_name = ui.TextInput(
        label="Channel Name",
        placeholder="e.g., Cybersecurity News",
        required=True,
        max_length=100
    )
    
    def __init__(self, session: AsyncSession, channel_id: int):
        super().__init__()
        self.db_session = session
        self.channel_id = channel_id
    
    async def on_submit(self, interaction: Interaction):
        # Check if channel is already configured
        result = await self.db_session.execute(
            select(NewsChannel).where(NewsChannel.channel_id == self.channel_id)
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            await interaction.response.send_message(
                f"❌ This channel is already configured as '{existing.name}'.",
                ephemeral=True
            )
            return
        
        # Create news channel configuration
        news_channel = NewsChannel(
            channel_id=self.channel_id,
            name=self.channel_name.value,
            is_active=True
        )
        
        self.db_session.add(news_channel)
        await self.db_session.commit()
        
        await interaction.response.send_message(
            f"✅ News channel '{self.channel_name.value}' configured!\n"
            f"Now add RSS feeds using 'Add Feed' button.",
            ephemeral=True
        )


class AddFeedModal(ui.Modal, title="Add News Feed"):
    """Modal for adding a news feed."""
    
    feed_name = ui.TextInput(
        label="Feed Name",
        placeholder="e.g., CERT-FR",
        required=True,
        max_length=100
    )
    
    feed_url = ui.TextInput(
        label="RSS Feed URL",
        placeholder="https://www.cert.ssi.gouv.fr/feed/",
        required=True,
        max_length=500
    )
    
    feed_color = ui.TextInput(
        label="Embed Color (hex, optional)",
        placeholder="#FF0000 or red or blue",
        required=False,
        max_length=20
    )
    
    def __init__(self, session: AsyncSession, channel_id: int):
        super().__init__()
        self.db_session = session
        self.channel_id = channel_id
    
    async def on_submit(self, interaction: Interaction):
        # Check if channel is configured
        result = await self.db_session.execute(
            select(NewsChannel).where(NewsChannel.channel_id == self.channel_id)
        )
        channel_config = result.scalar_one_or_none()
        
        if not channel_config:
            await interaction.response.send_message(
                "❌ This channel is not configured for news. Use 'Setup Channel' first.",
                ephemeral=True
            )
            return
        
        # Parse color
        color_value = self.feed_color.value.strip() if self.feed_color.value else None
        if color_value:
            # Handle named colors
            color_map = {
                'red': '#FF0000',
                'blue': '#0000FF',
                'green': '#00FF00',
                'yellow': '#FFFF00',
                'orange': '#FFA500',
                'purple': '#800080',
                'cyan': '#00FFFF',
                'magenta': '#FF00FF'
            }
            if color_value.lower() in color_map:
                color_value = color_map[color_value.lower()]
            elif not color_value.startswith('#'):
                color_value = '#' + color_value
        
        # Create feed
        feed = NewsFeed(
            channel_id=self.channel_id,
            name=self.feed_name.value,
            url=self.feed_url.value,
            color=color_value,
            is_active=True
        )
        
        self.db_session.add(feed)
        await self.db_session.commit()
        
        await interaction.response.send_message(
            f"✅ Feed '{self.feed_name.value}' added!\n"
            f"It will start fetching news within 30 minutes.",
            ephemeral=True
        )


class EditFeedModal(ui.Modal, title="Edit News Feed"):
    """Modal for editing a news feed."""
    
    feed_name = ui.TextInput(label="Feed Name", required=True, max_length=100)
    feed_url = ui.TextInput(label="RSS Feed URL", required=True, max_length=500)
    feed_color = ui.TextInput(
        label="Embed Color (hex, optional)",
        placeholder="#FF0000 or red",
        required=False,
        max_length=20
    )
    
    def __init__(self, session: AsyncSession, feed: NewsFeed):
        super().__init__()
        self.db_session = session
        self.feed = feed
        
        # Pre-fill with existing data
        self.feed_name.default = feed.name
        self.feed_url.default = feed.url
        self.feed_color.default = feed.color or ""
    
    async def on_submit(self, interaction: Interaction):
        # Parse color
        color_value = self.feed_color.value.strip() if self.feed_color.value else None
        if color_value:
            color_map = {
                'red': '#FF0000', 'blue': '#0000FF', 'green': '#00FF00',
                'yellow': '#FFFF00', 'orange': '#FFA500', 'purple': '#800080',
                'cyan': '#00FFFF', 'magenta': '#FF00FF'
            }
            if color_value.lower() in color_map:
                color_value = color_map[color_value.lower()]
            elif not color_value.startswith('#'):
                color_value = '#' + color_value
        
        # Update feed
        self.feed.name = self.feed_name.value
        self.feed.url = self.feed_url.value
        self.feed.color = color_value
        
        await self.db_session.commit()
        
        await interaction.response.send_message(
            f"✅ Feed '{self.feed_name.value}' has been updated!",
            ephemeral=True
        )


class NewsManagementView(ui.View):
    """Main view for managing news feeds."""
    
    def __init__(self):
        super().__init__(timeout=300)
    
    @ui.button(label="Setup Channel", style=ButtonStyle.green)
    async def setup_channel(self, interaction: Interaction, button: ui.Button):
        from db import AsyncSessionLocal
        
        async with AsyncSessionLocal() as session:
            modal = SetupNewsChannelModal(session, interaction.channel_id)
            await interaction.response.send_modal(modal)
    
    @ui.button(label="Add Feed", style=ButtonStyle.blurple)
    async def add_feed(self, interaction: Interaction, button: ui.Button):
        from db import AsyncSessionLocal
        
        async with AsyncSessionLocal() as session:
            modal = AddFeedModal(session, interaction.channel_id)
            await interaction.response.send_modal(modal)
    
    @ui.button(label="Manage Feeds", style=ButtonStyle.secondary)
    async def manage_feeds(self, interaction: Interaction, button: ui.Button):
        from db import AsyncSessionLocal
        
        async with AsyncSessionLocal() as session:
            # Get channel config
            result = await session.execute(
                select(NewsChannel).where(NewsChannel.channel_id == interaction.channel_id)
            )
            channel_config = result.scalar_one_or_none()
            
            if not channel_config:
                await interaction.response.send_message(
                    "❌ This channel is not configured for news.",
                    ephemeral=True
                )
                return
            
            # Get feeds
            if not channel_config.feeds:
                await interaction.response.send_message(
                    "❌ No feeds configured. Use 'Add Feed' first.",
                    ephemeral=True
                )
                return
            
            view = FeedManagementView(session, channel_config.feeds)
            embed = Embed(
                title="📰 Manage News Feeds",
                description="Select a feed to edit, toggle, or delete:",
                color=Color.blue()
            )
            
            feed_list = []
            for feed in channel_config.feeds:
                status = "✅" if bool(feed.is_active) else "⏸️"
                feed_list.append(f"{status} **{feed.name}** - {feed.url[:50]}...")
            
            embed.add_field(name="Feeds", value="\n".join(feed_list), inline=False)
            
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @ui.button(label="View Status", style=ButtonStyle.grey)
    async def view_status(self, interaction: Interaction, button: ui.Button):
        from db import AsyncSessionLocal
        
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(NewsChannel).where(NewsChannel.channel_id == interaction.channel_id)
            )
            channel_config = result.scalar_one_or_none()
            
            if not channel_config:
                await interaction.response.send_message(
                    "❌ This channel is not configured for news.",
                    ephemeral=True
                )
                return
            
            embed = Embed(
                title=f"📰 News Channel Status: {channel_config.name}",
                color=Color.blue()
            )
            embed.add_field(name="Channel ID", value=str(channel_config.channel_id), inline=False)
            embed.add_field(
                name="Status",
                value="🟢 Active" if bool(channel_config.is_active) else "🔴 Inactive",
                inline=False
            )
            embed.add_field(name="Total Feeds", value=str(len(channel_config.feeds)), inline=True)
            
            active_feeds = len([f for f in channel_config.feeds if bool(f.is_active)])
            embed.add_field(name="Active Feeds", value=str(active_feeds), inline=True)
            
            if channel_config.feeds:
                feed_info = []
                for feed in channel_config.feeds:
                    status = "✅" if bool(feed.is_active) else "⏸️"
                    sent_count = len(feed.sent_entries)
                    feed_info.append(f"{status} **{feed.name}** - {sent_count} entries sent")
                
                embed.add_field(name="Feeds", value="\n".join(feed_info), inline=False)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @ui.button(label="Delete Channel", style=ButtonStyle.red)
    async def delete_channel(self, interaction: Interaction, button: ui.Button):
        from db import AsyncSessionLocal
        
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(NewsChannel).where(NewsChannel.channel_id == interaction.channel_id)
            )
            channel_config = result.scalar_one_or_none()
            
            if not channel_config:
                await interaction.response.send_message(
                    "❌ This channel is not configured for news.",
                    ephemeral=True
                )
                return
            
            # Confirmation view
            confirm_view = ui.View(timeout=60)
            confirm_button = ui.Button(label="Confirm Delete", style=ButtonStyle.danger)
            cancel_button = ui.Button(label="Cancel", style=ButtonStyle.secondary)
            
            async def confirm_callback(confirm_interaction: Interaction):
                await session.delete(channel_config)
                await session.commit()
                
                await confirm_interaction.response.edit_message(
                    content=f"✅ News channel '{channel_config.name}' and all its feeds have been deleted.",
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
            confirm_view.add_item(confirm_button)
            confirm_view.add_item(cancel_button)
            
            embed = Embed(
                title="⚠️ Confirm Channel Deletion",
                description=f"Are you sure you want to delete news channel **{channel_config.name}**?\n\n"
                           f"This will delete:\n"
                           f"• {len(channel_config.feeds)} feed(s)\n"
                           f"• All tracking data\n\n"
                           f"**This action cannot be undone.**",
                color=Color.red()
            )
            await interaction.response.send_message(embed=embed, view=confirm_view, ephemeral=True)


class FeedManagementView(ui.View):
    """View for managing individual feeds."""
    
    def __init__(self, session: AsyncSession, feeds: List[NewsFeed]):
        super().__init__(timeout=300)
        self.db_session = session
        
        # Add feed selector
        options = [
            SelectOption(
                label=f"{feed.name}",
                value=str(feed.id),
                description=feed.url[:100]
            )
            for feed in feeds[:25]  # Discord limit
        ]
        
        select = ui.Select(placeholder="Select a feed...", options=options)
        select.callback = self.feed_selected
        self.add_item(select)
        self.feeds = {feed.id: feed for feed in feeds}
        self.selected_feed_id = None
    
    async def feed_selected(self, interaction: Interaction):
        self.selected_feed_id = int(self.children[0].values[0])
        feed = self.feeds[self.selected_feed_id]
        
        # Show feed management buttons
        view = FeedActionsView(self.db_session, feed)
        embed = Embed(
            title=f"📰 Manage Feed: {feed.name}",
            color=Color.blue()
        )
        embed.add_field(name="URL", value=feed.url, inline=False)
        embed.add_field(name="Color", value=feed.color or "Default", inline=True)
        embed.add_field(
            name="Status",
            value="🟢 Active" if feed.is_active == 'true' else "🔴 Inactive",
            inline=True
        )
        embed.add_field(name="Entries Sent", value=str(len(feed.sent_entries)), inline=True)
        
        await interaction.response.edit_message(embed=embed, view=view)


class FeedActionsView(ui.View):
    """View with actions for a specific feed."""
    
    def __init__(self, session: AsyncSession, feed: NewsFeed):
        super().__init__(timeout=300)
        self.db_session = session
        self.feed = feed
    
    @ui.button(label="Edit", style=ButtonStyle.blurple)
    async def edit_feed(self, interaction: Interaction, button: ui.Button):
        modal = EditFeedModal(self.db_session, self.feed)
        await interaction.response.send_modal(modal)
    
    @ui.button(label="Toggle Active", style=ButtonStyle.secondary)
    async def toggle_active(self, interaction: Interaction, button: ui.Button):
        # Toggle active status
        self.feed.is_active = not bool(self.feed.is_active)
        await self.db_session.commit()
        
        status = "activated" if bool(self.feed.is_active) else "deactivated"
        await interaction.response.send_message(
            f"✅ Feed '{self.feed.name}' has been {status}.",
            ephemeral=True
        )
    
    @ui.button(label="Clear History", style=ButtonStyle.grey)
    async def clear_history(self, interaction: Interaction, button: ui.Button):
        # Confirmation
        confirm_view = ui.View(timeout=60)
        confirm_button = ui.Button(label="Confirm Clear", style=ButtonStyle.danger)
        cancel_button = ui.Button(label="Cancel", style=ButtonStyle.secondary)
        
        async def confirm_callback(confirm_interaction: Interaction):
            # Delete all sent entries for this feed
            for entry in self.feed.sent_entries:
                await self.db_session.delete(entry)
            await self.db_session.commit()
            
            await confirm_interaction.response.edit_message(
                content=f"✅ History cleared for '{self.feed.name}'. It will re-send old entries.",
                embed=None,
                view=None
            )
        
        async def cancel_callback(cancel_interaction: Interaction):
            await cancel_interaction.response.edit_message(
                content="Clear cancelled.",
                embed=None,
                view=None
            )
        
        confirm_button.callback = confirm_callback
        cancel_button.callback = cancel_callback
        confirm_view.add_item(confirm_button)
        confirm_view.add_item(cancel_button)
        
        embed = Embed(
            title="⚠️ Confirm History Clear",
            description=f"This will clear all {len(self.feed.sent_entries)} sent entry records for **{self.feed.name}**.\n\n"
                       f"Old news entries will be re-sent as if they're new.\n\n"
                       f"This is useful if you want to reset the feed.",
            color=Color.orange()
        )
        await interaction.response.send_message(embed=embed, view=confirm_view, ephemeral=True)
    
    @ui.button(label="Delete Feed", style=ButtonStyle.red)
    async def delete_feed(self, interaction: Interaction, button: ui.Button):
        # Confirmation
        confirm_view = ui.View(timeout=60)
        confirm_button = ui.Button(label="Confirm Delete", style=ButtonStyle.danger)
        cancel_button = ui.Button(label="Cancel", style=ButtonStyle.secondary)
        
        async def confirm_callback(confirm_interaction: Interaction):
            await self.db_session.delete(self.feed)
            await self.db_session.commit()
            
            await confirm_interaction.response.edit_message(
                content=f"✅ Feed '{self.feed.name}' has been deleted.",
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
        confirm_view.add_item(confirm_button)
        confirm_view.add_item(cancel_button)
        
        embed = Embed(
            title="⚠️ Confirm Feed Deletion",
            description=f"Are you sure you want to delete feed **{self.feed.name}**?\n\n"
                       f"This will also delete {len(self.feed.sent_entries)} tracking records.\n\n"
                       f"**This action cannot be undone.**",
            color=Color.red()
        )
        await interaction.response.send_message(embed=embed, view=confirm_view, ephemeral=True)


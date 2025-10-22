import discord
from discord import ui, ButtonStyle, TextStyle, Interaction, Embed, SelectOption
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import ScheduleChannelConfig

# Day names mapping
DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
DAY_NAMES_FR = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]


class SetupScheduleModal(ui.Modal, title="Setup Schedule Channel"):
    """Modal for setting up a schedule channel."""
    
    grade_level = ui.TextInput(
        label="Grade Level",
        placeholder="e.g., M1 or M2",
        required=True,
        max_length=10
    )
    
    spreadsheet_url = ui.TextInput(
        label="Google Sheets URL",
        placeholder="https://docs.google.com/spreadsheets/d/...",
        required=True,
        max_length=500
    )
    
    gid = ui.TextInput(
        label="Sheet GID (from URL)",
        placeholder="e.g., 1908497559",
        required=True,
        max_length=50
    )
    
    classes_per_day = ui.TextInput(
        label="Classes per day",
        placeholder="2 for M1, 3 for M2",
        required=True,
        default="2",
        max_length=1
    )
    
    day_range = ui.TextInput(
        label="Day range (e.g., Mon-Wed or Wed-Fri)",
        placeholder="Format: Mon-Tue or Monday-Wednesday",
        required=True,
        default="Mon-Tue",
        max_length=30
    )
    
    def __init__(self, session: AsyncSession, channel_id: int):
        super().__init__()
        self.db_session = session
        self.channel_id = channel_id
    
    async def on_submit(self, interaction: Interaction):
        # Check if channel is already configured
        result = await self.db_session.execute(
            select(ScheduleChannelConfig).where(
                ScheduleChannelConfig.channel_id == self.channel_id
            )
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            await interaction.response.send_message(
                f"❌ This channel is already configured for {existing.grade_level} schedule.",
                ephemeral=True
            )
            return
        
        # Check if grade level is already used
        result = await self.db_session.execute(
            select(ScheduleChannelConfig).where(
                ScheduleChannelConfig.grade_level == self.grade_level.value
            )
        )
        existing_grade = result.scalar_one_or_none()
        
        if existing_grade:
            await interaction.response.send_message(
                f"❌ Grade level '{self.grade_level.value}' is already configured in another channel.",
                ephemeral=True
            )
            return
        
        # Extract spreadsheet ID from URL
        spreadsheet_id = None
        url = self.spreadsheet_url.value
        
        # Try to extract spreadsheet ID from various URL formats
        if '/d/' in url:
            try:
                spreadsheet_id = url.split('/d/')[1].split('/')[0]
            except:
                pass
        
        if not spreadsheet_id:
            await interaction.response.send_message(
                "❌ Could not extract spreadsheet ID from URL. Please check the URL format.",
                ephemeral=True
            )
            return
        
        # Validate classes_per_day
        try:
            classes_per_day_value = int(self.classes_per_day.value)
            if classes_per_day_value not in [2, 3]:
                await interaction.response.send_message(
                    "❌ Classes per day must be 2 or 3.",
                    ephemeral=True
                )
                return
        except ValueError:
            await interaction.response.send_message(
                "❌ Classes per day must be a number (2 or 3).",
                ephemeral=True
            )
            return
        
        # Parse day range
        day_range_input = self.day_range.value.strip()
        parts = day_range_input.split('-')
        
        if len(parts) != 2:
            await interaction.response.send_message(
                "❌ Invalid day range format. Use 'Mon-Wed' or 'Monday-Wednesday'.",
                ephemeral=True
            )
            return
        
        start_day_str = parts[0].strip().lower()
        end_day_str = parts[1].strip().lower()
        
        # Map day names to indices
        day_mapping = {
            'mon': 0, 'monday': 0, 'lundi': 0,
            'tue': 1, 'tuesday': 1, 'mardi': 1,
            'wed': 2, 'wednesday': 2, 'mercredi': 2,
            'thu': 3, 'thursday': 3, 'jeudi': 3,
            'fri': 4, 'friday': 4, 'vendredi': 4,
            'sat': 5, 'saturday': 5, 'samedi': 5,
            'sun': 6, 'sunday': 6, 'dimanche': 6,
        }
        
        start_day_index = day_mapping.get(start_day_str)
        end_day_index = day_mapping.get(end_day_str)
        
        if start_day_index is None or end_day_index is None:
            await interaction.response.send_message(
                "❌ Invalid day names. Use day names like 'Mon', 'Monday', or 'Lundi'.",
                ephemeral=True
            )
            return
        
        if start_day_index > end_day_index:
            await interaction.response.send_message(
                "❌ Start day must be before or equal to end day.",
                ephemeral=True
            )
            return
        
        # Create configuration
        config = ScheduleChannelConfig(
            channel_id=self.channel_id,
            grade_level=self.grade_level.value,
            spreadsheet_url=self.spreadsheet_url.value,
            gid=self.gid.value,
            classes_per_day=classes_per_day_value,
            start_day_index=start_day_index,
            end_day_index=end_day_index
        )
        
        self.db_session.add(config)
        await self.db_session.commit()
        
        # Trigger immediate schedule update
        from cogs.schedule import update_schedule_for_channel
        await update_schedule_for_channel(interaction.client, self.db_session, config)
        
        await interaction.response.send_message(
            f"✅ Schedule channel configured for {self.grade_level.value}!\n"
            f"The schedule will update automatically every 15 minutes.",
            ephemeral=True
        )


class EditScheduleConfigModal(ui.Modal, title="Edit Schedule Configuration"):
    """Modal for editing schedule configuration."""
    
    spreadsheet_url = ui.TextInput(
        label="Google Sheets URL",
        placeholder="https://docs.google.com/spreadsheets/d/...",
        required=True,
        max_length=500
    )
    
    gid = ui.TextInput(
        label="Sheet GID (from URL)",
        placeholder="e.g., 1908497559",
        required=True,
        max_length=50
    )
    
    classes_per_day = ui.TextInput(
        label="Classes per day",
        placeholder="2 for M1, 3 for M2",
        required=True,
        max_length=1
    )
    
    day_range = ui.TextInput(
        label="Day range (e.g., Mon-Wed or Wed-Fri)",
        placeholder="Format: Mon-Tue or Monday-Wednesday",
        required=True,
        max_length=30
    )
    
    def __init__(self, session: AsyncSession, config: ScheduleChannelConfig):
        super().__init__()
        self.db_session = session
        self.config = config
        
        # Pre-fill with existing data
        self.spreadsheet_url.default = config.spreadsheet_url
        self.gid.default = config.gid
        self.classes_per_day.default = str(getattr(config, 'classes_per_day', 2))
        
        # Format day range for display
        start_idx = getattr(config, 'start_day_index', 0)
        end_idx = getattr(config, 'end_day_index', 1)
        self.day_range.default = f"{DAY_NAMES[start_idx][:3]}-{DAY_NAMES[end_idx][:3]}"
    
    async def on_submit(self, interaction: Interaction):
        # Extract spreadsheet ID from URL
        spreadsheet_id = None
        url = self.spreadsheet_url.value
        
        if '/d/' in url:
            try:
                spreadsheet_id = url.split('/d/')[1].split('/')[0]
            except:
                pass
        
        if not spreadsheet_id:
            await interaction.response.send_message(
                "❌ Could not extract spreadsheet ID from URL. Please check the URL format.",
                ephemeral=True
            )
            return
        
        # Validate classes_per_day
        try:
            classes_per_day_value = int(self.classes_per_day.value)
            if classes_per_day_value not in [2, 3]:
                await interaction.response.send_message(
                    "❌ Classes per day must be 2 or 3.",
                    ephemeral=True
                )
                return
        except ValueError:
            await interaction.response.send_message(
                "❌ Classes per day must be a number (2 or 3).",
                ephemeral=True
            )
            return
        
        # Parse day range
        day_range_input = self.day_range.value.strip()
        parts = day_range_input.split('-')
        
        if len(parts) != 2:
            await interaction.response.send_message(
                "❌ Invalid day range format. Use 'Mon-Wed' or 'Monday-Wednesday'.",
                ephemeral=True
            )
            return
        
        start_day_str = parts[0].strip().lower()
        end_day_str = parts[1].strip().lower()
        
        # Map day names to indices
        day_mapping = {
            'mon': 0, 'monday': 0, 'lundi': 0,
            'tue': 1, 'tuesday': 1, 'mardi': 1,
            'wed': 2, 'wednesday': 2, 'mercredi': 2,
            'thu': 3, 'thursday': 3, 'jeudi': 3,
            'fri': 4, 'friday': 4, 'vendredi': 4,
            'sat': 5, 'saturday': 5, 'samedi': 5,
            'sun': 6, 'sunday': 6, 'dimanche': 6,
        }
        
        start_day_index = day_mapping.get(start_day_str)
        end_day_index = day_mapping.get(end_day_str)
        
        if start_day_index is None or end_day_index is None:
            await interaction.response.send_message(
                "❌ Invalid day names. Use day names like 'Mon', 'Monday', or 'Lundi'.",
                ephemeral=True
            )
            return
        
        if start_day_index > end_day_index:
            await interaction.response.send_message(
                "❌ Start day must be before or equal to end day.",
                ephemeral=True
            )
            return
        
        # Update configuration
        self.config.spreadsheet_url = self.spreadsheet_url.value
        self.config.gid = self.gid.value
        self.config.classes_per_day = classes_per_day_value
        self.config.start_day_index = start_day_index
        self.config.end_day_index = end_day_index
        self.config.last_schedule_hash = None  # Reset to force update
        
        await self.db_session.commit()
        
        # Trigger immediate schedule update
        from cogs.schedule import update_schedule_for_channel
        await update_schedule_for_channel(interaction.client, self.db_session, self.config)
        
        await interaction.response.send_message(
            f"✅ Schedule configuration updated for {self.config.grade_level}!",
            ephemeral=True
        )


class ScheduleManagementView(ui.View):
    """View for managing schedule configurations."""
    
    def __init__(self):
        super().__init__(timeout=300)
    
    @ui.button(label="Setup New Channel", style=ButtonStyle.green)
    async def setup_channel(self, interaction: Interaction, button: ui.Button):
        from db import AsyncSessionLocal
        
        async with AsyncSessionLocal() as session:
            modal = SetupScheduleModal(session, interaction.channel_id)
            await interaction.response.send_modal(modal)
    
    @ui.button(label="Edit Configuration", style=ButtonStyle.blurple)
    async def edit_config(self, interaction: Interaction, button: ui.Button):
        from db import AsyncSessionLocal
        
        async with AsyncSessionLocal() as session:
            # Get config for this channel
            result = await session.execute(
                select(ScheduleChannelConfig).where(
                    ScheduleChannelConfig.channel_id == interaction.channel_id
                )
            )
            config = result.scalar_one_or_none()
            
            if not config:
                await interaction.response.send_message(
                    "❌ This channel is not configured for schedule display. Use 'Setup New Channel' first.",
                    ephemeral=True
                )
                return
            
            modal = EditScheduleConfigModal(session, config)
            await interaction.response.send_modal(modal)
    
    @ui.button(label="Force Refresh", style=ButtonStyle.grey)
    async def force_refresh(self, interaction: Interaction, button: ui.Button):
        from db import AsyncSessionLocal
        
        async with AsyncSessionLocal() as session:
            # Get config for this channel
            result = await session.execute(
                select(ScheduleChannelConfig).where(
                    ScheduleChannelConfig.channel_id == interaction.channel_id
                )
            )
            config = result.scalar_one_or_none()
            
            if not config:
                await interaction.response.send_message(
                    "❌ This channel is not configured for schedule display.",
                    ephemeral=True
                )
                return
            
            # Reset hash to force update
            config.last_schedule_hash = None
            await session.commit()
            
            # Trigger update
            from cogs.schedule import update_schedule_for_channel
            await update_schedule_for_channel(interaction.client, session, config)
            
            await interaction.response.send_message(
                "✅ Schedule refreshed!",
                ephemeral=True
            )
    
    @ui.button(label="View Configuration", style=ButtonStyle.secondary)
    async def view_config(self, interaction: Interaction, button: ui.Button):
        from db import AsyncSessionLocal
        
        async with AsyncSessionLocal() as session:
            # Get config for this channel
            result = await session.execute(
                select(ScheduleChannelConfig).where(
                    ScheduleChannelConfig.channel_id == interaction.channel_id
                )
            )
            config = result.scalar_one_or_none()
            
            if not config:
                await interaction.response.send_message(
                    "❌ This channel is not configured for schedule display.",
                    ephemeral=True
                )
                return
            
            # Get day range
            start_idx = getattr(config, 'start_day_index', 0)
            end_idx = getattr(config, 'end_day_index', 1)
            day_range_display = f"{DAY_NAMES_FR[start_idx]} - {DAY_NAMES_FR[end_idx]}"
            
            embed = Embed(
                title=f"📅 Schedule Configuration for {config.grade_level}",
                color=discord.Color.blue()
            )
            embed.add_field(name="Channel ID", value=str(config.channel_id), inline=False)
            embed.add_field(name="Grade Level", value=config.grade_level, inline=False)
            embed.add_field(name="Spreadsheet URL", value=config.spreadsheet_url, inline=False)
            embed.add_field(name="GID", value=config.gid, inline=False)
            embed.add_field(
                name="Classes per Day",
                value=str(getattr(config, 'classes_per_day', 2)),
                inline=False
            )
            embed.add_field(
                name="Day Range",
                value=day_range_display,
                inline=False
            )
            embed.add_field(
                name="Message ID",
                value=str(config.message_id) if config.message_id else "Not set yet",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @ui.button(label="Delete Configuration", style=ButtonStyle.red)
    async def delete_config(self, interaction: Interaction, button: ui.Button):
        from db import AsyncSessionLocal
        
        async with AsyncSessionLocal() as session:
            # Get config for this channel
            result = await session.execute(
                select(ScheduleChannelConfig).where(
                    ScheduleChannelConfig.channel_id == interaction.channel_id
                )
            )
            config = result.scalar_one_or_none()
            
            if not config:
                await interaction.response.send_message(
                    "❌ This channel is not configured for schedule display.",
                    ephemeral=True
                )
                return
            
            # Confirmation view
            confirm_view = ui.View(timeout=60)
            confirm_button = ui.Button(label="Confirm Delete", style=ButtonStyle.danger)
            cancel_button = ui.Button(label="Cancel", style=ButtonStyle.secondary)
            
            async def confirm_callback(confirm_interaction: Interaction):
                # Delete the schedule message if it exists
                if config.message_id:
                    try:
                        channel = interaction.guild.get_channel(config.channel_id)
                        if channel:
                            message = await channel.fetch_message(config.message_id)
                            await message.delete()
                    except:
                        pass  # Message might already be deleted
                
                await session.delete(config)
                await session.commit()
                
                await confirm_interaction.response.edit_message(
                    content=f"✅ Schedule configuration for {config.grade_level} has been deleted.",
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
                title="⚠️ Confirm Configuration Deletion",
                description=f"Are you sure you want to delete the schedule configuration for **{config.grade_level}**?\n\n"
                           f"This will remove the schedule message and stop automatic updates.\n\n"
                           f"**This action cannot be undone.**",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, view=confirm_view, ephemeral=True)


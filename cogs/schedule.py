import discord
from discord.ext import commands, tasks
from discord import app_commands, Interaction, Embed, Color
from sqlalchemy import select
import aiohttp
import csv
import io
import locale
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List, Tuple

from db import AsyncSessionLocal, init_db
from db.models import ScheduleChannelConfig
from ui.schedule import ScheduleManagementView
from utils import ROLE_NOTABLE, ROLE_MANAGER

# Set French locale for date formatting
try:
    locale.setlocale(locale.LC_TIME, 'fr_FR.UTF-8')
except (locale.Error, ValueError):
    try:
        locale.setlocale(locale.LC_TIME, 'fr_FR')
    except (locale.Error, ValueError):
        pass  # Fallback to default if French locale not available


async def get_schedule_data(spreadsheet_url: str, gid: str) -> List[List[str]]:
    """
    Fetch schedule data from Google Sheets.
    
    Args:
        spreadsheet_url: The full Google Sheets URL
        gid: The sheet ID (gid parameter)
    
    Returns:
        List of rows from the spreadsheet
    """
    # Extract spreadsheet ID from URL
    spreadsheet_id = None
    if '/d/' in spreadsheet_url:
        try:
            spreadsheet_id = spreadsheet_url.split('/d/')[1].split('/')[0]
        except (IndexError, AttributeError):
            raise ValueError("Could not extract spreadsheet ID from URL")
    
    if not spreadsheet_id:
        raise ValueError("Invalid spreadsheet URL format")
    
    # Construct CSV export URL
    export_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?format=csv&gid={gid}"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(export_url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                response.raise_for_status()
                data = await response.text()
                reader = list(csv.reader(io.StringIO(data)))
                
                # Return the relevant rows (skip header rows, adjust based on sheet structure)
                # This may need adjustment based on the actual sheet structure
                return reader[8:92] + reader[102:] if len(reader) > 102 else reader
    
    except aiohttp.ClientError as e:
        raise Exception(f"Failed to fetch schedule: {str(e)}")
    except Exception as e:
        raise Exception(f"Failed to fetch schedule: {str(e)}")


def filter_schedule_for_week(schedule_data: List[List[str]], classes_per_day: int = 2) -> Tuple[List[List[str]], bool]:
    """
    Filter schedule data to get the current or next week.
    
    Args:
        schedule_data: Raw schedule data from spreadsheet
        classes_per_day: Number of time slots per day (2 for M1, 3 for M2)
    
    Returns:
        Tuple of (filtered schedule for current week, whether week was updated)
    """
    today = datetime.today()
    weekday = today.weekday()  # 0 = Monday, 6 = Sunday
    
    # Calculate start of the week (Monday)
    start_of_week = today - timedelta(days=weekday)
    week_updated = False
    days = 2  # Number of days to show in the week (typically Monday and Tuesday)
    
    # If we're past Wednesday (day 2), show next week
    if weekday > 2:
        start_of_week = start_of_week + timedelta(days=7)
        week_updated = True
    
    # Calculate number of rows based on classes per day
    # Each class has 3 rows: course name, teacher, room
    rows_per_week = 1 + (classes_per_day * 3)  # 1 row for dates + (classes * 3 rows each)
    
    # Search for the week in the schedule data
    for i in range(0, len(schedule_data), rows_per_week):
        try:
            # Try to parse the date in the first column (assuming it's in DD/MM format)
            if len(schedule_data[i]) > 1 and schedule_data[i][1]:
                date_str = schedule_data[i][1]
                date = datetime.strptime(date_str, "%d/%m").replace(year=today.year)
                
                # Check if this is the week we're looking for
                if date.date() == start_of_week.date():
                    # Format the dates with full day names
                    schedule_data[i][1] = date.strftime("%A %d %B %Y").capitalize()
                    
                    # Format the next few days
                    for j in range(2, days + 2):
                        if j < len(schedule_data[i]) and schedule_data[i][j]:
                            try:
                                day_date = datetime.strptime(schedule_data[i][j], "%d/%m").replace(year=today.year)
                                schedule_data[i][j] = day_date.strftime("%A %d %B %Y").capitalize()
                            except:
                                pass
                    
                    # Return the rows for this week
                    return [row[:days + 2] for row in schedule_data[i:i + rows_per_week]], week_updated
        
        except (ValueError, IndexError):
            continue
    
    return [], week_updated


def format_schedule(schedule_data: List[List[str]], classes_per_day: int = 2) -> str:
    """
    Format schedule data into a nice Discord message.
    
    Args:
        schedule_data: Filtered schedule data for the week
        classes_per_day: Number of time slots per day (2 for M1, 3 for M2)
    
    Returns:
        Formatted string for Discord message
    """
    # Minimum rows: 1 (dates) + classes_per_day * 3 (course, teacher, room for each class)
    min_rows = 1 + (classes_per_day * 3)
    
    if not schedule_data or len(schedule_data) < min_rows:
        return "❌ Aucun emploi du temps disponible pour cette semaine."
    
    formatted_parts = []
    
    # Process each day (columns 1+)
    for j in range(1, len(schedule_data[0])):
        try:
            day_name = schedule_data[0][j]
            day_classes = []
            
            # Process each class time slot
            for class_idx in range(classes_per_day):
                # Calculate row indices for this class (each class has 3 rows: course, teacher, room)
                course_row = 1 + (class_idx * 3)
                teacher_row = course_row + 1
                room_row = course_row + 2
                
                # Get class info
                course = schedule_data[course_row][j] if len(schedule_data[course_row]) > j else ""
                teacher = schedule_data[teacher_row][j] if len(schedule_data[teacher_row]) > j else ""
                room = schedule_data[room_row][j] if len(schedule_data[room_row]) > j else ""
                
                # Get label from first column (e.g., "Matin", "Après-midi", "Soir")
                label = schedule_data[course_row][0] if len(schedule_data[course_row]) > 0 else f"Cours {class_idx + 1}"
                
                # Format class text
                class_text = f"{label}: {course}" if course else f"{label}: -"
                if teacher:
                    class_text += f" ({teacher})"
                if room:
                    class_text += f" -> Salle {room}"
                
                day_classes.append(class_text)
            
            # Combine all classes for this day
            formatted_parts.append(f"**{day_name}**\n```{'\\n'.join(day_classes)}```")
        
        except IndexError:
            continue
    
    return '\n'.join(formatted_parts) if formatted_parts else "❌ Erreur de formatage de l'emploi du temps."


def detect_changes(current_data: List[List[str]], previous_hash: Optional[str]) -> Tuple[List[str], str]:
    """
    Detect changes in the schedule.
    
    Args:
        current_data: Current schedule data
        previous_hash: Hash of the previous schedule
    
    Returns:
        Tuple of (list of changes, current hash)
    """
    # Create hash of current data
    current_str = str(current_data)
    current_hash = hashlib.md5(current_str.encode()).hexdigest()
    
    # If no previous hash or hashes match, no changes
    if not previous_hash or current_hash == previous_hash:
        return [], current_hash
    
    # If hashes differ, there are changes (we'll return a generic message)
    changes = ["📋 L'emploi du temps a été mis à jour"]
    
    return changes, current_hash


async def update_schedule_for_channel(bot: commands.Bot, session, config: ScheduleChannelConfig):
    """
    Update the schedule for a specific channel.
    
    Args:
        bot: Discord bot instance
        session: Database session
        config: Schedule channel configuration
    """
    try:
        # Get the channel
        channel = bot.get_channel(config.channel_id)
        if not channel:
            print(f"Channel {config.channel_id} not found for {config.grade_level}")
            return
        
        # Fetch schedule data
        schedule_data = await get_schedule_data(config.spreadsheet_url, config.gid)
        
        # Get classes per day from config (default to 2 if not set)
        classes_per_day = getattr(config, 'classes_per_day', 2)
        
        # Filter for current week
        filtered_data, week_updated = filter_schedule_for_week(schedule_data, classes_per_day)
        
        if not filtered_data:
            print(f"No schedule data found for {config.grade_level}")
            return
        
        # Detect changes
        changes, current_hash = detect_changes(filtered_data, config.last_schedule_hash)
        
        # Format the schedule
        schedule_message = format_schedule(filtered_data, classes_per_day)
        
        # Create or update the message
        message_updated = False
        
        if config.message_id:
            try:
                message = await channel.fetch_message(config.message_id)
                await message.edit(content=schedule_message)
                message_updated = True
            except discord.NotFound:
                # Message was deleted, create new one
                message = await channel.send(schedule_message)
                config.message_id = message.id
                message_updated = True
            except Exception as e:
                print(f"Error editing message for {config.grade_level}: {e}")
        else:
            # No message ID stored, create new message
            message = await channel.send(schedule_message)
            config.message_id = message.id
            message_updated = True
        
        # Send notification for changes (but not on week updates)
        if changes and not week_updated and config.last_schedule_hash is not None:
            notification = "📋 **Modifications de l'emploi du temps** :\n" + "\n".join(changes)
            await channel.send(notification + "\n||@everyone||", delete_after=3600)
        
        # Update the hash in database
        if message_updated:
            config.last_schedule_hash = current_hash
            await session.commit()
    
    except Exception as e:
        print(f"Error updating schedule for {config.grade_level}: {e}")


class Schedule(commands.Cog):
    """Cog for managing course schedules."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.update_all_schedules.start()
    
    async def cog_load(self):
        """Initialize database when cog loads."""
        await init_db()
    
    def cog_unload(self):
        """Stop the update task when cog unloads."""
        self.update_all_schedules.cancel()
    
    @app_commands.command(
        name="schedule",
        description="Manage schedule channel configuration (Admin/Manager only)."
    )
    @app_commands.checks.has_any_role(ROLE_MANAGER.id, ROLE_NOTABLE.id)
    async def schedule(self, interaction: Interaction):
        """Open schedule management panel."""
        view = ScheduleManagementView()
        embed = Embed(
            title="📅 Schedule Management",
            description="Configure and manage course schedules for M1/M2 channels.",
            color=Color.blue()
        )
        embed.add_field(
            name="Available Actions",
            value="• **Setup New Channel** - Configure this channel for schedule display\n"
                  "• **Edit Configuration** - Update spreadsheet URL or GID\n"
                  "• **Force Refresh** - Manually update the schedule\n"
                  "• **View Configuration** - See current settings\n"
                  "• **Delete Configuration** - Remove schedule from this channel",
            inline=False
        )
        embed.set_footer(text="Schedules update automatically every 15 minutes")
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @tasks.loop(minutes=15)
    async def update_all_schedules(self):
        """Update all configured schedule channels."""
        async with AsyncSessionLocal() as session:
            # Get all schedule configurations
            result = await session.execute(select(ScheduleChannelConfig))
            configs = result.scalars().all()
            
            for config in configs:
                await update_schedule_for_channel(self.bot, session, config)
    
    @update_all_schedules.before_loop
    async def before_update_all_schedules(self):
        """Wait until the bot is ready before starting the update task."""
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(Schedule(bot))

import os
from discord.ext import commands, tasks
from discord import app_commands, Interaction, Embed, Color, TextChannel
from sqlalchemy import select
from datetime import datetime, timedelta
from typing import Optional, List

from db import AsyncSessionLocal, init_db
from db.models import GradeChannelConfig, Course, Assignment
from utils import ROLE_NOTABLE, ROLE_MANAGER, ROLE_M1, ROLE_M2, ROLE_FI, ROLE_FA


def get_role_mentions_for_channel(channel: TextChannel, grade_level: str) -> str:
    """
    Get the appropriate role mentions for a channel based on permissions.
    Check if FI or FA roles are explicitly DENIED view_channel permission.
    
    Args:
        channel: The Discord channel
        grade_level: The grade level (M1 or M2)
    
    Returns:
        String with role mentions
    """
    # Get grade role ID
    grade_role_map = {
        'M1': ROLE_M1.id,
        'M2': ROLE_M2.id,
    }
    grade_role_id = grade_role_map.get(grade_level.upper())
    
    # Check if FI role is explicitly DENIED view_channel permission
    fi_role = channel.guild.get_role(ROLE_FI.id)
    fi_denied = False
    if fi_role:
        fi_overwrite = channel.overwrites_for(fi_role)
        if fi_overwrite.view_channel is False:
            fi_denied = True
    
    # Check if FA role is explicitly DENIED view_channel permission
    fa_role = channel.guild.get_role(ROLE_FA.id)
    fa_denied = False
    if fa_role:
        fa_overwrite = channel.overwrites_for(fa_role)
        if fa_overwrite.view_channel is False:
            fa_denied = True
    
    # Logic:
    # - If FA is denied → mention only @FI
    # - If FI is denied → mention only @FA
    # - If both can access → mention only @M1
    if fa_denied and not fi_denied:
        # Only FI can access
        return f"<@&{ROLE_FI.id}>"
    elif fi_denied and not fa_denied:
        # Only FA can access
        return f"<@&{ROLE_FA.id}>"
    else:
        # Both can access (or both denied which is impossible) → mention grade level
        return f"<@&{grade_role_id}>" if grade_role_id else "||@everyone||"


def strip_emojis(text: str) -> str:
    """Remove emojis from text, keeping only letters, numbers, spaces, and dashes."""
    import re
    # Remove emojis and special characters, keep only alphanumeric, spaces, and dashes
    cleaned = re.sub(r'[^\w\s-]', '', text, flags=re.UNICODE)
    # Remove extra spaces
    cleaned = ' '.join(cleaned.split())
    return cleaned


async def update_homework_message(bot: commands.Bot, session, config: GradeChannelConfig):
    """Update the homework to-do list message in a channel."""
    import hashlib
    
    channel = bot.get_channel(config.channel_id)
    if not channel:
        return
    
    # Fetch all courses for this channel with their assignments
    result = await session.execute(
        select(Course).where(Course.channel_id == config.channel_id)
    )
    courses = result.scalars().all()
    
    # Create embeds for each course
    embeds = []
    content_parts = []  # Track content for change detection
    has_courses_with_assignments = False
    
    # Get grade level as string
    grade_level_str = str(config.grade_level.value) if hasattr(config.grade_level, 'value') else str(config.grade_level)
    
    if not courses:
        embed = Embed(
            title=f"📚 {grade_level_str} - Homework To-Do List",
            description="No courses have been added yet.",
            color=Color.blue()
        )
        embeds.append(embed)
        content_parts.append("no_courses")
    else:
        # Prepare courses with their assignments and earliest due date
        courses_with_assignments = []
        
        for course in courses:
            # Get active assignments sorted by due date
            active_assignments = [
                a for a in course.assignments 
                if a.status == 'active'
            ]
            
            # Skip courses with no active assignments
            if not active_assignments:
                continue
            
            # Sort assignments by due date (earliest first for processing)
            active_assignments.sort(key=lambda a: a.due_date)
            
            # Get earliest assignment for color determination and sorting
            earliest_assignment = active_assignments[0]
            
            courses_with_assignments.append((course, active_assignments, earliest_assignment))
        
        # Sort courses by earliest assignment due date (most urgent courses LAST)
        # Put courses with the nearest due dates later in the embeds list
        courses_with_assignments.sort(key=lambda x: x[2].due_date, reverse=True)
        
        # Create embeds for each course
        for course, active_assignments, earliest_assignment in courses_with_assignments:
            has_courses_with_assignments = True
            
            # Determine embed color based on earliest (most urgent) assignment
            now = datetime.now()
            time_until_earliest = earliest_assignment.due_date - now
            
            if time_until_earliest < timedelta(0):
                # Overdue - red
                embed_color = Color.red()
            elif time_until_earliest < timedelta(hours=24):
                # Due within 24 hours - dark orange/red
                embed_color = Color.dark_orange()
            elif time_until_earliest < timedelta(days=3):
                # Due within 3 days - orange
                embed_color = Color.orange()
            elif time_until_earliest < timedelta(days=7):
                # Due within 7 days - yellow/gold
                embed_color = Color.gold()
            else:
                # More than 7 days - green
                embed_color = Color.green()
            
            # Get course channel name (without emojis)
            channel_name = ""
            if course.course_channel_id:
                course_channel = bot.get_channel(course.course_channel_id)
                if course_channel:
                    channel_name = f" ({strip_emojis(course_channel.name)})"
            
            course_embed = Embed(
                title=f"🎓 {course.name.upper()}{channel_name}",
                color=embed_color
            )
            
            # Reverse assignments so most urgent is LAST (bottom)
            for assignment in reversed(active_assignments):
                # Format the field value
                field_value = ""
                
                if assignment.description:
                    field_value += f"\u200b\n{assignment.description}\n"
                
                # Format due date as Discord timestamp
                timestamp = int(assignment.due_date.timestamp())
                field_value += f"📅 Due: <t:{timestamp}:F> (<t:{timestamp}:R>)"
                
                if assignment.modality:
                    field_value += f"\n\u200b\n📝 Modality: {assignment.modality}"
                
                # Check if overdue
                if assignment.due_date < datetime.now():
                    field_name = f"⚠️ {assignment.title} (OVERDUE)"
                else:
                    # Check if due soon
                    time_until_due = assignment.due_date - datetime.now()
                    if time_until_due < timedelta(days=1):
                        field_name = f"🔴 {assignment.title}"
                    elif time_until_due < timedelta(days=7):
                        field_name = f"🟡 {assignment.title}"
                    else:
                        field_name = f"📝 {assignment.title}"
                
                course_embed.add_field(
                    name=f"\u200b\n\u200b\n__{field_name}__",
                    value=f"\u200b\n{field_value}",
                    inline=False
                )
                
                # Track content for change detection including due date/modality/description
                # Include stable due_date timestamp to ensure edits trigger updates
                due_ts = int(assignment.due_date.timestamp()) if assignment.due_date else 0
                modality_part = assignment.modality or ""
                # Keep description short in hash to avoid excessive size but still detect changes
                desc_part = (assignment.description or "")[:100]
                content_parts.append(
                    f"{course.name}:{assignment.id}:{assignment.title}:{assignment.status}:{due_ts}:{modality_part}:{desc_part}"
                )
            
            embeds.append(course_embed)
    
    # Only add footer if there are course embeds
    if not embeds:
        # No assignments at all, don't send anything
        return
    
    # Add footer embed
    footer_embed = Embed(
        description="\u200b\n**Color Legend:**\n"
                    "🔴 Red = Overdue\n"
                    "🟠 Dark Orange = Due within 24h\n"
                    "🟠 Orange = Due within 3 days\n"
                    "🟡 Gold = Due within 7 days\n"
                    "🟢 Green = More than 7 days\n\n"
                    "**Assignment Icons:**\n"
                    "⚠️ Overdue | 🔴 < 24h | 🟡 < 7d | 📝 Active",
        color=Color.light_gray()
    )
    
    # Compute content hash to detect actual changes
    content_hash = hashlib.md5("".join(content_parts).encode()).hexdigest()
    
    # Check if content actually changed by comparing with stored hash
    content_changed = True
    if hasattr(config, 'content_hash') and config.content_hash:
        content_changed = (config.content_hash != content_hash)
    
    # Only update the message if content actually changed
    if content_changed:
        # Update timestamp
        footer_embed.set_footer(text=f"Last updated: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        embeds.append(footer_embed)
        
        # Update or create message (no view/buttons - display only)
        try:
            if config.message_id:
                try:
                    message = await channel.fetch_message(config.message_id)
                    await message.edit(embeds=embeds)
                except:
                    # Message was deleted, create new one
                    message = await channel.send(embeds=embeds)
                    config.message_id = message.id
                    await session.commit()
            else:
                message = await channel.send(embeds=embeds)
                config.message_id = message.id
                await session.commit()
            
            # Store the new content hash
            config.content_hash = content_hash
            await session.commit()
            
        except Exception as e:
            print(f"Error updating homework message: {e}")
    # If content hasn't changed, don't update the message at all


class Homework(commands.Cog):
    """Cog for managing homework to-do lists."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.check_reminders.start()
    
    async def cog_load(self):
        """Initialize database when cog loads."""
        await init_db()
    
    def cog_unload(self):
        """Stop the reminder task when cog unloads."""
        self.check_reminders.cancel()
    
    @app_commands.command(
        name="manage_homework",
        description="Homework management dashboard (Admin/Manager only)."
    )
    @app_commands.checks.has_any_role(ROLE_MANAGER.id, ROLE_NOTABLE.id)
    async def manage_homework(self, interaction: Interaction):
        """Open homework management dashboard."""
        from ui.homework import HomeworkAdminPanel
        
        # Use the channel where the command was typed
        view = HomeworkAdminPanel(interaction.channel_id)
        embed = Embed(
            title="📚 Homework Management Dashboard",
            description=f"Managing homework for <#{interaction.channel_id}>\n\nSelect an action from the menu below:",
            color=Color.blue()
        )
        embed.add_field(
            name="Available Actions",
            value="• Setup this channel for homework tracking\n"
                  "• Add/edit/delete assignments\n"
                  "• Add/edit/delete courses\n"
                  "• Refresh to-do list\n"
                  "• View statistics\n"
                  "• Remove channel configuration",
            inline=False
        )
        embed.set_footer(text="All actions apply to this channel")
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @tasks.loop(minutes=1)
    async def check_reminders(self):
        """Check for assignments that need reminders."""
        async with AsyncSessionLocal() as session:
            # Get all active assignments
            result = await session.execute(
                select(Assignment).where(Assignment.status == 'active')
            )
            assignments = result.scalars().all()
            
            now = datetime.now()
            
            for assignment in assignments:
                time_until_due = assignment.due_date - now
                
                # Check if overdue by more than 3 hours - delete from display
                if time_until_due < timedelta(hours=-3):
                    assignment.status = 'past_due'
                    continue
                
                # Check reminder thresholds
                # Remind at: 1 week, 1 day, 1 hour, 10 minutes before, and AT DUE TIME
                # Windows are wide enough to catch the reminder (task runs every minute)
                
                reminder_windows = [
                    (timedelta(days=7, seconds=-30), timedelta(days=7, seconds=30), "1 week"),
                    (timedelta(days=1, seconds=-30), timedelta(days=1, seconds=30), "1 day"),
                    (timedelta(hours=1, seconds=-30), timedelta(hours=1, seconds=30), "1 hour"),
                    (timedelta(minutes=10, seconds=-30), timedelta(minutes=10, seconds=30), "10 minutes"),
                    (timedelta(seconds=-30), timedelta(seconds=30), "NOW - DUE!"),
                ]
                
                for threshold_min, threshold_max, label in reminder_windows:
                    if threshold_min <= time_until_due <= threshold_max:
                        # Send reminder
                        result = await session.execute(
                            select(Course).where(Course.id == assignment.course_id)
                        )
                        course = result.scalar_one_or_none()
                        
                        if course:
                            # Send reminder to the homework to-do channel
                            channel = self.bot.get_channel(course.channel_id)
                            if channel:
                                # Get the grade level from the course's grade channel config
                                result_grade = await session.execute(
                                    select(GradeChannelConfig).where(
                                        GradeChannelConfig.channel_id == course.channel_id
                                    )
                                )
                                grade_config = result_grade.scalar_one_or_none()
                                grade_level = str(grade_config.grade_level.value) if grade_config else "M1"
                                
                                # Get appropriate role mentions based on course channel permissions
                                # Use course_channel_id if set, otherwise fall back to homework channel
                                permission_channel_id = course.course_channel_id if course.course_channel_id else course.channel_id
                                permission_channel = self.bot.get_channel(permission_channel_id)
                                
                                if permission_channel:
                                    role_mentions = get_role_mentions_for_channel(permission_channel, grade_level)
                                else:
                                    # Fall back to mentioning the grade role only
                                    grade_role_map = {'M1': ROLE_M1.id, 'M2': ROLE_M2.id}
                                    grade_role_id = grade_role_map.get(grade_level)
                                    role_mentions = f"<@&{grade_role_id}>" if grade_role_id else "||@everyone||"
                                
                                # Build plain text message for smartphone notifications
                                message_content = f"{role_mentions}\n\n"
                                
                                # Customize message based on urgency
                                if label == "NOW - DUE!":
                                    message_content += f"🔴 **Assignment Due NOW!**\n\n"
                                elif label == "10 minutes":
                                    message_content += f"⏰ **Assignment Due in 10 Minutes!**\n\n"
                                elif label == "1 hour":
                                    message_content += f"⏰ **Assignment Due in 1 Hour!**\n\n"
                                elif label == "1 day":
                                    message_content += f"📅 **Assignment Due Tomorrow!**\n\n"
                                elif label == "1 week":
                                    message_content += f"📆 **Assignment Due in 1 Week!**\n\n"
                                
                                message_content += f"📝 **{assignment.title}** for {course.name}\n"
                                message_content += f"📅 Due: <t:{int(assignment.due_date.timestamp())}:F>\n"
                                
                                if assignment.description:
                                    # Limit description to 200 chars for cleaner notification
                                    desc = assignment.description[:200]
                                    if len(assignment.description) > 200:
                                        desc += "..."
                                    message_content += f"\n{desc}\n"
                                
                                if assignment.modality:
                                    message_content += f"\n📝 Modality: {assignment.modality}"
                                
                                # Send plain text message (better for smartphone notifications)
                                # Delete message after 10 minutes
                                await channel.send(message_content, delete_after=600)
                        
                        # Break after sending reminder to avoid multiple notifications
                        break
            
            # Commit status changes
            await session.commit()
            
            # Update all homework messages
            result = await session.execute(select(GradeChannelConfig))
            configs = result.scalars().all()
            
            for config in configs:
                await update_homework_message(self.bot, session, config)
    
    @check_reminders.before_loop
    async def before_check_reminders(self):
        """Wait until the bot is ready before starting the reminder task."""
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(Homework(bot))


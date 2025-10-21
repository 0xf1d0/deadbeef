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
        # Create an embed for each course (only if it has active assignments)
        for course in sorted(courses, key=lambda c: c.name):
            # Get active assignments sorted by due date
            active_assignments = [
                a for a in course.assignments 
                if a.status == 'active'
            ]
            active_assignments.sort(key=lambda a: a.due_date)
            
            # Skip courses with no active assignments
            if not active_assignments:
                continue
            
            has_courses_with_assignments = True
            
            course_embed = Embed(
                title=f"🎓 {course.name.upper()}",
                color=Color.green()
            )
            
            for assignment in active_assignments:
                # Format the field value
                field_value = ""
                
                if assignment.description:
                    field_value += f"_{assignment.description}_\n"
                
                # Format due date as Discord timestamp
                timestamp = int(assignment.due_date.timestamp())
                field_value += f"📅 Due: <t:{timestamp}:F> (<t:{timestamp}:R>)"
                
                if assignment.modality:
                    field_value += f"\n📝 Modality: {assignment.modality}"
                
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
                    name=field_name,
                    value=field_value,
                    inline=False
                )
                
                # Track content for change detection (exclude timestamps for relative changes)
                content_parts.append(f"{course.name}:{assignment.id}:{assignment.title}:{assignment.status}")
            
            embeds.append(course_embed)
    
    # Only add footer if there are course embeds
    if not embeds:
        # No assignments at all, don't send anything
        return
    
    # Add footer embed
    footer_embed = Embed(
        description="\u200b\n**Legend:**\n🔴 Due within 24 hours\n🟡 Due within 7 days\n📝 Active assignment\n⚠️ Overdue",
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
        print("[HOMEWORK] Cog initialized, starting reminder task...")
        self.check_reminders.start()
    
    async def cog_load(self):
        """Initialize database when cog loads."""
        await init_db()
        print("[HOMEWORK] Database initialized")
    
    def cog_unload(self):
        """Stop the reminder task when cog unloads."""
        self.check_reminders.cancel()
        print("[HOMEWORK] Cog unloaded, reminder task cancelled")
    
    @app_commands.command(
        name="homework",
        description="Homework management dashboard (Admin/Manager only)."
    )
    @app_commands.checks.has_any_role(ROLE_MANAGER.id, ROLE_NOTABLE.id)
    async def homework(self, interaction: Interaction):
        """Open homework management dashboard."""
        from ui.homework import HomeworkAdminPanel
        
        view = HomeworkAdminPanel()
        embed = Embed(
            title="📚 Homework Management Dashboard",
            description="Select an action from the menu below to manage homework assignments and courses.",
            color=Color.blue()
        )
        embed.add_field(
            name="Available Actions",
            value="• Setup new homework channel\n"
                  "• Add/edit/delete assignments\n"
                  "• Add/edit/delete courses\n"
                  "• Refresh to-do lists\n"
                  "• View statistics",
            inline=False
        )
        embed.set_footer(text="Use the select menu below to get started")
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @app_commands.command(
        name="test_reminder",
        description="Test reminder system (Admin/Manager only)."
    )
    @app_commands.checks.has_any_role(ROLE_MANAGER.id, ROLE_NOTABLE.id)
    async def test_reminder(self, interaction: Interaction):
        """Manually trigger reminder check for testing."""
        await interaction.response.defer(ephemeral=True)
        
        async with AsyncSessionLocal() as session:
            # Get all active assignments
            result = await session.execute(
                select(Assignment).where(Assignment.status == 'active')
            )
            assignments = result.scalars().all()
            
            if not assignments:
                await interaction.followup.send("❌ No active assignments found.", ephemeral=True)
                return
            
            now = datetime.now()
            report = []
            report.append(f"**Found {len(assignments)} active assignment(s):**\n")
            
            for assignment in assignments:
                time_until_due = assignment.due_date - now
                days = time_until_due.days
                hours = time_until_due.seconds // 3600
                minutes = (time_until_due.seconds % 3600) // 60
                
                result = await session.execute(
                    select(Course).where(Course.id == assignment.course_id)
                )
                course = result.scalar_one_or_none()
                course_name = course.name if course else "Unknown"
                
                # Get grade level and channel info
                if course:
                    result_grade = await session.execute(
                        select(GradeChannelConfig).where(
                            GradeChannelConfig.channel_id == course.channel_id
                        )
                    )
                    grade_config = result_grade.scalar_one_or_none()
                    grade_level = str(grade_config.grade_level.value) if grade_config else "N/A"
                    
                    # Get role mentions
                    permission_channel_id = course.course_channel_id if course.course_channel_id else course.channel_id
                    permission_channel = self.bot.get_channel(permission_channel_id)
                    
                    if permission_channel:
                        role_mentions = get_role_mentions_for_channel(permission_channel, grade_level)
                        channel_info = f"Channel: {permission_channel.name}"
                    else:
                        role_mentions = "No channel found"
                        channel_info = "Channel: Not found"
                else:
                    grade_level = "N/A"
                    role_mentions = "N/A"
                    channel_info = "No course"
                
                status_icon = "✅" if time_until_due > timedelta(0) else "⚠️"
                report.append(
                    f"{status_icon} **{assignment.title}**\n"
                    f"  • Course: {course_name}\n"
                    f"  • Grade: {grade_level}\n"
                    f"  • Due: {days}d {hours}h {minutes}m\n"
                    f"  • {channel_info}\n"
                    f"  • Roles: {role_mentions}\n"
                )
            
            embed = Embed(
                title="📊 Reminder System Test",
                description="\n".join(report),
                color=Color.blue()
            )
            embed.set_footer(text="Reminder windows: 7 days, 1 day, 1 hour (±30 min)")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
    
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
            print(f"[HOMEWORK] {now.strftime('%H:%M:%S')} - Checking {len(assignments)} active assignment(s) for reminders")
            
            for assignment in assignments:
                time_until_due = assignment.due_date - now
                
                # Check if overdue by more than 3 hours - delete from display
                if time_until_due < timedelta(hours=-3):
                    assignment.status = 'past_due'
                    continue
                
                # Check reminder thresholds
                # Remind at: 7 days, 1 day, 1 hour before, and AT DUE TIME
                # To avoid duplicate reminders, we'll check if we're within a small window
                
                reminder_windows = [
                    (timedelta(days=7), timedelta(days=7, minutes=30), "1 week"),
                    (timedelta(days=1), timedelta(days=1, minutes=30), "1 day"),
                    (timedelta(hours=1), timedelta(hours=1, minutes=30), "1 hour"),
                    (timedelta(minutes=-5), timedelta(minutes=5), "NOW - DUE!"),  # At due time (±5 min)
                ]
                
                for threshold, window, label in reminder_windows:
                    if threshold <= time_until_due < window:
                        print(f"[HOMEWORK] ⏰ REMINDER TRIGGERED for '{assignment.title}' - Due in {label}!")
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
                                
                                embed = Embed(
                                    title=f"⏰ Assignment Reminder",
                                    description=f"The assignment **{assignment.title}** for {course.name} is due in **{label}**!",
                                    color=Color.orange()
                                )
                                embed.add_field(
                                    name="Due Date",
                                    value=f"<t:{int(assignment.due_date.timestamp())}:F>",
                                    inline=False
                                )
                                if assignment.description:
                                    embed.add_field(
                                        name="Description",
                                        value=assignment.description[:500],
                                        inline=False
                                    )
                                if assignment.modality:
                                    embed.add_field(
                                        name="Modality",
                                        value=assignment.modality,
                                        inline=False
                                    )
                                
                                # Send to homework to-do channel with role mentions
                                await channel.send(role_mentions, embed=embed)
                                print(f"[HOMEWORK] ✅ Reminder sent to {channel.name} - Mentioned: {role_mentions}")
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
        print("[HOMEWORK] Waiting for bot to be ready...")
        await self.bot.wait_until_ready()
        print("[HOMEWORK] Bot ready! Starting reminder checks every minute.")


async def setup(bot: commands.Bot):
    await bot.add_cog(Homework(bot))


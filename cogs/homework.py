import os
from discord.ext import commands, tasks
from discord import app_commands, Interaction, Embed, Color, TextChannel
from sqlalchemy import select
from datetime import datetime, timedelta
from typing import Optional, List

from db import AsyncSessionLocal, init_db
from db.models import GradeChannelConfig, Course, Assignment
from utils import ROLE_NOTABLE, ROLE_MANAGER, ROLE_M1, ROLE_M2, ROLE_FI, ROLE_FA


def get_roles_with_channel_access(channel: TextChannel) -> List[int]:
    """
    Get the list of role IDs that have access to view a channel.
    
    Args:
        channel: The Discord channel to check
    
    Returns:
        List of role IDs that have view_channel permission
    """
    roles_with_access = []
    
    # Check permission overwrites for specific roles
    role_ids_to_check = {
        'M1': ROLE_M1.id,
        'M2': ROLE_M2.id,
        'FI': ROLE_FI.id,
        'FA': ROLE_FA.id,
    }
    
    for role_name, role_id in role_ids_to_check.items():
        # Get the role object from the guild
        role = channel.guild.get_role(role_id)
        if not role:
            continue
        
        # Check if there's an overwrite for this role
        overwrite = channel.overwrites_for(role)
        
        # Check view_channel permission
        # If explicitly allowed (True), or not explicitly denied (None) and @everyone can see
        if overwrite.view_channel is True:
            roles_with_access.append(role_id)
        elif overwrite.view_channel is None:
            # Check @everyone permissions
            everyone_role = channel.guild.default_role
            everyone_overwrite = channel.overwrites_for(everyone_role)
            if everyone_overwrite.view_channel is not False:
                # If @everyone can view or it's not explicitly denied, and the role isn't denied
                roles_with_access.append(role_id)
    
    return roles_with_access


def get_role_mentions_for_channel(channel: TextChannel, grade_level: str) -> str:
    """
    Get the appropriate role mentions for a channel based on permissions.
    
    Args:
        channel: The Discord channel
        grade_level: The grade level (M1 or M2)
    
    Returns:
        String with role mentions (e.g., "<@&M1_ID> <@&FI_ID>")
    """
    accessible_role_ids = get_roles_with_channel_access(channel)
    
    # Determine which grade role to mention
    grade_role_map = {
        'M1': ROLE_M1.id,
        'M2': ROLE_M2.id,
    }
    
    mentions = []
    
    # Add grade level mention if accessible
    grade_role_id = grade_role_map.get(grade_level.upper())
    if grade_role_id and grade_role_id in accessible_role_ids:
        mentions.append(f"<@&{grade_role_id}>")
    
    # Add formation mentions (FI/FA) if accessible
    if ROLE_FI.id in accessible_role_ids:
        mentions.append(f"<@&{ROLE_FI.id}>")
    
    if ROLE_FA.id in accessible_role_ids:
        mentions.append(f"<@&{ROLE_FA.id}>")
    
    # If no specific roles found, fall back to @everyone
    if not mentions:
        return "||@everyone||"
    
    return " ".join(mentions)


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
    
    if not courses:
        embed = Embed(
            title=f"📚 {config.grade_level} - Homework To-Do List",
            description="No courses have been added yet.",
            color=Color.blue()
        )
        embeds.append(embed)
        content_parts.append("no_courses")
    else:
        # Add a header embed
        header_embed = Embed(
            title=f"📚 {config.grade_level} - Homework To-Do List",
            description=f"View all assignments and deadlines for {config.grade_level} courses.\n\u200b",
            color=Color.blue()
        )
        embeds.append(header_embed)
        
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
        
        # If no courses have active assignments, show a message
        if not has_courses_with_assignments:
            no_assignments_embed = Embed(
                description="✨ No active assignments at the moment!",
                color=Color.green()
            )
            embeds.append(no_assignments_embed)
            content_parts.append("no_active_assignments")
    
    # Add footer embed
    footer_embed = Embed(
        description="\u200b\n**Legend:**\n🔴 Due within 24 hours\n🟡 Due within 7 days\n📝 Active assignment\n⚠️ Overdue",
        color=Color.light_gray()
    )
    
    # Compute content hash to detect actual changes
    content_hash = hashlib.md5("".join(content_parts).encode()).hexdigest()
    
    # Check if content actually changed
    content_changed = True
    if config.message_id:
        try:
            message = await channel.fetch_message(config.message_id)
            # Check if we have stored hash in message footer (if it exists)
            if message.embeds and len(message.embeds) > 0:
                last_embed = message.embeds[-1]
                if last_embed.footer and last_embed.footer.text:
                    # Extract hash from footer if present
                    if "#" in last_embed.footer.text:
                        old_hash = last_embed.footer.text.split("#")[-1]
                        content_changed = (old_hash != content_hash)
        except:
            pass
    
    # Only add timestamp if content changed
    if content_changed:
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
    except Exception as e:
        print(f"Error updating homework message: {e}")


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
                
                # Check if overdue
                if time_until_due < timedelta(0):
                    # Mark as past due
                    assignment.status = 'past_due'
                    continue
                
                # Check reminder thresholds
                # We'll use a simple approach: remind at 7 days, 1 day, and 1 hour
                # To avoid duplicate reminders, we'll check if we're within a small window
                
                reminder_windows = [
                    (timedelta(days=7), timedelta(days=7, minutes=30), "1 week"),
                    (timedelta(days=1), timedelta(days=1, minutes=30), "1 day"),
                    (timedelta(hours=1), timedelta(hours=1, minutes=30), "1 hour"),
                ]
                
                for threshold, window, label in reminder_windows:
                    if threshold <= time_until_due < window:
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
                                grade_level = grade_config.grade_level if grade_config else "M1"
                                
                                # Get appropriate role mentions based on course channel permissions
                                # Use course_channel_id if set, otherwise fall back to homework channel
                                permission_channel_id = course.course_channel_id if course.course_channel_id else course.channel_id
                                permission_channel = self.bot.get_channel(permission_channel_id)
                                
                                if permission_channel:
                                    role_mentions = get_role_mentions_for_channel(permission_channel, grade_level)
                                else:
                                    role_mentions = "||@everyone||"
                                
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
                                
                                await channel.send(role_mentions, embed=embed)
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


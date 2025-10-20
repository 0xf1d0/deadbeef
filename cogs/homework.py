import os
from discord.ext import commands, tasks
from discord import app_commands, Interaction, Embed, Color, TextChannel
from sqlalchemy import select
from datetime import datetime, timedelta
from typing import Optional

from db import AsyncSessionLocal, init_db
from db.models import GradeChannelConfig, Course, Assignment
from ui.homework import HomeworkMainView, AssignmentActionsView
from utils.utils import ROLE_NOTABLE, ROLE_MANAGER


async def update_homework_message(bot: commands.Bot, session, config: GradeChannelConfig):
    """Update the homework to-do list message in a channel."""
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
    
    if not courses:
        embed = Embed(
            title=f"📚 {config.grade_level} - Homework To-Do List",
            description="No courses have been added yet.\n\nUse the '📘 Manage Courses' button below to add courses.",
            color=Color.blue()
        )
        embeds.append(embed)
    else:
        # Add a header embed
        header_embed = Embed(
            title=f"📚 {config.grade_level} - Homework To-Do List",
            description=f"Track your assignments and deadlines for {config.grade_level} courses.\n\u200b",
            color=Color.blue()
        )
        embeds.append(header_embed)
        
        # Create an embed for each course
        for course in sorted(courses, key=lambda c: c.name):
            # Get active assignments sorted by due date
            active_assignments = [
                a for a in course.assignments 
                if a.status == 'active'
            ]
            active_assignments.sort(key=lambda a: a.due_date)
            
            course_embed = Embed(
                title=f"🎓 {course.name.upper()}",
                color=Color.green() if active_assignments else Color.greyple()
            )
            
            if not active_assignments:
                course_embed.description = "*No active assignments*"
            else:
                for assignment in active_assignments:
                    # Format the field value
                    field_value = ""
                    
                    if assignment.description:
                        field_value += f"_{assignment.description}_\n"
                    
                    # Format due date as Discord timestamp
                    timestamp = int(assignment.due_date.timestamp())
                    field_value += f"📅 Due: <t:{timestamp}:F> (<t:{timestamp}:R>)\n"
                    
                    if assignment.modality:
                        field_value += f"📝 Modality: {assignment.modality}\n"
                    
                    # Add action buttons mention
                    field_value += f"\n*ID: {assignment.id}* - Use buttons below to manage"
                    
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
            
            embeds.append(course_embed)
    
    # Add footer embed
    footer_embed = Embed(
        description="\u200b\n**Legend:**\n🔴 Due within 24 hours\n🟡 Due within 7 days\n📝 Active assignment\n⚠️ Overdue",
        color=Color.light_gray()
    )
    footer_embed.set_footer(text=f"Last updated: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    embeds.append(footer_embed)
    
    # Create the view
    view = HomeworkMainView()
    
    # Update or create message
    try:
        if config.message_id:
            try:
                message = await channel.fetch_message(config.message_id)
                await message.edit(embeds=embeds, view=view)
            except:
                # Message was deleted, create new one
                message = await channel.send(embeds=embeds, view=view)
                config.message_id = message.id
                await session.commit()
        else:
            message = await channel.send(embeds=embeds, view=view)
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
        name="setup_homework_channel",
        description="Set up this channel for homework tracking (Admin/Manager only)."
    )
    @app_commands.describe(grade_level="The grade level (e.g., M1, M2)")
    @app_commands.checks.has_any_role(ROLE_MANAGER.id, ROLE_NOTABLE.id)
    async def setup_homework_channel(self, interaction: Interaction, grade_level: str):
        """Set up a channel for homework tracking."""
        async with AsyncSessionLocal() as session:
            # Check if channel is already configured
            result = await session.execute(
                select(GradeChannelConfig).where(
                    GradeChannelConfig.channel_id == interaction.channel_id
                )
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                await interaction.response.send_message(
                    f"❌ This channel is already configured for {existing.grade_level}.",
                    ephemeral=True
                )
                return
            
            # Check if grade level is already used
            result = await session.execute(
                select(GradeChannelConfig).where(
                    GradeChannelConfig.grade_level == grade_level
                )
            )
            existing_grade = result.scalar_one_or_none()
            
            if existing_grade:
                await interaction.response.send_message(
                    f"❌ Grade level '{grade_level}' is already configured in another channel.",
                    ephemeral=True
                )
                return
            
            # Create configuration
            config = GradeChannelConfig(
                channel_id=interaction.channel_id,
                grade_level=grade_level
            )
            session.add(config)
            await session.commit()
            await session.refresh(config)
            
            # Send initial message
            await update_homework_message(self.bot, session, config)
            
            await interaction.response.send_message(
                f"✅ This channel is now set up for {grade_level} homework tracking!",
                ephemeral=True
            )
    
    @app_commands.command(
        name="assignment_actions",
        description="Manage a specific assignment (Notable/Manager only)."
    )
    @app_commands.describe(assignment_id="The ID of the assignment")
    @app_commands.checks.has_any_role(ROLE_MANAGER.id, ROLE_NOTABLE.id)
    async def assignment_actions(self, interaction: Interaction, assignment_id: int):
        """Show action buttons for an assignment."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Assignment).where(Assignment.id == assignment_id)
            )
            assignment = result.scalar_one_or_none()
            
            if not assignment:
                await interaction.response.send_message(
                    "❌ Assignment not found.",
                    ephemeral=True
                )
                return
            
            # Verify assignment belongs to this channel
            result = await session.execute(
                select(Course).where(Course.id == assignment.course_id)
            )
            course = result.scalar_one_or_none()
            
            if not course or course.channel_id != interaction.channel_id:
                await interaction.response.send_message(
                    "❌ Assignment not found in this channel.",
                    ephemeral=True
                )
                return
            
            view = AssignmentActionsView(assignment_id)
            embed = Embed(
                title=f"📝 {assignment.title}",
                description=f"**Course:** {course.name}\n"
                           f"**Due:** <t:{int(assignment.due_date.timestamp())}:F>\n"
                           f"**Status:** {assignment.status}",
                color=Color.blue()
            )
            
            if assignment.description:
                embed.add_field(name="Description", value=assignment.description, inline=False)
            
            if assignment.modality:
                embed.add_field(name="Modality", value=assignment.modality, inline=False)
            
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @tasks.loop(minutes=30)
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
                            channel = self.bot.get_channel(course.channel_id)
                            if channel:
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
                                
                                await channel.send("||@everyone||", embed=embed)
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


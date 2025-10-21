import discord
from discord import ui, ButtonStyle, TextStyle, Interaction, Embed, SelectOption, ChannelType
from typing import List, Optional
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import GradeChannelConfig, Course, Assignment


# ============================================================================
# Admin Management Interface
# ============================================================================

class HomeworkAdminPanel(ui.View):
    """Main admin panel for homework management with select menu."""
    
    def __init__(self):
        super().__init__(timeout=300)
        
        # Create select menu with all admin options
        options = [
            SelectOption(
                label="Setup Homework Channel",
                description="Configure a channel for homework tracking",
                value="setup",
                emoji="⚙️"
            ),
            SelectOption(
                label="Add Assignment",
                description="Create a new assignment",
                value="add_assignment",
                emoji="➕"
            ),
            SelectOption(
                label="Edit Assignment",
                description="Modify an existing assignment",
                value="edit_assignment",
                emoji="✏️"
            ),
            SelectOption(
                label="Delete Assignment",
                description="Remove an assignment",
                value="delete_assignment",
                emoji="🗑️"
            ),
            SelectOption(
                label="Add Course",
                description="Add a new course",
                value="add_course",
                emoji="📘"
            ),
            SelectOption(
                label="Edit Course",
                description="Modify an existing course",
                value="edit_course",
                emoji="📝"
            ),
            SelectOption(
                label="Delete Course",
                description="Remove a course",
                value="delete_course",
                emoji="❌"
            ),
            SelectOption(
                label="Refresh To-Do List",
                description="Update the homework message",
                value="refresh",
                emoji="🔄"
            ),
            SelectOption(
                label="View Statistics",
                description="Show homework statistics",
                value="stats",
                emoji="📊"
            ),
            SelectOption(
                label="Remove Channel Configuration",
                description="Delete a homework channel configuration",
                value="remove_channel",
                emoji="🗑️"
            ),
        ]
        
        select = ui.Select(
            placeholder="Select an action...",
            options=options,
            custom_id="homework_admin_select"
        )
        select.callback = self.action_selected
        self.add_item(select)
    
    async def action_selected(self, interaction: Interaction):
        """Handle admin action selection."""
        from db import AsyncSessionLocal
        
        action = self.children[0].values[0]
        
        if action == "setup":
            # Show channel select for setup
            view = SetupChannelSelectView()
            embed = Embed(
                title="⚙️ Setup Homework Channel",
                description="Select the channel where you want to display the homework to-do list:",
                color=discord.Color.blue()
            )
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        
        elif action == "add_assignment":
            # Show channel select to choose which homework channel
            view = SelectHomeworkChannelView(action="add_assignment")
            embed = Embed(
                title="➕ Add Assignment",
                description="Select the homework channel:",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        
        elif action == "edit_assignment":
            view = SelectHomeworkChannelView(action="edit_assignment")
            embed = Embed(
                title="✏️ Edit Assignment",
                description="Select the homework channel:",
                color=discord.Color.orange()
            )
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        
        elif action == "delete_assignment":
            view = SelectHomeworkChannelView(action="delete_assignment")
            embed = Embed(
                title="🗑️ Delete Assignment",
                description="Select the homework channel:",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        
        elif action == "add_course":
            view = SelectHomeworkChannelView(action="add_course")
            embed = Embed(
                title="📘 Add Course",
                description="Select the homework channel:",
                color=discord.Color.blurple()
            )
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        
        elif action == "edit_course":
            view = SelectHomeworkChannelView(action="edit_course")
            embed = Embed(
                title="📝 Edit Course",
                description="Select the homework channel:",
                color=discord.Color.blue()
            )
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        
        elif action == "delete_course":
            view = SelectHomeworkChannelView(action="delete_course")
            embed = Embed(
                title="❌ Delete Course",
                description="Select the homework channel:",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        
        elif action == "refresh":
            view = SelectHomeworkChannelView(action="refresh")
            embed = Embed(
                title="🔄 Refresh To-Do List",
                description="Select the homework channel to refresh:",
                color=discord.Color.greyple()
            )
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        
        elif action == "stats":
            # Show statistics
            async with AsyncSessionLocal() as session:
                result = await session.execute(select(GradeChannelConfig))
                configs = result.scalars().all()
                
                if not configs:
                    await interaction.response.send_message(
                        "❌ No homework channels configured yet.",
                        ephemeral=True
                    )
                    return
                
                embed = Embed(
                    title="📊 Homework Statistics",
                    description="Overview of homework channels:",
                    color=discord.Color.blue()
                )
                
                for config in configs:
                    channel = interaction.guild.get_channel(config.channel_id)
                    channel_name = channel.mention if channel else f"Unknown ({config.channel_id})"
                    
                    result = await session.execute(
                        select(Course).where(Course.channel_id == config.channel_id)
                    )
                    courses = result.scalars().all()
                    
                    total_assignments = 0
                    active_assignments = 0
                    for course in courses:
                        total_assignments += len(course.assignments)
                        active_assignments += len([a for a in course.assignments if a.status == 'active'])
                    
                    embed.add_field(
                        name=f"{config.grade_level} - {channel_name}",
                        value=f"📘 {len(courses)} course(s)\n"
                              f"📝 {active_assignments}/{total_assignments} active assignments",
                        inline=False
                    )
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
        
        elif action == "remove_channel":
            # Show channel select to remove configuration
            view = RemoveChannelSelectView()
            embed = Embed(
                title="🗑️ Remove Channel Configuration",
                description="Select the homework channel configuration to remove:",
                color=discord.Color.red()
            )
            embed.add_field(
                name="⚠️ Warning",
                value="This will remove the channel configuration and all associated courses and assignments from the database.",
                inline=False
            )
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class SetupChannelSelectView(ui.View):
    """View with channel select for homework setup."""
    
    def __init__(self):
        super().__init__(timeout=300)
        
        channel_select = ui.ChannelSelect(
            placeholder="Select a channel...",
            channel_types=[ChannelType.text],
            custom_id="setup_channel_select"
        )
        channel_select.callback = self.channel_selected
        self.add_item(channel_select)
    
    async def channel_selected(self, interaction: Interaction):
        """Handle channel selection for setup."""
        channel_id = self.children[0].values[0].id
        
        # Show grade level select
        view = GradeLevelSelectView(channel_id)
        embed = Embed(
            title="⚙️ Select Grade Level",
            description=f"Channel: <#{channel_id}>\n\nSelect the grade level for this homework channel:",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class GradeLevelSelectView(ui.View):
    """View for selecting grade level during setup."""
    
    def __init__(self, channel_id: int):
        super().__init__(timeout=300)
        self.channel_id = channel_id
        
        options = [
            SelectOption(label="M1", value="M1", emoji="1️⃣"),
            SelectOption(label="M2", value="M2", emoji="2️⃣"),
        ]
        
        select = ui.Select(placeholder="Select grade level...", options=options)
        select.callback = self.grade_selected
        self.add_item(select)
    
    async def grade_selected(self, interaction: Interaction):
        """Handle grade level selection."""
        from db import AsyncSessionLocal
        grade_level = self.children[0].values[0]
        
        async with AsyncSessionLocal() as session:
            # Check if channel already configured
            result = await session.execute(
                select(GradeChannelConfig).where(
                    GradeChannelConfig.channel_id == self.channel_id
                )
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                await interaction.response.send_message(
                    f"❌ This channel is already configured for {existing.grade_level}.",
                    ephemeral=True
                )
                return
            
            # Check if grade level already used
            result = await session.execute(
                select(GradeChannelConfig).where(
                    GradeChannelConfig.grade_level == grade_level
                )
            )
            existing_grade = result.scalar_one_or_none()
            
            if existing_grade:
                await interaction.response.send_message(
                    f"❌ {grade_level} is already configured in <#{existing_grade.channel_id}>.",
                    ephemeral=True
                )
                return
            
            # Create configuration
            config = GradeChannelConfig(
                channel_id=self.channel_id,
                grade_level=grade_level
            )
            session.add(config)
            await session.commit()
            
            # Create initial message
            from cogs.homework import update_homework_message
            await update_homework_message(interaction.client, session, config)
            
            embed = Embed(
                title="✅ Homework Channel Configured",
                description=f"Channel: <#{self.channel_id}>\nGrade Level: **{grade_level}**",
                color=discord.Color.green()
            )
            embed.add_field(
                name="Next Steps",
                value="Use `/homework` → Add Course to start adding courses and assignments.",
                inline=False
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)


class RemoveChannelSelectView(ui.View):
    """View for selecting a homework channel to remove."""
    
    def __init__(self):
        super().__init__(timeout=300)
        
        channel_select = ui.ChannelSelect(
            placeholder="Select channel to remove...",
            channel_types=[ChannelType.text],
            custom_id="remove_channel_select"
        )
        channel_select.callback = self.channel_selected
        self.add_item(channel_select)
    
    async def channel_selected(self, interaction: Interaction):
        """Handle channel selection for removal."""
        from db import AsyncSessionLocal
        
        channel_id = self.children[0].values[0].id
        
        async with AsyncSessionLocal() as session:
            # Check if channel is configured
            result = await session.execute(
                select(GradeChannelConfig).where(
                    GradeChannelConfig.channel_id == channel_id
                )
            )
            config = result.scalar_one_or_none()
            
            if not config:
                await interaction.response.send_message(
                    f"❌ <#{channel_id}> is not configured as a homework channel.",
                    ephemeral=True
                )
                return
            
            # Get counts for confirmation
            result = await session.execute(
                select(Course).where(Course.channel_id == channel_id)
            )
            courses = result.scalars().all()
            
            total_assignments = sum(len(course.assignments) for course in courses)
            
            # Show confirmation view
            view = ConfirmRemoveChannelView(config, len(courses), total_assignments)
            embed = Embed(
                title="⚠️ Confirm Removal",
                description=f"Are you sure you want to remove the homework configuration for <#{channel_id}>?",
                color=discord.Color.red()
            )
            embed.add_field(
                name="Configuration Details",
                value=f"**Grade Level:** {config.grade_level}\n"
                      f"**Courses:** {len(courses)}\n"
                      f"**Assignments:** {total_assignments}",
                inline=False
            )
            embed.add_field(
                name="⚠️ This action will:",
                value="• Delete the channel configuration\n"
                      "• Remove all associated courses\n"
                      "• Delete all assignments\n"
                      "• Remove the to-do list message",
                inline=False
            )
            embed.set_footer(text="This action cannot be undone!")
            
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class ConfirmRemoveChannelView(ui.View):
    """Confirmation view for removing a homework channel."""
    
    def __init__(self, config: GradeChannelConfig, course_count: int, assignment_count: int):
        super().__init__(timeout=60)
        self.config = config
        self.course_count = course_count
        self.assignment_count = assignment_count
    
    @ui.button(label="✅ Confirm Removal", style=ButtonStyle.danger)
    async def confirm(self, interaction: Interaction, button: ui.Button):
        """Confirm and execute removal."""
        from db import AsyncSessionLocal
        
        async with AsyncSessionLocal() as session:
            # Re-fetch the config to ensure it's bound to this session
            result = await session.execute(
                select(GradeChannelConfig).where(
                    GradeChannelConfig.channel_id == self.config.channel_id
                )
            )
            config = result.scalar_one_or_none()
            
            if not config:
                await interaction.response.send_message(
                    "❌ Configuration no longer exists.",
                    ephemeral=True
                )
                return
            
            channel_id = config.channel_id
            grade_level = config.grade_level
            message_id = config.message_id
            
            # Delete the configuration (cascade will handle courses and assignments)
            await session.delete(config)
            await session.commit()
            
            # Try to delete the to-do list message
            if message_id:
                try:
                    channel = interaction.guild.get_channel(channel_id)
                    if channel:
                        message = await channel.fetch_message(message_id)
                        await message.delete()
                except:
                    pass  # Message might already be deleted
            
            embed = Embed(
                title="✅ Configuration Removed",
                description=f"Successfully removed homework configuration for <#{channel_id}>.",
                color=discord.Color.green()
            )
            embed.add_field(
                name="Removed",
                value=f"**Grade Level:** {grade_level}\n"
                      f"**Courses:** {self.course_count}\n"
                      f"**Assignments:** {self.assignment_count}",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
            # Disable the buttons
            for item in self.children:
                item.disabled = True
            await interaction.message.edit(view=self)
    
    @ui.button(label="❌ Cancel", style=ButtonStyle.secondary)
    async def cancel(self, interaction: Interaction, button: ui.Button):
        """Cancel the removal."""
        await interaction.response.send_message(
            "✅ Removal cancelled. No changes were made.",
            ephemeral=True
        )
        
        # Disable the buttons
        for item in self.children:
            item.disabled = True
        await interaction.message.edit(view=self)


class SelectHomeworkChannelView(ui.View):
    """View for selecting which homework channel to work with."""
    
    def __init__(self, action: str):
        super().__init__(timeout=300)
        self.action = action
        
        # Use channel select - we'll validate it's a homework channel on selection
        channel_select = ui.ChannelSelect(
            placeholder="Select homework channel...",
            channel_types=[ChannelType.text],
            custom_id=f"select_hw_channel_{action}"
        )
        channel_select.callback = self.channel_selected
        self.add_item(channel_select)
    
    async def channel_selected(self, interaction: Interaction):
        """Handle homework channel selection."""
        from db import AsyncSessionLocal
        
        channel_id = self.children[0].values[0].id
        
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(GradeChannelConfig).where(
                    GradeChannelConfig.channel_id == channel_id
                )
            )
            config = result.scalar_one_or_none()
            
            if not config:
                await interaction.response.send_message(
                    f"❌ <#{channel_id}> is not configured as a homework channel. Use `/homework` → Setup to configure it first.",
                    ephemeral=True
                )
                return
            
            # Route to appropriate action
            if self.action == "add_assignment":
                # Get courses for this channel
                result = await session.execute(
                    select(Course).where(Course.channel_id == channel_id)
                )
                courses = result.scalars().all()
                
                if not courses:
                    await interaction.response.send_message(
                        "❌ No courses available. Add a course first.",
                        ephemeral=True
                    )
                    return
                
                view = AddAssignmentCourseSelect(session, courses)
                embed = Embed(
                    title="➕ Add Assignment",
                    description="Select a course for the new assignment:",
                    color=discord.Color.green()
                )
                await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            
            elif self.action == "edit_assignment":
                # Get all assignments
                result = await session.execute(
                    select(Course).where(Course.channel_id == channel_id)
                )
                courses = result.scalars().all()
                
                assignments = []
                for course in courses:
                    for assignment in course.assignments:
                        assignments.append((assignment, course))
                
                if not assignments:
                    await interaction.response.send_message(
                        "❌ No assignments available to edit.",
                        ephemeral=True
                    )
                    return
                
                view = EditAssignmentSelect(session, assignments)
                embed = Embed(
                    title="✏️ Edit Assignment",
                    description="Select an assignment to edit:",
                    color=discord.Color.orange()
                )
                await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            
            elif self.action == "delete_assignment":
                # Get all assignments
                result = await session.execute(
                    select(Course).where(Course.channel_id == channel_id)
                )
                courses = result.scalars().all()
                
                assignments = []
                for course in courses:
                    for assignment in course.assignments:
                        assignments.append((assignment, course))
                
                if not assignments:
                    await interaction.response.send_message(
                        "❌ No assignments available to delete.",
                        ephemeral=True
                    )
                    return
                
                view = DeleteAssignmentSelect(session, assignments, channel_id)
                embed = Embed(
                    title="🗑️ Delete Assignment",
                    description="Select an assignment to delete:",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            
            elif self.action == "add_course":
                modal = AddCourseModal(session, channel_id)
                await interaction.response.send_modal(modal)
            
            elif self.action == "edit_course":
                # Get courses
                result = await session.execute(
                    select(Course).where(Course.channel_id == channel_id)
                )
                courses = result.scalars().all()
                
                if not courses:
                    await interaction.response.send_message(
                        "❌ No courses available to edit.",
                        ephemeral=True
                    )
                    return
                
                view = EditCourseSelect(session, courses)
                embed = Embed(
                    title="📝 Edit Course",
                    description="Select a course to edit:",
                    color=discord.Color.blue()
                )
                await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            
            elif self.action == "delete_course":
                # Get courses
                result = await session.execute(
                    select(Course).where(Course.channel_id == channel_id)
                )
                courses = result.scalars().all()
                
                if not courses:
                    await interaction.response.send_message(
                        "❌ No courses available to delete.",
                        ephemeral=True
                    )
                    return
                
                view = DeleteCourseSelect(session, courses, channel_id)
                embed = Embed(
                    title="❌ Delete Course",
                    description="⚠️ Warning: Deleting a course will also delete all its assignments!\n\nSelect a course to delete:",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            
            elif self.action == "refresh":
                from cogs.homework import update_homework_message
                await update_homework_message(interaction.client, session, config)
                await interaction.response.send_message(
                    f"✅ To-do list refreshed for <#{channel_id}>!",
                    ephemeral=True
                )


# ============================================================================
# Assignment Management
# ============================================================================

class AddAssignmentCourseSelect(ui.View):
    """View for selecting a course when adding an assignment."""
    
    def __init__(self, session: AsyncSession, courses: List[Course]):
        super().__init__(timeout=300)
        self.db_session = session
        
        options = [
            SelectOption(label=course.name, value=str(course.id))
            for course in courses
        ]
        
        select = ui.Select(placeholder="Select a course...", options=options)
        select.callback = self.course_selected
        self.add_item(select)
        self.courses = {course.id: course for course in courses}
    
    async def course_selected(self, interaction: Interaction):
        course_id = int(self.children[0].values[0])
        course = self.courses[course_id]
        
        modal = AddAssignmentModal(self.db_session, course)
        await interaction.response.send_modal(modal)


class AddAssignmentModal(ui.Modal, title="Add Assignment"):
    """Modal for adding a new assignment."""
    
    assignment_title = ui.TextInput(
        label="Assignment Title",
        placeholder="e.g., Final Project Proposal",
        required=True,
        max_length=200
    )
    
    due_date_input = ui.TextInput(
        label="Due Date (DD/MM/YYYY HH:MM)",
        placeholder="e.g., 25/12/2024 23:59",
        required=True,
        max_length=16
    )
    
    modality = ui.TextInput(
        label="Submission Modality",
        placeholder="e.g., Online Submission, In-person",
        required=False,
        max_length=100
    )
    
    description = ui.TextInput(
        label="Description",
        placeholder="Details about the assignment...",
        style=TextStyle.paragraph,
        required=False,
        max_length=1000
    )
    
    def __init__(self, session: AsyncSession, course: Course):
        super().__init__()
        self.db_session = session
        self.course = course
        # Discord modal titles have a 45-character limit
        # "Add Assignment: " is 17 chars, leaving 28 for course name
        course_name = course.name[:28] if len(course.name) > 28 else course.name
        self.title = f"Add Assignment: {course_name}"
    
    async def on_submit(self, interaction: Interaction):
        try:
            # Parse date
            due_date = datetime.strptime(self.due_date_input.value, "%d/%m/%Y %H:%M")
        except ValueError:
            await interaction.response.send_message(
                "❌ Invalid date format. Please use DD/MM/YYYY HH:MM (e.g., 25/12/2024 23:59)",
                ephemeral=True
            )
            return
        
        # Create assignment
        assignment = Assignment(
            title=self.assignment_title.value,
            description=self.description.value if self.description.value else None,
            due_date=due_date,
            modality=self.modality.value if self.modality.value else None,
            status='active',
            course_id=self.course.id
        )
        
        self.db_session.add(assignment)
        await self.db_session.commit()
        
        # Update the to-do list
        result = await self.db_session.execute(
            select(GradeChannelConfig).where(
                GradeChannelConfig.channel_id == self.course.channel_id
            )
        )
        config = result.scalar_one_or_none()
        
        if config:
            from cogs.homework import update_homework_message
            await update_homework_message(interaction.client, self.db_session, config)
        
        await interaction.response.send_message(
            f"✅ Assignment **{self.assignment_title.value}** added to {self.course.name}!",
            ephemeral=True
        )


class EditAssignmentSelect(ui.View):
    """View for selecting an assignment to edit."""
    
    def __init__(self, session: AsyncSession, assignments: List[tuple]):
        super().__init__(timeout=300)
        self.db_session = session
        
        options = []
        for assignment, course in assignments[:25]:  # Discord limit
            status_emoji = "📝" if assignment.status == 'active' else "✅" if assignment.status == 'completed' else "⚠️"
            options.append(
                SelectOption(
                    label=f"{assignment.title[:80]}",
                    value=str(assignment.id),
                    description=f"{course.name} - Due: {assignment.due_date.strftime('%d/%m/%Y')}",
                    emoji=status_emoji
                )
            )
        
        select = ui.Select(placeholder="Select an assignment...", options=options)
        select.callback = self.assignment_selected
        self.add_item(select)
        self.assignments = {a[0].id: a for a in assignments}
    
    async def assignment_selected(self, interaction: Interaction):
        assignment_id = int(self.children[0].values[0])
        assignment, course = self.assignments[assignment_id]
        
        modal = EditAssignmentModal(self.db_session, assignment, course)
        await interaction.response.send_modal(modal)


class EditAssignmentModal(ui.Modal, title="Edit Assignment"):
    """Modal for editing an existing assignment."""
    
    assignment_title = ui.TextInput(
        label="Assignment Title",
        required=True,
        max_length=200
    )
    
    due_date_input = ui.TextInput(
        label="Due Date (DD/MM/YYYY HH:MM)",
        required=True,
        max_length=16
    )
    
    modality = ui.TextInput(
        label="Submission Modality",
        required=False,
        max_length=100
    )
    
    description = ui.TextInput(
        label="Description",
        style=TextStyle.paragraph,
        required=False,
        max_length=1000
    )
    
    def __init__(self, session: AsyncSession, assignment: Assignment, course: Course):
        super().__init__()
        self.db_session = session
        self.assignment = assignment
        self.course = course
        
        # Pre-fill with existing data
        self.assignment_title.default = assignment.title
        self.due_date_input.default = assignment.due_date.strftime("%d/%m/%Y %H:%M")
        self.modality.default = assignment.modality or ""
        self.description.default = assignment.description or ""
    
    async def on_submit(self, interaction: Interaction):
        try:
            due_date = datetime.strptime(self.due_date_input.value, "%d/%m/%Y %H:%M")
        except ValueError:
            await interaction.response.send_message(
                "❌ Invalid date format. Please use DD/MM/YYYY HH:MM",
                ephemeral=True
            )
            return
        
        # Update assignment
        self.assignment.title = self.assignment_title.value
        self.assignment.due_date = due_date
        self.assignment.modality = self.modality.value if self.modality.value else None
        self.assignment.description = self.description.value if self.description.value else None
        
        await self.db_session.commit()
        
        # Update to-do list
        result = await self.db_session.execute(
            select(GradeChannelConfig).where(
                GradeChannelConfig.channel_id == self.course.channel_id
            )
        )
        config = result.scalar_one_or_none()
        
        if config:
            from cogs.homework import update_homework_message
            await update_homework_message(interaction.client, self.db_session, config)
        
        await interaction.response.send_message(
            f"✅ Assignment **{self.assignment_title.value}** updated!",
            ephemeral=True
        )


class DeleteAssignmentSelect(ui.View):
    """View for selecting an assignment to delete."""
    
    def __init__(self, session: AsyncSession, assignments: List[tuple], channel_id: int):
        super().__init__(timeout=300)
        self.db_session = session
        self.channel_id = channel_id
        
        options = []
        for assignment, course in assignments[:25]:
            status_emoji = "📝" if assignment.status == 'active' else "✅" if assignment.status == 'completed' else "⚠️"
            options.append(
                SelectOption(
                    label=f"{assignment.title[:80]}",
                    value=str(assignment.id),
                    description=f"{course.name} - Due: {assignment.due_date.strftime('%d/%m/%Y')}",
                    emoji=status_emoji
                )
            )
        
        select = ui.Select(placeholder="Select an assignment...", options=options)
        select.callback = self.assignment_selected
        self.add_item(select)
        self.assignments = {a[0].id: a for a in assignments}
    
    async def assignment_selected(self, interaction: Interaction):
        assignment_id = int(self.children[0].values[0])
        assignment, course = self.assignments[assignment_id]
        
        # Show confirmation
        view = ConfirmDeleteView(self.db_session, assignment, course, self.channel_id, "assignment")
        embed = Embed(
            title="⚠️ Confirm Deletion",
            description=f"Are you sure you want to delete this assignment?\n\n"
                       f"**{assignment.title}**\n"
                       f"Course: {course.name}\n"
                       f"Due: {assignment.due_date.strftime('%d/%m/%Y %H:%M')}",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


# ============================================================================
# Course Management
# ============================================================================

class AddCourseModal(ui.Modal, title="Add Course"):
    """Modal for adding a new course."""
    
    course_name = ui.TextInput(
        label="Course Name",
        placeholder="e.g., Advanced Networking",
        required=True,
        max_length=100
    )
    
    course_channel_id = ui.TextInput(
        label="Course Channel ID (Optional)",
        placeholder="Right-click channel > Copy ID",
        required=False,
        max_length=20
    )
    
    def __init__(self, session: AsyncSession, channel_id: int):
        super().__init__()
        self.db_session = session
        self.channel_id = channel_id
    
    async def on_submit(self, interaction: Interaction):
        # Check if course already exists
        result = await self.db_session.execute(
            select(Course).where(
                Course.channel_id == self.channel_id,
                Course.name == self.course_name.value
            )
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            await interaction.response.send_message(
                f"❌ A course named '{self.course_name.value}' already exists in this channel.",
                ephemeral=True
            )
            return
        
        # Parse course channel ID if provided
        course_channel_id = None
        if self.course_channel_id.value:
            try:
                course_channel_id = int(self.course_channel_id.value.strip())
                # Verify the channel exists
                channel = interaction.guild.get_channel(course_channel_id)
                if not channel:
                    await interaction.response.send_message(
                        f"❌ Channel with ID {course_channel_id} not found in this server.",
                        ephemeral=True
                    )
                    return
            except ValueError:
                await interaction.response.send_message(
                    f"❌ Invalid channel ID format. Please enter a valid numeric ID.",
                    ephemeral=True
                )
                return
        
        # Create course
        course = Course(
            name=self.course_name.value,
            channel_id=self.channel_id,
            course_channel_id=course_channel_id
        )
        self.db_session.add(course)
        await self.db_session.commit()
        
        # Update the main message
        result = await self.db_session.execute(
            select(GradeChannelConfig).where(GradeChannelConfig.channel_id == self.channel_id)
        )
        config = result.scalar_one_or_none()
        
        if config:
            from cogs.homework import update_homework_message
            await update_homework_message(interaction.client, self.db_session, config)
        
        await interaction.response.send_message(
            f"✅ Course '{self.course_name.value}' added successfully!",
            ephemeral=True
        )


class EditCourseSelect(ui.View):
    """View for selecting a course to edit."""
    
    def __init__(self, session: AsyncSession, courses: List[Course]):
        super().__init__(timeout=300)
        self.db_session = session
        
        options = [
            SelectOption(
                label=course.name,
                value=str(course.id),
                description=f"{len(course.assignments)} assignment(s)",
                emoji="📘"
            )
            for course in courses[:25]
        ]
        
        select = ui.Select(placeholder="Select a course...", options=options)
        select.callback = self.course_selected
        self.add_item(select)
        self.courses = {course.id: course for course in courses}
    
    async def course_selected(self, interaction: Interaction):
        course_id = int(self.children[0].values[0])
        course = self.courses[course_id]
        
        modal = EditCourseModal(self.db_session, course)
        await interaction.response.send_modal(modal)


class EditCourseModal(ui.Modal, title="Edit Course"):
    """Modal for editing an existing course."""
    
    course_name = ui.TextInput(
        label="Course Name",
        required=True,
        max_length=100
    )
    
    course_channel_id = ui.TextInput(
        label="Course Channel ID (Optional)",
        placeholder="Right-click channel > Copy ID",
        required=False,
        max_length=20
    )
    
    def __init__(self, session: AsyncSession, course: Course):
        super().__init__()
        self.db_session = session
        self.course = course
        
        # Pre-fill with existing data
        self.course_name.default = course.name
        self.course_channel_id.default = str(course.course_channel_id) if course.course_channel_id else ""
    
    async def on_submit(self, interaction: Interaction):
        # Parse course channel ID if provided
        course_channel_id = None
        if self.course_channel_id.value:
            try:
                course_channel_id = int(self.course_channel_id.value.strip())
                channel = interaction.guild.get_channel(course_channel_id)
                if not channel:
                    await interaction.response.send_message(
                        f"❌ Channel with ID {course_channel_id} not found in this server.",
                        ephemeral=True
                    )
                    return
            except ValueError:
                await interaction.response.send_message(
                    f"❌ Invalid channel ID format.",
                    ephemeral=True
                )
                return
        
        # Update course
        self.course.name = self.course_name.value
        self.course.course_channel_id = course_channel_id
        
        await self.db_session.commit()
        
        # Update to-do list
        result = await self.db_session.execute(
            select(GradeChannelConfig).where(
                GradeChannelConfig.channel_id == self.course.channel_id
            )
        )
        config = result.scalar_one_or_none()
        
        if config:
            from cogs.homework import update_homework_message
            await update_homework_message(interaction.client, self.db_session, config)
        
        await interaction.response.send_message(
            f"✅ Course '{self.course_name.value}' updated!",
            ephemeral=True
        )


class DeleteCourseSelect(ui.View):
    """View for selecting a course to delete."""
    
    def __init__(self, session: AsyncSession, courses: List[Course], channel_id: int):
        super().__init__(timeout=300)
        self.db_session = session
        self.channel_id = channel_id
        
        options = [
            SelectOption(
                label=course.name,
                value=str(course.id),
                description=f"{len(course.assignments)} assignment(s) will be deleted!",
                emoji="📘"
            )
            for course in courses[:25]
        ]
        
        select = ui.Select(placeholder="Select a course...", options=options)
        select.callback = self.course_selected
        self.add_item(select)
        self.courses = {course.id: course for course in courses}
    
    async def course_selected(self, interaction: Interaction):
        course_id = int(self.children[0].values[0])
        course = self.courses[course_id]
        
        # Show confirmation
        view = ConfirmDeleteView(self.db_session, course, None, self.channel_id, "course")
        embed = Embed(
            title="⚠️ Confirm Deletion",
            description=f"Are you sure you want to delete this course?\n\n"
                       f"**{course.name}**\n"
                       f"⚠️ This will also delete **{len(course.assignments)}** assignment(s)!",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class ConfirmDeleteView(ui.View):
    """Confirmation view for deletions."""
    
    def __init__(self, session: AsyncSession, item, course, channel_id: int, item_type: str):
        super().__init__(timeout=60)
        self.db_session = session
        self.item = item
        self.course = course
        self.channel_id = channel_id
        self.item_type = item_type
    
    @ui.button(label="Confirm Delete", style=ButtonStyle.danger)
    async def confirm(self, interaction: Interaction, button: ui.Button):
        # Delete the item
        await self.db_session.delete(self.item)
        await self.db_session.commit()
        
        # Update to-do list
        result = await self.db_session.execute(
            select(GradeChannelConfig).where(
                GradeChannelConfig.channel_id == self.channel_id
            )
        )
        config = result.scalar_one_or_none()
        
        if config:
            from cogs.homework import update_homework_message
            await update_homework_message(interaction.client, self.db_session, config)
        
        item_name = self.item.title if self.item_type == "assignment" else self.item.name
        await interaction.response.send_message(
            f"✅ {self.item_type.capitalize()} **{item_name}** deleted successfully!",
            ephemeral=True
        )
    
    @ui.button(label="Cancel", style=ButtonStyle.secondary)
    async def cancel(self, interaction: Interaction, button: ui.Button):
        await interaction.response.send_message(
            "❌ Deletion cancelled.",
            ephemeral=True
        )


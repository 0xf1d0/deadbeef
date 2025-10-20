import discord
from discord import ui, ButtonStyle, TextStyle, Interaction, Embed, SelectOption
from typing import List
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import GradeChannelConfig, Course, Assignment


class HomeworkMainView(ui.View):
    """Main view for the homework to-do list with management buttons."""
    
    def __init__(self):
        super().__init__(timeout=None)  # Persistent view
    
    @ui.button(label="➕ Add Assignment", style=ButtonStyle.green, custom_id="hw_add_assignment")
    async def add_assignment(self, interaction: Interaction, button: ui.Button):
        from db import AsyncSessionLocal
        
        async with AsyncSessionLocal() as session:
            # Get courses for this channel
            result = await session.execute(
                select(Course).where(Course.channel_id == interaction.channel_id)
            )
            courses = result.scalars().all()
            
            if not courses:
                await interaction.response.send_message(
                    "❌ No courses available. Please add courses first using the 'Manage Courses' button.",
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
    
    @ui.button(label="📘 Manage Courses", style=ButtonStyle.blurple, custom_id="hw_manage_courses")
    async def manage_courses(self, interaction: Interaction, button: ui.Button):
        view = CourseManagementView(interaction.channel_id)
        embed = Embed(
            title="📘 Course Management",
            description="Choose an action:",
            color=discord.Color.blurple()
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @ui.button(label="🔄 Refresh", style=ButtonStyle.grey, custom_id="hw_refresh")
    async def refresh(self, interaction: Interaction, button: ui.Button):
        from db import AsyncSessionLocal
        
        async with AsyncSessionLocal() as session:
            # Get channel config
            result = await session.execute(
                select(GradeChannelConfig).where(GradeChannelConfig.channel_id == interaction.channel_id)
            )
            config = result.scalar_one_or_none()
            
            if not config:
                await interaction.response.send_message(
                    "❌ This channel is not configured for homework tracking.",
                    ephemeral=True
                )
                return
            
            # Refresh the to-do list
            from cogs.homework import update_homework_message
            await update_homework_message(interaction.client, session, config)
            
            await interaction.response.send_message("✅ To-do list refreshed!", ephemeral=True)


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
        self.title = f"Add Assignment for {course.name}"
    
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
            description=self.description.value or None,
            due_date=due_date,
            modality=self.modality.value or None,
            status='active',
            course_id=self.course.id
        )
        
        self.db_session.add(assignment)
        await self.db_session.commit()
        
        # Update the main message
        result = await self.db_session.execute(
            select(GradeChannelConfig).where(GradeChannelConfig.channel_id == self.course.channel_id)
        )
        config = result.scalar_one_or_none()
        
        if config:
            from cogs.homework import update_homework_message
            await update_homework_message(interaction.client, self.db_session, config)
        
        await interaction.response.send_message(
            f"✅ Assignment '{self.assignment_title.value}' added to {self.course.name}!",
            ephemeral=True
        )


class EditAssignmentModal(ui.Modal, title="Edit Assignment"):
    """Modal for editing an existing assignment."""
    
    assignment_title = ui.TextInput(label="Assignment Title", required=True, max_length=200)
    due_date_input = ui.TextInput(label="Due Date (DD/MM/YYYY HH:MM)", required=True, max_length=16)
    modality = ui.TextInput(label="Submission Modality", required=False, max_length=100)
    description = ui.TextInput(
        label="Description",
        style=TextStyle.paragraph,
        required=False,
        max_length=1000
    )
    
    def __init__(self, session: AsyncSession, assignment: Assignment):
        super().__init__()
        self.db_session = session
        self.assignment = assignment
        
        # Pre-fill with existing data
        self.assignment_title.default = assignment.title
        self.due_date_input.default = assignment.due_date.strftime("%d/%m/%Y %H:%M")
        self.modality.default = assignment.modality or ""
        self.description.default = assignment.description or ""
    
    async def on_submit(self, interaction: Interaction):
        try:
            # Parse date
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
        self.assignment.modality = self.modality.value or None
        self.assignment.description = self.description.value or None
        await self.db_session.commit()
        
        # Update the main message
        result = await self.db_session.execute(
            select(Course).where(Course.id == self.assignment.course_id)
        )
        course = result.scalar_one_or_none()
        
        if course:
            result = await self.db_session.execute(
                select(GradeChannelConfig).where(GradeChannelConfig.channel_id == course.channel_id)
            )
            config = result.scalar_one_or_none()
            
            if config:
                from cogs.homework import update_homework_message
                await update_homework_message(interaction.client, self.db_session, config)
        
        await interaction.response.send_message(
            f"✅ Assignment '{self.assignment_title.value}' has been updated!",
            ephemeral=True
        )


class AssignmentActionsView(ui.View):
    """View with Edit and Delete buttons for an assignment."""
    
    def __init__(self, assignment_id: int):
        super().__init__(timeout=300)
        self.assignment_id = assignment_id
    
    @ui.button(label="Edit", style=ButtonStyle.blurple)
    async def edit_assignment(self, interaction: Interaction, button: ui.Button):
        from db import AsyncSessionLocal
        
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Assignment).where(Assignment.id == self.assignment_id)
            )
            assignment = result.scalar_one_or_none()
            
            if not assignment:
                await interaction.response.send_message(
                    "❌ Assignment not found.",
                    ephemeral=True
                )
                return
            
            modal = EditAssignmentModal(session, assignment)
            await interaction.response.send_modal(modal)
    
    @ui.button(label="Delete", style=ButtonStyle.red)
    async def delete_assignment(self, interaction: Interaction, button: ui.Button):
        from db import AsyncSessionLocal
        
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Assignment).where(Assignment.id == self.assignment_id)
            )
            assignment = result.scalar_one_or_none()
            
            if not assignment:
                await interaction.response.send_message(
                    "❌ Assignment not found.",
                    ephemeral=True
                )
                return
            
            # Confirmation view
            confirm_view = ui.View(timeout=60)
            confirm_button = ui.Button(label="Confirm Delete", style=ButtonStyle.danger)
            cancel_button = ui.Button(label="Cancel", style=ButtonStyle.secondary)
            
            async def confirm_callback(confirm_interaction: Interaction):
                await session.delete(assignment)
                await session.commit()
                
                # Update the main message
                result = await session.execute(
                    select(Course).where(Course.id == assignment.course_id)
                )
                course = result.scalar_one_or_none()
                
                if course:
                    result = await session.execute(
                        select(GradeChannelConfig).where(GradeChannelConfig.channel_id == course.channel_id)
                    )
                    config = result.scalar_one_or_none()
                    
                    if config:
                        from cogs.homework import update_homework_message
                        await update_homework_message(confirm_interaction.client, session, config)
                
                await confirm_interaction.response.edit_message(
                    content=f"✅ Assignment '{assignment.title}' has been deleted.",
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
                title="⚠️ Confirm Deletion",
                description=f"Are you sure you want to delete the assignment **{assignment.title}**?\n\nThis action cannot be undone.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, view=confirm_view, ephemeral=True)
    
    @ui.button(label="Mark Complete", style=ButtonStyle.green)
    async def mark_complete(self, interaction: Interaction, button: ui.Button):
        from db import AsyncSessionLocal
        
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Assignment).where(Assignment.id == self.assignment_id)
            )
            assignment = result.scalar_one_or_none()
            
            if not assignment:
                await interaction.response.send_message(
                    "❌ Assignment not found.",
                    ephemeral=True
                )
                return
            
            assignment.status = 'completed'
            await session.commit()
            
            # Update the main message
            result = await session.execute(
                select(Course).where(Course.id == assignment.course_id)
            )
            course = result.scalar_one_or_none()
            
            if course:
                result = await session.execute(
                    select(GradeChannelConfig).where(GradeChannelConfig.channel_id == course.channel_id)
                )
                config = result.scalar_one_or_none()
                
                if config:
                    from cogs.homework import update_homework_message
                    await update_homework_message(interaction.client, session, config)
            
            await interaction.response.send_message(
                f"✅ Assignment '{assignment.title}' marked as completed!",
                ephemeral=True
            )


class CourseManagementView(ui.View):
    """View for managing courses."""
    
    def __init__(self, channel_id: int):
        super().__init__(timeout=300)
        self.channel_id = channel_id
    
    @ui.button(label="Add Course", style=ButtonStyle.green)
    async def add_course(self, interaction: Interaction, button: ui.Button):
        from db import AsyncSessionLocal
        
        async with AsyncSessionLocal() as session:
            modal = AddCourseModal(session, self.channel_id)
            await interaction.response.send_modal(modal)
    
    @ui.button(label="Edit Course", style=ButtonStyle.blurple)
    async def edit_course(self, interaction: Interaction, button: ui.Button):
        from db import AsyncSessionLocal
        
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Course).where(Course.channel_id == self.channel_id)
            )
            courses = result.scalars().all()
            
            if not courses:
                await interaction.response.send_message(
                    "❌ No courses available.",
                    ephemeral=True
                )
                return
            
            view = EditCourseSelect(session, courses)
            embed = Embed(
                title="Edit Course",
                description="Select a course to edit:",
                color=discord.Color.blurple()
            )
            await interaction.response.edit_message(embed=embed, view=view)
    
    @ui.button(label="Delete Course", style=ButtonStyle.red)
    async def delete_course(self, interaction: Interaction, button: ui.Button):
        from db import AsyncSessionLocal
        
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Course).where(Course.channel_id == self.channel_id)
            )
            courses = result.scalars().all()
            
            if not courses:
                await interaction.response.send_message(
                    "❌ No courses available.",
                    ephemeral=True
                )
                return
            
            view = DeleteCourseSelect(session, courses)
            embed = Embed(
                title="Delete Course",
                description="⚠️ Select a course to delete.\n**Warning:** This will also delete all assignments for this course!",
                color=discord.Color.red()
            )
            await interaction.response.edit_message(embed=embed, view=view)


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
            f"✅ Course '{self.course_name.value}' has been added!",
            ephemeral=True
        )


class EditCourseSelect(ui.View):
    """View for selecting a course to edit."""
    
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
        
        modal = EditCourseModal(self.db_session, course)
        await interaction.response.send_modal(modal)


class EditCourseModal(ui.Modal, title="Edit Course"):
    """Modal for editing a course."""
    
    course_name = ui.TextInput(label="Course Name", required=True, max_length=100)
    
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
        if course.course_channel_id:
            self.course_channel_id.default = str(course.course_channel_id)
    
    async def on_submit(self, interaction: Interaction):
        # Check if new name conflicts
        if self.course_name.value != self.course.name:
            result = await self.db_session.execute(
                select(Course).where(
                    Course.channel_id == self.course.channel_id,
                    Course.name == self.course_name.value
                )
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                await interaction.response.send_message(
                    f"❌ A course named '{self.course_name.value}' already exists.",
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
        
        # Update course
        self.course.name = self.course_name.value
        self.course.course_channel_id = course_channel_id
        await self.db_session.commit()
        
        # Update the main message
        result = await self.db_session.execute(
            select(GradeChannelConfig).where(GradeChannelConfig.channel_id == self.course.channel_id)
        )
        config = result.scalar_one_or_none()
        
        if config:
            from cogs.homework import update_homework_message
            await update_homework_message(interaction.client, self.db_session, config)
        
        await interaction.response.send_message(
            f"✅ Course has been renamed to '{self.course_name.value}'!",
            ephemeral=True
        )


class DeleteCourseSelect(ui.View):
    """View for selecting a course to delete."""
    
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
        
        # Count assignments
        assignment_count = len(course.assignments)
        
        # Confirmation view
        confirm_view = ui.View(timeout=60)
        confirm_button = ui.Button(label="Confirm Delete", style=ButtonStyle.danger)
        cancel_button = ui.Button(label="Cancel", style=ButtonStyle.secondary)
        
        async def confirm_callback(confirm_interaction: Interaction):
            await self.db_session.delete(course)
            await self.db_session.commit()
            
            # Update the main message
            result = await self.db_session.execute(
                select(GradeChannelConfig).where(GradeChannelConfig.channel_id == course.channel_id)
            )
            config = result.scalar_one_or_none()
            
            if config:
                from cogs.homework import update_homework_message
                await update_homework_message(confirm_interaction.client, self.db_session, config)
            
            await confirm_interaction.response.edit_message(
                content=f"✅ Course '{course.name}' and its {assignment_count} assignment(s) have been deleted.",
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
            title="⚠️ Confirm Course Deletion",
            description=f"Are you sure you want to delete the course **{course.name}**?\n\n"
                       f"This will also delete **{assignment_count} assignment(s)**.\n\n"
                       f"**This action cannot be undone.**",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, view=confirm_view, ephemeral=True)


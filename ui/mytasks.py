"""
UI components for the My Tasks personal hub.
Provides persistent button views and interactive task list.
"""
from discord import ui, Interaction, Embed, Color, ButtonStyle
from typing import List, Set
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class MyTasksHubView(ui.View):
    """Persistent view for the My Tasks hub with the main button."""
    
    def __init__(self, bot):
        super().__init__(timeout=None)  # Persistent view
        self.bot = bot
    
    @ui.button(
        label="View My Tasks",
        style=ButtonStyle.primary,
        custom_id="persistent:my_tasks_view"
    )
    async def view_my_tasks(self, interaction: Interaction, button: ui.Button):
        """Handle clicking the 'View My Tasks' button."""
        await interaction.response.defer(ephemeral=True, thinking=True)
        
        from db import AsyncSessionLocal
        from db.models import MyTasksHubConfig, UserAssignmentProgress, Assignment, Course, GradeChannelConfig, AssignmentStatus
        from sqlalchemy import select, and_
        
        async with AsyncSessionLocal() as session:
            # Find grade level for this channel
            result = await session.execute(
                select(MyTasksHubConfig).where(
                    MyTasksHubConfig.channel_id == interaction.channel_id
                )
            )
            hub_config = result.scalar_one_or_none()
            
            if not hub_config:
                await interaction.followup.send(
                    "❌ This channel is not configured as a My Tasks hub.",
                    ephemeral=True
                )
                return
            
            grade_level = hub_config.grade_level
            
            # Get all relevant assignments for this grade level
            result = await session.execute(
                select(Assignment)
                .join(Course, Assignment.course_id == Course.id)
                .join(GradeChannelConfig, Course.channel_id == GradeChannelConfig.channel_id)
                .where(
                    GradeChannelConfig.grade_level == grade_level,
                    Assignment.status == AssignmentStatus.ACTIVE.value
                )
                .order_by(Assignment.due_date.asc())
            )
            all_assignments: List[Assignment] = result.scalars().all()
            
            # Get user's completed task IDs
            result = await session.execute(
                select(UserAssignmentProgress.assignment_id).where(
                    UserAssignmentProgress.user_id == interaction.user.id
                )
            )
            completed_ids: Set[int] = set(result.scalars().all())
            
            # Create the task list view
            view = UserTaskListView(
                interaction.user.id,
                all_assignments,
                completed_ids,
                self.bot
            )
            embed = view.create_embed()
            
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)


class UserTaskListView(ui.View):
    """Ephemeral view showing all tasks for a user with check/uncheck buttons."""
    
    def __init__(self, user_id: int, all_assignments: List, completed_ids: Set[int], bot):
        super().__init__(timeout=180)  # Ephemeral views timeout
        self.user_id = user_id
        self.all_assignments = all_assignments
        self.completed_ids = completed_ids
        self.bot = bot
        self.populate_items()
    
    def create_embed(self) -> Embed:
        """Create the embed showing all tasks and their completion status."""
        embed = Embed(
            title="📋 My Tasks",
            description="Manage your assignment progress below:",
            color=Color.blue()
        )
        
        description_parts = []
        
        for assignment in self.all_assignments:
            is_checked = assignment.id in self.completed_ids
            
            # Format due date
            due_str = assignment.due_date.strftime('%d/%m/%Y')
            
            if is_checked:
                description_parts.append(
                    f"~~✓ **{assignment.title}** ({assignment.course.name}) - Due: {due_str}~~"
                )
            else:
                description_parts.append(
                    f"□ **{assignment.title}** ({assignment.course.name}) - Due: {due_str}"
                )
        
        if not description_parts:
            embed.description = "🎉 No tasks assigned! You're all caught up."
        else:
            embed.description = "\n".join(description_parts)
        
        # Add footer stats
        completed_count = len(self.completed_ids)
        total_count = len(self.all_assignments)
        progress = (completed_count / total_count * 100) if total_count > 0 else 0
        embed.set_footer(text=f"Progress: {completed_count}/{total_count} ({progress:.0f}%)")
        
        return embed
    
    def populate_items(self):
        """Add/refresh all buttons for tasks."""
        self.clear_items()
        
        # Limit to 25 buttons (5 rows max in Discord)
        tasks_to_show = self.all_assignments[:25]
        
        for assignment in tasks_to_show:
            is_checked = assignment.id in self.completed_ids
            
            if is_checked:
                label = "✓ Mark Incomplete"
                style = ButtonStyle.secondary
                custom_id = f"mytask:uncheck:{assignment.id}"
            else:
                label = "○ Mark Complete"
                style = ButtonStyle.success
                custom_id = f"mytask:check:{assignment.id}"
            
            # Truncate label if needed (max 80 chars)
            if len(label) > 80:
                label = label[:77] + "..."
            
            self.add_item(
                TaskToggleButton(
                    label=label,
                    style=style,
                    custom_id=custom_id,
                    assignment_id=assignment.id
                )
            )
        
        if len(self.all_assignments) > 25:
            # Add info about pagination
            pass  # Could implement pagination here if needed


class TaskToggleButton(ui.Button):
    """Helper button for individual task toggling."""
    
    def __init__(self, *, label: str, style: ButtonStyle, custom_id: str, assignment_id: int):
        super().__init__(label=label, style=style, custom_id=custom_id)
        self.assignment_id = assignment_id
    
    async def callback(self, interaction: Interaction):
        """Handle task check/uncheck."""
        view: UserTaskListView = self.view
        user_id = interaction.user.id
        
        # Parse action from custom_id
        parts = self.custom_id.split(":")
        if len(parts) != 3:
            await interaction.response.send_message("❌ Invalid button action.", ephemeral=True)
            return
        
        action = parts[1]
        
        await interaction.response.defer()
        
        from db import AsyncSessionLocal
        from db.models import UserAssignmentProgress, Assignment
        from sqlalchemy import delete
        
        async with AsyncSessionLocal() as session:
            if action == "check":
                # Mark as completed
                new_progress = UserAssignmentProgress(
                    user_id=user_id,
                    assignment_id=self.assignment_id
                )
                session.add(new_progress)
                view.completed_ids.add(self.assignment_id)
                
            elif action == "uncheck":
                # Mark as incomplete
                stmt = delete(UserAssignmentProgress).where(
                    UserAssignmentProgress.user_id == user_id,
                    UserAssignmentProgress.assignment_id == self.assignment_id
                )
                await session.execute(stmt)
                view.completed_ids.discard(self.assignment_id)
            
            await session.commit()
            
            # Refresh the message
            new_embed = view.create_embed()
            view.populate_items()  # Refresh all buttons
            
            await interaction.edit_original_response(embed=new_embed, view=view)


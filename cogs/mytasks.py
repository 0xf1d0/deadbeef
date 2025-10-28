"""
My Tasks cog for personal assignment tracking.
Provides a hub where students can view and mark assignments as completed.
"""
from discord.ext import commands
from discord import app_commands, Interaction, Embed, Color, TextChannel
from typing import Optional
from sqlalchemy import select

from db import AsyncSessionLocal, init_db
from db.models import MyTasksHubConfig, GradeChannelConfig, AssignmentStatus
from db.constants import GradeLevel
from ui.mytasks import MyTasksHubView


class MyTasks(commands.Cog):
    """Cog for the My Tasks personal hub system."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    async def cog_load(self):
        """Initialize database and add persistent view when cog loads."""
        await init_db()
        
        # Add persistent view to bot
        self.bot.add_view(MyTasksHubView(self.bot))
        print("MyTasks cog loaded with persistent view")
    
    @app_commands.command(
        name="setup_mytasks",
        description="Setup a My Tasks hub for a grade level (Admin only)."
    )
    @app_commands.describe(
        channel="The channel for the My Tasks hub",
        grade="The grade level (M1 or M2)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_mytasks(
        self,
        interaction: Interaction,
        channel: TextChannel,
        grade: str
    ):
        """Setup a My Tasks hub channel for a grade level."""
        # Validate grade level
        valid_grades = ['M1', 'M2']
        if grade.upper() not in valid_grades:
            await interaction.response.send_message(
                f"❌ Invalid grade. Must be one of: {', '.join(valid_grades)}",
                ephemeral=True
            )
            return
        
        await interaction.response.defer(ephemeral=True)
        
        async with AsyncSessionLocal() as session:
            # Check if this grade already has a hub
            result = await session.execute(
                select(MyTasksHubConfig).where(
                    MyTasksHubConfig.grade_level == grade.upper()
                )
            )
            existing_config = result.scalar_one_or_none()
            
            if existing_config:
                # Update channel
                existing_config.channel_id = channel.id
                config = existing_config
            else:
                # Create new config
                config = MyTasksHubConfig(
                    channel_id=channel.id,
                    grade_level=grade.upper()
                )
                session.add(config)
            
            # Create the hub message
            embed = Embed(
                title="📋 My Tasks Hub",
                description=(
                    f"**Grade Level:** {grade.upper()}\n\n"
                    "This is your personal tasks hub. Click the button below to view and manage your assignments.\n\n"
                    "You can mark assignments as complete as you finish them. Your progress is saved automatically."
                ),
                color=Color.blue()
            )
            embed.add_field(
                name="How It Works",
                value=(
                    "1️⃣ Click 'View My Tasks' below\n"
                    "2️⃣ See all your active assignments\n"
                    "3️⃣ Click buttons to mark them complete\n"
                    "4️⃣ Check off assignments as you finish them"
                ),
                inline=False
            )
            embed.set_footer(text="Your progress is private and only visible to you")
            
            view = MyTasksHubView(self.bot)
            message = await channel.send(embed=embed, view=view)
            
            # Save message ID
            config.message_id = message.id
            await session.commit()
            
            await interaction.followup.send(
                f"✅ My Tasks hub configured for **{grade.upper()}** in {channel.mention}!\n"
                f"The hub message has been posted with a persistent button.",
                ephemeral=True
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(MyTasks(bot))


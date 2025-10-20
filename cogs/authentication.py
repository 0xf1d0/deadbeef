"""
Authentication cog for managing student and professional authentication.
Provides admin commands to register professionals and manage access.
"""
from discord.ext import commands
from discord import app_commands, Interaction, Embed, Color, TextChannel, SelectOption, Member
from discord import ui, ButtonStyle
from sqlalchemy import select
from typing import List, Optional

from db import AsyncSessionLocal, init_db
from db.models import AuthenticatedUser, Professional, ProfessionalCourseChannel, PendingAuth
from utils.utils import ROLE_MANAGER, ROLE_NOTABLE, ROLE_M1, ROLE_M2, ROLE_FI, ROLE_FA
from utils.csv_parser import get_all_students


class Authentication(commands.Cog):
    """Cog for authentication management."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    async def cog_load(self):
        """Initialize database when cog loads."""
        await init_db()
    
    @app_commands.command(
        name="register_professional",
        description="Register a new professional/teacher (Admin only)."
    )
    @app_commands.describe(
        email="Professional's email address",
        first_name="First name (optional)",
        last_name="Last name (optional)"
    )
    @app_commands.checks.has_any_role(ROLE_MANAGER.id, ROLE_NOTABLE.id)
    async def register_professional(
        self,
        interaction: Interaction,
        email: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None
    ):
        """Register a new professional in the system."""
        async with AsyncSessionLocal() as session:
            # Check if professional already exists
            result = await session.execute(
                select(Professional).where(Professional.email == email)
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                await interaction.response.send_message(
                    f"❌ Professional with email {email} already exists.",
                    ephemeral=True
                )
                return
            
            # Create new professional
            professional = Professional(
                email=email,
                first_name=first_name,
                last_name=last_name
            )
            
            session.add(professional)
            await session.commit()
            
            embed = Embed(
                title="✅ Professional Registered",
                color=Color.green()
            )
            embed.add_field(name="Email", value=email, inline=False)
            if first_name or last_name:
                name = f"{first_name or ''} {last_name or ''}".strip()
                embed.add_field(name="Name", value=name, inline=False)
            embed.add_field(
                name="Next Steps",
                value="Use `/add_course_access` to grant access to course channels.",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(
        name="add_course_access",
        description="Add course channel access for a professional (Admin only)."
    )
    @app_commands.describe(
        email="Professional's email",
        channel="Course channel to grant access to",
        channel_name="Friendly name for the channel (optional)"
    )
    @app_commands.checks.has_any_role(ROLE_MANAGER.id, ROLE_NOTABLE.id)
    async def add_course_access(
        self,
        interaction: Interaction,
        email: str,
        channel: TextChannel,
        channel_name: Optional[str] = None
    ):
        """Add course channel access for a professional."""
        async with AsyncSessionLocal() as session:
            # Get professional
            result = await session.execute(
                select(Professional).where(Professional.email == email)
            )
            pro = result.scalar_one_or_none()
            
            if not pro:
                await interaction.response.send_message(
                    f"❌ Professional not found. Register them first with `/register_professional`.",
                    ephemeral=True
                )
                return
            
            # Check if already has access
            result = await session.execute(
                select(ProfessionalCourseChannel).where(
                    ProfessionalCourseChannel.professional_id == pro.id,
                    ProfessionalCourseChannel.channel_id == channel.id
                )
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                await interaction.response.send_message(
                    f"❌ Professional already has access to {channel.mention}.",
                    ephemeral=True
                )
                return
            
            # Add course channel
            course_channel = ProfessionalCourseChannel(
                professional_id=pro.id,
                channel_id=channel.id,
                channel_name=channel_name or channel.name
            )
            
            session.add(course_channel)
            await session.commit()
            
            embed = Embed(
                title="✅ Course Access Added",
                color=Color.green()
            )
            embed.add_field(name="Professional", value=email, inline=False)
            embed.add_field(name="Channel", value=channel.mention, inline=False)
            if channel_name:
                embed.add_field(name="Channel Name", value=channel_name, inline=False)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(
        name="remove_course_access",
        description="Remove course channel access for a professional (Admin only)."
    )
    @app_commands.describe(
        email="Professional's email",
        channel="Course channel to remove access from"
    )
    @app_commands.checks.has_any_role(ROLE_MANAGER.id, ROLE_NOTABLE.id)
    async def remove_course_access(
        self,
        interaction: Interaction,
        email: str,
        channel: TextChannel
    ):
        """Remove course channel access for a professional."""
        async with AsyncSessionLocal() as session:
            # Get professional
            result = await session.execute(
                select(Professional).where(Professional.email == email)
            )
            pro = result.scalar_one_or_none()
            
            if not pro:
                await interaction.response.send_message(
                    f"❌ Professional not found.",
                    ephemeral=True
                )
                return
            
            # Get course channel mapping
            result = await session.execute(
                select(ProfessionalCourseChannel).where(
                    ProfessionalCourseChannel.professional_id == pro.id,
                    ProfessionalCourseChannel.channel_id == channel.id
                )
            )
            course_channel = result.scalar_one_or_none()
            
            if not course_channel:
                await interaction.response.send_message(
                    f"❌ Professional doesn't have access to {channel.mention}.",
                    ephemeral=True
                )
                return
            
            await session.delete(course_channel)
            await session.commit()
            
            embed = Embed(
                title="✅ Course Access Removed",
                color=Color.orange()
            )
            embed.add_field(name="Professional", value=email, inline=False)
            embed.add_field(name="Channel", value=channel.mention, inline=False)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(
        name="list_professionals",
        description="List all registered professionals (Admin only)."
    )
    @app_commands.checks.has_any_role(ROLE_MANAGER.id, ROLE_NOTABLE.id)
    async def list_professionals(self, interaction: Interaction):
        """List all registered professionals."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Professional))
            professionals = result.scalars().all()
            
            if not professionals:
                await interaction.response.send_message(
                    "No professionals registered yet.",
                    ephemeral=True
                )
                return
            
            embed = Embed(
                title="👔 Registered Professionals",
                color=Color.blue()
            )
            
            for pro in professionals:
                name = f"{pro.first_name or ''} {pro.last_name or ''}".strip() or "No name"
                channel_count = len(pro.course_channels)
                embed.add_field(
                    name=name,
                    value=f"📧 {pro.email}\n📚 {channel_count} course(s)",
                    inline=False
                )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(
        name="view_professional",
        description="View details of a specific professional (Admin only)."
    )
    @app_commands.describe(email="Professional's email")
    @app_commands.checks.has_any_role(ROLE_MANAGER.id, ROLE_NOTABLE.id)
    async def view_professional(self, interaction: Interaction, email: str):
        """View professional details and course access."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Professional).where(Professional.email == email)
            )
            pro = result.scalar_one_or_none()
            
            if not pro:
                await interaction.response.send_message(
                    f"❌ Professional not found.",
                    ephemeral=True
                )
                return
            
            embed = Embed(
                title=f"👔 Professional Details",
                color=Color.blue()
            )
            embed.add_field(name="Email", value=pro.email, inline=False)
            
            if pro.first_name or pro.last_name:
                name = f"{pro.first_name or ''} {pro.last_name or ''}".strip()
                embed.add_field(name="Name", value=name, inline=False)
            
            if pro.course_channels:
                channels = []
                for cc in pro.course_channels:
                    channel = interaction.guild.get_channel(cc.channel_id)
                    if channel:
                        channels.append(f"• {channel.mention} ({cc.channel_name or 'No name'})")
                    else:
                        channels.append(f"• Channel ID: {cc.channel_id} (deleted)")
                
                embed.add_field(
                    name=f"Course Channels ({len(pro.course_channels)})",
                    value="\n".join(channels) or "None",
                    inline=False
                )
            else:
                embed.add_field(name="Course Channels", value="None", inline=False)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(
        name="delete_professional",
        description="Delete a professional from the system (Admin only)."
    )
    @app_commands.describe(email="Professional's email")
    @app_commands.checks.has_any_role(ROLE_MANAGER.id, ROLE_NOTABLE.id)
    async def delete_professional(self, interaction: Interaction, email: str):
        """Delete a professional."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Professional).where(Professional.email == email)
            )
            pro = result.scalar_one_or_none()
            
            if not pro:
                await interaction.response.send_message(
                    f"❌ Professional not found.",
                    ephemeral=True
                )
                return
            
            # Confirmation
            view = ui.View(timeout=60)
            confirm_button = ui.Button(label="Confirm Delete", style=ButtonStyle.danger)
            cancel_button = ui.Button(label="Cancel", style=ButtonStyle.secondary)
            
            async def confirm_callback(confirm_interaction: Interaction):
                await session.delete(pro)
                await session.commit()
                
                await confirm_interaction.response.edit_message(
                    content=f"✅ Professional {email} has been deleted.",
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
            view.add_item(confirm_button)
            view.add_item(cancel_button)
            
            embed = Embed(
                title="⚠️ Confirm Deletion",
                description=f"Delete professional **{email}**?\n\n"
                           f"This will remove:\n"
                           f"• Professional record\n"
                           f"• {len(pro.course_channels)} course access(es)\n\n"
                           f"**This action cannot be undone.**",
                color=Color.red()
            )
            
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @app_commands.command(
        name="auth_stats",
        description="View authentication statistics (Admin only)."
    )
    @app_commands.checks.has_any_role(ROLE_MANAGER.id, ROLE_NOTABLE.id)
    async def auth_stats(self, interaction: Interaction):
        """View authentication statistics."""
        async with AsyncSessionLocal() as session:
            # Get all authenticated users
            result = await session.execute(select(AuthenticatedUser))
            users = result.scalars().all()
            
            # Get pending authentications
            result = await session.execute(select(PendingAuth))
            pending = result.scalars().all()
            
            # Count by type
            students = [u for u in users if u.user_type == 'student']
            professionals = [u for u in users if u.user_type == 'professional']
            
            # Count by grade level
            m1_students = [u for u in students if u.grade_level == 'M1']
            m2_students = [u for u in students if u.grade_level == 'M2']
            
            # Count by formation
            fi_students = [u for u in students if u.formation_type == 'FI']
            fa_students = [u for u in students if u.formation_type == 'FA']
            
            # Get total from CSV files
            all_students_csv = get_all_students()
            
            embed = Embed(
                title="📊 Authentication Statistics",
                color=Color.blue()
            )
            
            embed.add_field(
                name="Authenticated Users",
                value=f"**Total:** {len(users)}\n"
                      f"**Students:** {len(students)}\n"
                      f"**Professionals:** {len(professionals)}",
                inline=True
            )
            
            embed.add_field(
                name="Students by Grade",
                value=f"**M1:** {len(m1_students)}\n"
                      f"**M2:** {len(m2_students)}",
                inline=True
            )
            
            embed.add_field(
                name="Students by Formation",
                value=f"**FI:** {len(fi_students)}\n"
                      f"**FA:** {len(fa_students)}",
                inline=True
            )
            
            embed.add_field(
                name="CSV Data",
                value=f"**Total in CSV:** {len(all_students_csv)}\n"
                      f"**Authenticated:** {len(students)} ({len(students)*100//max(len(all_students_csv),1)}%)",
                inline=False
            )
            
            embed.add_field(
                name="Pending Authentications",
                value=str(len(pending)),
                inline=True
            )
            
            # Profile links
            with_rootme = len([u for u in users if u.rootme_id])
            with_linkedin = len([u for u in users if u.linkedin_url])
            
            embed.add_field(
                name="Profile Links",
                value=f"**Root-Me:** {with_rootme}\n"
                      f"**LinkedIn:** {with_linkedin}",
                inline=True
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(
        name="reset_roles",
        description="Remove M1/M2/FI/FA roles from all members (Admin only)."
    )
    @app_commands.describe(
        role_type="The role type to reset (M1, M2, FI, or FA)"
    )
    @app_commands.choices(role_type=[
        app_commands.Choice(name="M1 - Remove from all M1 students", value="M1"),
        app_commands.Choice(name="M2 - Remove from all M2 students", value="M2"),
        app_commands.Choice(name="FI - Remove from all FI students", value="FI"),
        app_commands.Choice(name="FA - Remove from all FA students", value="FA"),
    ])
    @app_commands.checks.has_any_role(ROLE_MANAGER.id, ROLE_NOTABLE.id)
    async def reset_roles(
        self,
        interaction: Interaction,
        role_type: str
    ):
        """Remove specified role from all members who have it."""
        # Map role type to role object
        role_map = {
            "M1": ROLE_M1,
            "M2": ROLE_M2,
            "FI": ROLE_FI,
            "FA": ROLE_FA
        }
        
        role_obj = role_map.get(role_type)
        if not role_obj:
            await interaction.response.send_message(
                f"❌ Invalid role type: {role_type}",
                ephemeral=True
            )
            return
        
        # Get the actual role from the guild
        role = interaction.guild.get_role(role_obj.id)
        if not role:
            await interaction.response.send_message(
                f"❌ Role not found in the server.",
                ephemeral=True
            )
            return
        
        # Count members with this role
        members_with_role = [member for member in interaction.guild.members if role in member.roles]
        member_count = len(members_with_role)
        
        if member_count == 0:
            await interaction.response.send_message(
                f"ℹ️ No members have the {role.mention} role.",
                ephemeral=True
            )
            return
        
        # Create confirmation view
        view = ui.View(timeout=60)
        confirm_button = ui.Button(label=f"Confirm - Remove from {member_count} member(s)", style=ButtonStyle.danger)
        cancel_button = ui.Button(label="Cancel", style=ButtonStyle.secondary)
        
        async def confirm_callback(confirm_interaction: Interaction):
            await confirm_interaction.response.defer()
            
            # Remove role from all members
            success_count = 0
            failed_count = 0
            
            for member in members_with_role:
                try:
                    await member.remove_roles(role, reason=f"Role reset by {interaction.user}")
                    success_count += 1
                except Exception as e:
                    print(f"Failed to remove role from {member}: {e}")
                    failed_count += 1
            
            # Create result embed
            result_embed = Embed(
                title="✅ Role Reset Complete",
                color=Color.green()
            )
            result_embed.add_field(
                name="Role",
                value=role.mention,
                inline=False
            )
            result_embed.add_field(
                name="Successfully Removed",
                value=str(success_count),
                inline=True
            )
            if failed_count > 0:
                result_embed.add_field(
                    name="Failed",
                    value=str(failed_count),
                    inline=True
                )
            result_embed.add_field(
                name="Executed By",
                value=interaction.user.mention,
                inline=False
            )
            
            await confirm_interaction.edit_original_response(
                content=None,
                embed=result_embed,
                view=None
            )
        
        async def cancel_callback(cancel_interaction: Interaction):
            await cancel_interaction.response.edit_message(
                content="❌ Role reset cancelled.",
                embed=None,
                view=None
            )
        
        confirm_button.callback = confirm_callback
        cancel_button.callback = cancel_callback
        view.add_item(confirm_button)
        view.add_item(cancel_button)
        
        # Create warning embed
        warning_embed = Embed(
            title="⚠️ Confirm Role Reset",
            description=f"This will remove the {role.mention} role from **{member_count}** member(s).\n\n"
                       f"**This action cannot be undone.**\n\n"
                       f"Members will need to re-authenticate to get this role back.",
            color=Color.red()
        )
        warning_embed.add_field(
            name="Affected Members",
            value=f"{member_count} member(s) currently have this role",
            inline=False
        )
        warning_embed.set_footer(text="This action will be logged and attributed to you.")
        
        await interaction.response.send_message(
            embed=warning_embed,
            view=view,
            ephemeral=True
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Authentication(bot))

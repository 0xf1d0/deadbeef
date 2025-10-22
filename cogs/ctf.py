"""
CTF Team Management System
Provides comprehensive tools for creating, managing, and competing in CTF teams.
"""
from discord.ext import commands
from discord import app_commands, Interaction, Embed, Color, PermissionOverwrite
from sqlalchemy import select, func
from typing import Optional

from db import AsyncSessionLocal, init_db
from db.models import PlayerProfile, Team, TeamInvite, TeamApplication, AuthenticatedUser
from utils import ROLE_MANAGER, ROLE_NOTABLE, CTF_CATEGORY
from ui.ctf import (
    CreateTeamModal, TeamManagementPanel, TeamListView,
    SetStatusView, ProfileView
)


class CTF(commands.Cog):
    """CTF Team Management System."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    async def cog_load(self):
        """Initialize database when cog loads."""
        await init_db()
    
    async def ensure_profile(self, user_id: int) -> PlayerProfile:
        """Ensure a player profile exists for the authenticated user."""
        async with AsyncSessionLocal() as session:
            # First check if user is authenticated
            result = await session.execute(
                select(AuthenticatedUser).where(AuthenticatedUser.user_id == user_id)
            )
            auth_user = result.scalar_one_or_none()
            
            if not auth_user:
                raise ValueError("User must be authenticated to create a CTF profile")
            
            # Check if CTF profile exists
            result = await session.execute(
                select(PlayerProfile).where(PlayerProfile.user_id == user_id)
            )
            profile = result.scalar_one_or_none()
            
            if not profile:
                profile = PlayerProfile(user_id=user_id)
                session.add(profile)
                await session.commit()
                await session.refresh(profile)
            
            return profile
    
    # ========================================================================
    # Profile Commands
    # ========================================================================
    
    profile_group = app_commands.Group(name="ctf", description="CTF Team Management")
    
    @profile_group.command(name="profile", description="View your CTF profile")
    async def profile_view(self, interaction: Interaction):
        """View user's CTF profile."""
        try:
            await self.ensure_profile(interaction.user.id)
            view = ProfileView(interaction.user.id)
            await view.send(interaction)
        except ValueError as e:
            await interaction.response.send_message(
                f"❌ {str(e)}\n\nYou must be authenticated first. Use the authentication system to get started.",
                ephemeral=True
            )
    
    
    @profile_group.command(
        name="set_status",
        description="Set your recruitment status"
    )
    async def set_status(self, interaction: Interaction):
        """Set recruitment status."""
        try:
            await self.ensure_profile(interaction.user.id)
            view = SetStatusView(interaction.user.id)
            embed = Embed(
                title="📊 Set Recruitment Status",
                description="Choose your current status:",
                color=Color.blue()
            )
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        except ValueError as e:
            await interaction.response.send_message(
                f"❌ {str(e)}\n\nYou must be authenticated first. Use the authentication system to get started.",
                ephemeral=True
            )
    
    # ========================================================================
    # Team Commands
    # ========================================================================
    
    @profile_group.command(name="create_team", description="Create a new CTF team")
    async def create_team(self, interaction: Interaction):
        """Create a new CTF team."""
        try:
            profile = await self.ensure_profile(interaction.user.id)
            
            async with AsyncSessionLocal() as session:
                # Refresh profile in this session
                result = await session.execute(
                    select(PlayerProfile).where(PlayerProfile.user_id == interaction.user.id)
                )
                profile = result.scalar_one()
                
                # Check if user is already on a team
                if profile.team_id is not None:
                    # Get team name
                    result = await session.execute(
                        select(Team).where(Team.id == profile.team_id)
                    )
                    team = result.scalar_one_or_none()
                    team_name = team.name if team else "a team"
                    
                    await interaction.response.send_message(
                        f"❌ You're already on **{team_name}**. Leave your current team before creating a new one.",
                        ephemeral=True
                    )
                    return
            
            # Show team creation modal
            modal = CreateTeamModal(self.bot)
            await interaction.response.send_modal(modal)
        except ValueError as e:
            await interaction.response.send_message(
                f"❌ {str(e)}\n\nYou must be authenticated first. Use the authentication system to get started.",
                ephemeral=True
            )
    
    @profile_group.command(name="leave_team", description="Leave your current team")
    async def leave_team(self, interaction: Interaction):
        """Leave current team."""
        try:
            await self.ensure_profile(interaction.user.id)
            
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(PlayerProfile).where(PlayerProfile.user_id == interaction.user.id)
                )
                profile = result.scalar_one()
                
                if not profile.team_id:
                    await interaction.response.send_message(
                        "❌ You're not on any team.",
                        ephemeral=True
                    )
                    return
            
            # Get team
            result = await session.execute(
                select(Team).where(Team.id == profile.team_id)
            )
            team = result.scalar_one()
            
            # Check if owner
            if team.owner_id == interaction.user.id:
                await interaction.response.send_message(
                    "❌ You're the team owner. Transfer ownership or disband the team first.",
                    ephemeral=True
                )
                return
            
            # Remove from team
            team_name = team.name
            profile.team_id = None
            await session.commit()
            
            # Remove team role
            try:
                guild = interaction.guild
                member = guild.get_member(interaction.user.id)
                team_role = next((r for r in guild.roles if r.name == f"CTF-{team_name}"), None)
                if team_role and team_role in member.roles:
                    await member.remove_roles(team_role, reason="Left team")
            except Exception as e:
                print(f"Error removing team role: {e}")
            
            # Notify team channel
            try:
                channel = self.bot.get_channel(team.channel_id)
                if channel:
                    await channel.send(f"📤 {interaction.user.mention} has left the team.")
            except:
                pass
            
            await interaction.response.send_message(
                f"✅ You've left **{team_name}**.",
                ephemeral=True
            )
        except ValueError as e:
            await interaction.response.send_message(
                f"❌ {str(e)}\n\nYou must be authenticated first. Use the authentication system to get started.",
                ephemeral=True
            )
    
    @profile_group.command(name="team_stats", description="View your team's statistics")
    async def team_stats(self, interaction: Interaction):
        """View team statistics."""
        try:
            await self.ensure_profile(interaction.user.id)
            
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(PlayerProfile).where(PlayerProfile.user_id == interaction.user.id)
                )
                profile = result.scalar_one()
                
                if not profile.team_id:
                    await interaction.response.send_message(
                        "❌ You're not on any team.",
                        ephemeral=True
                    )
                    return
            
            # Get team
            result = await session.execute(
                select(Team).where(Team.id == profile.team_id)
            )
            team = result.scalar_one()
            
            # Get all team members and their auth records (avoid lazy-loads)
            result = await session.execute(
                select(PlayerProfile, AuthenticatedUser)
                .join(AuthenticatedUser, AuthenticatedUser.user_id == PlayerProfile.user_id)
                .where(PlayerProfile.team_id == team.id)
            )
            rows = result.all()
            
            # Build stats embed
            embed = Embed(
                title=f"🏆 {team.name} - Team Statistics",
                description=team.description or "No description set",
                color=Color.blue()
            )
            
            # Team info
            owner = interaction.guild.get_member(team.owner_id)
            embed.add_field(
                name="Team Owner",
                value=owner.mention if owner else f"User ID: {team.owner_id}",
                inline=True
            )
            embed.add_field(name="Members", value=str(len(rows)), inline=True)
            embed.add_field(
                name="Recruiting",
                value="✅ Open" if team.is_recruiting else "❌ Closed",
                inline=True
            )
            
            # Member list
            member_list = []
            for member, auth_user in rows:
                user = interaction.guild.get_member(member.user_id)
                if user:
                    rootme_status = f" (`{auth_user.rootme_id}`)" if auth_user and auth_user.rootme_id else " (No Root-Me)"
                    owner_badge = " 👑" if member.user_id == team.owner_id else ""
                    member_list.append(f"• {user.mention}{owner_badge}{rootme_status}")
            
            if member_list:
                embed.add_field(
                    name="Team Members",
                    value="\n".join(member_list),
                    inline=False
                )
            
            # Root-Me stats (placeholder for now)
            linked_count = sum(1 for _m, a in rows if a and a.rootme_id)
            embed.add_field(name="📊 Root-Me Integration", value=f"{linked_count}/{len(rows)} members have linked Root-Me accounts\n*Full stats integration coming soon!*", inline=False)
            
            embed.set_footer(text=f"Team ID: {team.id} | Created {team.created_at.strftime('%Y-%m-%d')}")
            
            await interaction.response.send_message(embed=embed)
        except ValueError as e:
            await interaction.response.send_message(
                f"❌ {str(e)}\n\nYou must be authenticated first. Use the authentication system to get started.",
                ephemeral=True
            )
    
    @profile_group.command(name="teams", description="Browse available CTF teams")
    async def teams_list(self, interaction: Interaction):
        """List all recruiting teams."""
        try:
            await self.ensure_profile(interaction.user.id)
            
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(Team).where(Team.is_recruiting == True).order_by(Team.created_at.desc())
                )
                teams = result.scalars().all()
                
                if not teams:
                    await interaction.response.send_message(
                        "ℹ️ No teams are currently recruiting. Be the first to create one!",
                        ephemeral=True
                    )
                    return
                
                view = TeamListView(teams, interaction.user.id)
                await view.send(interaction)
        except ValueError as e:
            await interaction.response.send_message(
                f"❌ {str(e)}\n\nYou must be authenticated first. Use the authentication system to get started.",
                ephemeral=True
            )
    
    @profile_group.command(name="manage_team", description="Open team management panel (Owner only)")
    async def manage_team(self, interaction: Interaction):
        """Open team management panel."""
        try:
            await self.ensure_profile(interaction.user.id)
            
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(PlayerProfile).where(PlayerProfile.user_id == interaction.user.id)
                )
                profile = result.scalar_one()
                
                if not profile.team_id:
                    await interaction.response.send_message(
                        "❌ You're not on any team.",
                        ephemeral=True
                    )
                    return
            
            # Get team
            result = await session.execute(
                select(Team).where(Team.id == profile.team_id)
            )
            team = result.scalar_one()
            
            # Check if owner
            if team.owner_id != interaction.user.id:
                await interaction.response.send_message(
                    "❌ Only the team owner can access the management panel.",
                    ephemeral=True
                )
                return
            
            view = TeamManagementPanel(team.id)
            embed = Embed(
                title=f"⚙️ Manage {team.name}",
                description="Select an action from the menu below:",
                color=Color.blue()
            )
            
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        except ValueError as e:
            await interaction.response.send_message(
                f"❌ {str(e)}\n\nYou must be authenticated first. Use the authentication system to get started.",
                ephemeral=True
            )


async def setup(bot: commands.Bot):
    cog = CTF(bot)
    await bot.add_cog(cog)


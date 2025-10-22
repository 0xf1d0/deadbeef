"""
UI components for CTF Team Management System.
Provides modals, views, and interactive components for team operations.
"""
from discord import ui, Interaction, Embed, Color, SelectOption, ButtonStyle, PermissionOverwrite, ChannelType, TextStyle
from discord.ext import commands
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import datetime
import pytz

from db import AsyncSessionLocal
from db.models import PlayerProfile, Team, TeamInvite, TeamApplication, AuthenticatedUser
from utils import CTF_CATEGORY


# ============================================================================
# Profile Management Components
# ============================================================================

class ProfileView(ui.View):
    """View for displaying user's CTF profile."""
    
    def __init__(self, user_id: int):
        super().__init__(timeout=300)
        self.user_id = user_id
    
    async def send(self, interaction: Interaction):
        """Send the profile view."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(PlayerProfile).where(PlayerProfile.user_id == self.user_id)
            )
            profile = result.scalar_one_or_none()
            
            if not profile:
                await interaction.response.send_message(
                    "❌ Profile not found. This shouldn't happen!",
                    ephemeral=True
                )
                return
            
            embed = Embed(
                title="🎮 CTF Profile",
                color=Color.blue()
            )
            
            user = interaction.guild.get_member(self.user_id)
            if user:
                embed.set_author(name=user.display_name, icon_url=user.display_avatar.url)
            
            # Root-Me status (fetch directly from AuthenticatedUser to avoid lazy-load)
            result = await session.execute(
                select(AuthenticatedUser).where(AuthenticatedUser.user_id == self.user_id)
            )
            auth_user = result.scalar_one_or_none()
            rootme_status = f"`{auth_user.rootme_id}`" if auth_user and auth_user.rootme_id else "❌ Not linked"
            embed.add_field(name="Root-Me Account", value=rootme_status, inline=True)
            
            # Team status
            if profile.team_id:
                result = await session.execute(
                    select(Team).where(Team.id == profile.team_id)
                )
                team = result.scalar_one_or_none()
                team_info = f"**{team.name}**" if team else "Unknown"
                if team and team.owner_id == self.user_id:
                    team_info += " 👑"
            else:
                team_info = "No team"
            
            embed.add_field(name="Current Team", value=team_info, inline=True)
            
            # Status
            status_emoji = "🔍" if profile.status == "Looking for Team" else "💤"
            embed.add_field(name="Status", value=f"{status_emoji} {profile.status}", inline=True)
            
            # Commands
            commands_text = (
                "`/ctf set_status` - Change status\n"
                "`/ctf create_team` - Create a team\n"
                "`/ctf teams` - Browse teams\n"
                "`/profile` - Link Root-Me account (in main system)\n"
            )
            embed.add_field(name="Available Commands", value=commands_text, inline=False)
            
            if interaction.response.is_done():
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message(embed=embed, ephemeral=True)




class SetStatusView(ui.View):
    """View for setting recruitment status."""
    
    def __init__(self, user_id: int):
        super().__init__(timeout=300)
        self.user_id = user_id
        
        # Add select menu
        options = [
            SelectOption(label="Idle", description="Not actively looking", value="Idle", emoji="💤"),
            SelectOption(label="Looking for Team", description="Open to invites", value="Looking for Team", emoji="🔍"),
        ]
        
        select = ui.Select(placeholder="Choose your status...", options=options)
        select.callback = self.status_selected
        self.add_item(select)
    
    async def status_selected(self, interaction: Interaction):
        """Handle status selection."""
        status = self.children[0].values[0]
        
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(PlayerProfile).where(PlayerProfile.user_id == self.user_id)
            )
            profile = result.scalar_one()
            
            profile.status = status
            await session.commit()
            
            status_emoji = "🔍" if status == "Looking for Team" else "💤"
            await interaction.response.send_message(
                f"✅ Status updated to {status_emoji} **{status}**",
                ephemeral=True
            )


# ============================================================================
# User Selection Components
# ============================================================================

class PaginatedUserSelectView(ui.View):
    """Paginated view for selecting authenticated users."""
    
    def __init__(self, users: List[AuthenticatedUser], page: int = 0, callback_func=None, **callback_kwargs):
        super().__init__(timeout=300)
        self.users = users
        self.page = page
        self.callback_func = callback_func
        self.callback_kwargs = callback_kwargs
        self.users_per_page = 25  # Discord limit
        self.total_pages = (len(users) + self.users_per_page - 1) // self.users_per_page
        
        # Update button states
        if hasattr(self, 'children') and len(self.children) > 0:
            self.children[0].disabled = (page == 0)
            self.children[1].disabled = (page >= self.total_pages - 1)
    
    async def send(self, interaction: Interaction):
        """Send the user selection view."""
        embed = self.create_embed(interaction)
        await interaction.response.send_message(embed=embed, view=self, ephemeral=True)
    
    def create_embed(self, interaction: Interaction) -> Embed:
        """Create embed for current page."""
        embed = Embed(
            title="👥 Select User",
            description=f"Page {self.page + 1}/{self.total_pages}",
            color=Color.blue()
        )
        
        start_idx = self.page * self.users_per_page
        end_idx = start_idx + self.users_per_page
        page_users = self.users[start_idx:end_idx]
        
        # Create select menu options
        options = []
        for user in page_users:
            member = interaction.guild.get_member(user.user_id)
            display_name = member.display_name if member else f"User ID: {user.user_id}"
            rootme_info = f" ({user.rootme_id})" if user.rootme_id else ""
            
            options.append(SelectOption(
                label=display_name[:100],  # Discord limit
                description=f"Email: {user.email}{rootme_info}",
                value=str(user.user_id)
            ))
        
        # Update existing select menu or create new one
        if len(self.children) > 2:  # If select menu exists (after buttons)
            self.children[2].options = options
        else:
            # Create select menu
            select = ui.Select(placeholder="Choose a user...", options=options)
            select.callback = self.user_selected
            self.add_item(select)
        
        embed.set_footer(text=f"Total users: {len(self.users)} | Use buttons to navigate")
        
        return embed
    
    async def user_selected(self, interaction: Interaction):
        """Handle user selection."""
        # Find the select menu (it's the last child after buttons)
        select_menu = None
        for child in self.children:
            if isinstance(child, ui.Select):
                select_menu = child
                break
        
        if not select_menu or not select_menu.values:
            await interaction.response.send_message(
                "❌ No user selected.",
                ephemeral=True
            )
            return
        
        user_id = int(select_menu.values[0])
        
        if self.callback_func:
            await self.callback_func(interaction, user_id, **self.callback_kwargs)
    
    @ui.button(label="◀️ Previous", style=ButtonStyle.grey)
    async def previous_page(self, interaction: Interaction, button: ui.Button):
        """Go to previous page."""
        if self.page > 0:
            self.page -= 1
            # Update button states
            for child in self.children:
                if isinstance(child, ui.Button):
                    if child.label == "◀️ Previous":
                        child.disabled = (self.page == 0)
                    elif child.label == "Next ▶️":
                        child.disabled = False
            
            embed = self.create_embed(interaction)
            await interaction.response.edit_message(embed=embed, view=self)
    
    @ui.button(label="Next ▶️", style=ButtonStyle.grey)
    async def next_page(self, interaction: Interaction, button: ui.Button):
        """Go to next page."""
        if self.page < self.total_pages - 1:
            self.page += 1
            # Update button states
            for child in self.children:
                if isinstance(child, ui.Button):
                    if child.label == "◀️ Previous":
                        child.disabled = False
                    elif child.label == "Next ▶️":
                        child.disabled = (self.page >= self.total_pages - 1)
            
            embed = self.create_embed(interaction)
            await interaction.response.edit_message(embed=embed, view=self)


# ============================================================================
# Team Creation
# ============================================================================

class CreateTeamModal(ui.Modal, title="Create CTF Team"):
    """Modal for creating a new team."""
    
    team_name = ui.TextInput(
        label="Team Name",
        placeholder="Enter a unique team name",
        required=True,
        max_length=100
    )
    
    description = ui.TextInput(
        label="Team Description",
        placeholder="Tell others about your team...",
        required=False,
        style=TextStyle.paragraph,
        max_length=500
    )
    
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot
    
    async def on_submit(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        
        async with AsyncSessionLocal() as session:
            # Check if team name is taken
            result = await session.execute(
                select(Team).where(Team.name == self.team_name.value)
            )
            existing_team = result.scalar_one_or_none()
            
            if existing_team:
                await interaction.followup.send(
                    f"❌ Team name `{self.team_name.value}` is already taken.",
                    ephemeral=True
                )
                return
            
            # Get user profile
            result = await session.execute(
                select(PlayerProfile).where(PlayerProfile.user_id == interaction.user.id)
            )
            profile = result.scalar_one()
            
            # Double-check team constraint
            if profile.team_id is not None:
                await interaction.followup.send(
                    "❌ You're already on a team. Leave it first.",
                    ephemeral=True
                )
                return
            
            try:
                # Create team role
                guild = interaction.guild
                team_role = await guild.create_role(
                    name=f"CTF-{self.team_name.value}",
                    mentionable=True,
                    reason=f"Team role for {self.team_name.value}"
                )
                
                # Create team channel
                category = self.bot.get_channel(CTF_CATEGORY.id)
                if not category:
                    await interaction.followup.send(
                        "❌ CTF category not found. Contact an administrator.",
                        ephemeral=True
                    )
                    return
                
                # Set up permissions
                overwrites = {
                    guild.default_role: PermissionOverwrite(read_messages=False),
                    team_role: PermissionOverwrite(
                        read_messages=True,
                        send_messages=True,
                        read_message_history=True
                    ),
                    interaction.user: PermissionOverwrite(
                        read_messages=True,
                        send_messages=True,
                        manage_channels=True,
                        manage_messages=True
                    )
                }
                
                channel = await category.create_text_channel(
                    name=f"🏆・team-{self.team_name.value.lower().replace(' ', '-')}",
                    overwrites=overwrites,
                    reason=f"CTF team channel for {self.team_name.value}"
                )
                
                # Create inbox thread
                welcome_msg = await channel.send(
                    f"Welcome to **{self.team_name.value}**! 🎉\n\n"
                    f"This is your team's private channel. Use `/ctf manage_team` to access the management panel."
                )
                
                inbox_thread = await channel.create_thread(
                    name="📥 Team Inbox",
                    message=welcome_msg,
                    auto_archive_duration=10080,  # 1 week
                    reason="Team inbox for applications and notifications"
                )
                
                # Create team in database
                team = Team(
                    name=self.team_name.value,
                    description=self.description.value or None,
                    owner_id=interaction.user.id,
                    channel_id=channel.id,
                    inbox_thread_id=inbox_thread.id,
                    is_recruiting=True
                )
                
                session.add(team)
                await session.flush()  # Get team ID
                
                # Update profile
                profile.team_id = team.id
                await session.commit()
                
                # Assign team role to owner
                member = guild.get_member(interaction.user.id)
                await member.add_roles(team_role, reason="Team owner")
                
                # Post management panel in channel
                mgmt_embed = Embed(
                    title="⚙️ Team Management",
                    description=f"Welcome to **{team.name}**!\n\n"
                               f"As the team owner, you can manage your team using `/ctf manage_team`.",
                    color=Color.blue()
                )
                mgmt_embed.add_field(
                    name="Quick Actions",
                    value="• `/ctf manage_team` - Open management panel\n"
                          "• `/ctf team_stats` - View team statistics\n"
                          "• `/ctf teams` - Browse other teams",
                    inline=False
                )
                
                await channel.send(embed=mgmt_embed)
                
                # Success message
                await interaction.followup.send(
                    f"✅ Team **{self.team_name.value}** created successfully!\n"
                    f"Channel: {channel.mention}",
                    ephemeral=True
                )
                
            except Exception as e:
                await interaction.followup.send(
                    f"❌ Error creating team: {str(e)}\nPlease contact an administrator.",
                    ephemeral=True
                )
                # Rollback
                await session.rollback()
                raise


# ============================================================================
# Team Browsing and Applications
# ============================================================================

class TeamListView(ui.View):
    """Paginated view for browsing teams."""
    
    def __init__(self, teams: List[Team], user_id: int, page: int = 0):
        super().__init__(timeout=300)
        self.teams = teams
        self.user_id = user_id
        self.page = page
        self.teams_per_page = 5
        self.total_pages = (len(teams) + self.teams_per_page - 1) // self.teams_per_page
        
        # Update button states
        self.children[0].disabled = (page == 0)
        self.children[1].disabled = (page >= self.total_pages - 1)
    
    async def send(self, interaction: Interaction):
        """Send the team list view."""
        embed = self.create_embed(interaction)
        await interaction.response.send_message(embed=embed, view=self, ephemeral=True)
    
    def create_embed(self, interaction: Interaction) -> Embed:
        """Create embed for current page."""
        embed = Embed(
            title="🏆 Available CTF Teams",
            description=f"Page {self.page + 1}/{self.total_pages}",
            color=Color.blue()
        )
        
        start_idx = self.page * self.teams_per_page
        end_idx = start_idx + self.teams_per_page
        page_teams = self.teams[start_idx:end_idx]
        
        for team in page_teams:
            # Get owner
            owner = interaction.guild.get_member(team.owner_id)
            owner_name = owner.display_name if owner else f"User ID: {team.owner_id}"
            
            team_info = f"**Owner:** {owner_name}\n"
            team_info += f"**Recruiting:** {'✅ Open' if team.is_recruiting else '❌ Closed'}\n"
            if team.description:
                team_info += f"\n{team.description[:150]}"
            
            embed.add_field(
                name=f"🏆 {team.name}",
                value=team_info,
                inline=False
            )
        
        embed.set_footer(text=f"Total teams: {len(self.teams)} | Use the buttons to apply")
        
        return embed
    
    @ui.button(label="◀️ Previous", style=ButtonStyle.grey)
    async def previous_page(self, interaction: Interaction, button: ui.Button):
        """Go to previous page."""
        if self.page > 0:
            self.page -= 1
            self.children[0].disabled = (self.page == 0)
            self.children[1].disabled = False
            self.children[2].disabled = False
            
            embed = self.create_embed(interaction)
            await interaction.response.edit_message(embed=embed, view=self)
    
    @ui.button(label="Next ▶️", style=ButtonStyle.grey)
    async def next_page(self, interaction: Interaction, button: ui.Button):
        """Go to next page."""
        if self.page < self.total_pages - 1:
            self.page += 1
            self.children[0].disabled = False
            self.children[1].disabled = (self.page >= self.total_pages - 1)
            self.children[2].disabled = False
            
            embed = self.create_embed(interaction)
            await interaction.response.edit_message(embed=embed, view=self)
    
    @ui.button(label="📝 Apply to Team", style=ButtonStyle.green)
    async def apply_to_team(self, interaction: Interaction, button: ui.Button):
        """Apply to a team."""
        # Show team select
        view = SelectTeamToApplyView(self.teams, self.user_id)
        await interaction.response.send_message(
            "Select a team to apply to:",
            view=view,
            ephemeral=True
        )


class SelectTeamToApplyView(ui.View):
    """View for selecting a team to apply to."""
    
    def __init__(self, teams: List[Team], user_id: int):
        super().__init__(timeout=300)
        self.user_id = user_id
        
        # Create select menu with teams
        options = [
            SelectOption(
                label=team.name[:100],  # Discord limit
                description=team.description[:100] if team.description else "No description",
                value=str(team.id)
            )
            for team in teams[:25]  # Discord limit
        ]
        
        select = ui.Select(placeholder="Choose a team...", options=options)
        select.callback = self.team_selected
        self.add_item(select)
    
    async def team_selected(self, interaction: Interaction):
        """Handle team selection."""
        team_id = int(self.children[0].values[0])
        
        async with AsyncSessionLocal() as session:
            # Check if user is on a team
            result = await session.execute(
                select(PlayerProfile).where(PlayerProfile.user_id == self.user_id)
            )
            profile = result.scalar_one_or_none()
            
            if profile and profile.team_id:
                await interaction.response.send_message(
                    "❌ You're already on a team. Leave it first.",
                    ephemeral=True
                )
                return
            
            # Check if already applied
            result = await session.execute(
                select(TeamApplication).where(
                    TeamApplication.team_id == team_id,
                    TeamApplication.applicant_id == self.user_id,
                    TeamApplication.status == 'pending'
                )
            )
            existing_app = result.scalar_one_or_none()
            
            if existing_app:
                await interaction.response.send_message(
                    "❌ You've already applied to this team. Wait for a response.",
                    ephemeral=True
                )
                return
            
            # Show application modal
            modal = ApplicationModal(team_id)
            await interaction.response.send_modal(modal)


class ApplicationModal(ui.Modal, title="Apply to Team"):
    """Modal for team application."""
    
    reason = ui.TextInput(
        label="Why do you want to join this team?",
        placeholder="Tell them about your skills, experience, and motivation...",
        required=True,
        style=TextStyle.paragraph,
        max_length=1000
    )
    
    def __init__(self, team_id: int):
        super().__init__()
        self.team_id = team_id
    
    async def on_submit(self, interaction: Interaction):
        async with AsyncSessionLocal() as session:
            # Get team
            result = await session.execute(
                select(Team).where(Team.id == self.team_id)
            )
            team = result.scalar_one_or_none()
            
            if not team:
                await interaction.response.send_message(
                    "❌ Team not found.",
                    ephemeral=True
                )
                return
            
            # Create application
            application = TeamApplication(
                team_id=self.team_id,
                applicant_id=interaction.user.id,
                reason=self.reason.value,
                status='pending'
            )
            
            session.add(application)
            await session.commit()
            
            # Notify team inbox
            try:
                bot = interaction.client
                inbox_thread = bot.get_channel(team.inbox_thread_id)
                
                if inbox_thread:
                    app_embed = Embed(
                        title="📨 New Team Application",
                        color=Color.green()
                    )
                    app_embed.add_field(name="Applicant", value=interaction.user.mention, inline=True)
                    # French timezone
                    fr_tz = pytz.timezone('Europe/Paris')
                    fr_time = datetime.now(pytz.UTC).astimezone(fr_tz)
                    app_embed.add_field(name="Date", value=f"<t:{int(fr_time.timestamp())}:R>", inline=True)
                    app_embed.add_field(name="Reason", value=self.reason.value, inline=False)
                    
                    view = ApplicationResponseView(application.id)
                    await inbox_thread.send(f"<@{team.owner_id}>", embed=app_embed, view=view)
            except Exception as e:
                print(f"Error notifying team: {e}")
            
            await interaction.response.send_message(
                f"✅ Application sent to **{team.name}**!\n"
                f"The team owner will review your application soon.",
                ephemeral=True
            )


class ApplicationResponseView(ui.View):
    """View for team owner to respond to application."""
    
    def __init__(self, application_id: int):
        super().__init__(timeout=None)  # Persistent
        self.application_id = application_id
    
    @ui.button(label="✅ Approve", style=ButtonStyle.green, custom_id="app_approve")
    async def approve(self, interaction: Interaction, button: ui.Button):
        """Approve the application."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(TeamApplication).where(TeamApplication.id == self.application_id)
            )
            application = result.scalar_one_or_none()
            
            if not application or application.status != 'pending':
                await interaction.response.send_message(
                    "❌ Application no longer pending.",
                    ephemeral=True
                )
                return
            
            # Get team
            result = await session.execute(
                select(Team).where(Team.id == application.team_id)
            )
            team = result.scalar_one()
            
            # Check if owner
            if team.owner_id != interaction.user.id:
                await interaction.response.send_message(
                    "❌ Only the team owner can respond to applications.",
                    ephemeral=True
                )
                return
            
            # Get applicant profile
            result = await session.execute(
                select(PlayerProfile).where(PlayerProfile.user_id == application.applicant_id)
            )
            profile = result.scalar_one_or_none()
            
            if not profile:
                await interaction.response.send_message(
                    "❌ Applicant profile not found.",
                    ephemeral=True
                )
                return
            
            # Check if applicant is already on a team
            if profile.team_id is not None:
                await interaction.response.send_message(
                    "❌ Applicant has already joined another team.",
                    ephemeral=True
                )
                return
            
            # Approve application
            application.status = 'approved'
            profile.team_id = team.id
            await session.commit()
            
            # Add team role
            try:
                guild = interaction.guild
                member = guild.get_member(application.applicant_id)
                team_role = next((r for r in guild.roles if r.name == f"CTF-{team.name}"), None)
                
                if member and team_role:
                    await member.add_roles(team_role, reason="Joined team")
                
                # Notify in team channel
                channel = interaction.client.get_channel(team.channel_id)
                if channel:
                    await channel.send(
                        f"🎉 Welcome {member.mention} to **{team.name}**!"
                    )
                
                # DM the applicant
                try:
                    await member.send(
                        f"🎉 Congratulations! Your application to **{team.name}** has been approved!\n"
                        f"Check out your team channel: <#{team.channel_id}>"
                    )
                except:
                    pass
            
            except Exception as e:
                print(f"Error adding role: {e}")
            
            # Disable buttons
            for child in self.children:
                child.disabled = True
            
            await interaction.response.edit_message(
                content=f"✅ Application approved by {interaction.user.mention}",
                view=self
            )
    
    @ui.button(label="❌ Deny", style=ButtonStyle.red, custom_id="app_deny")
    async def deny(self, interaction: Interaction, button: ui.Button):
        """Deny the application."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(TeamApplication).where(TeamApplication.id == self.application_id)
            )
            application = result.scalar_one_or_none()
            
            if not application or application.status != 'pending':
                await interaction.response.send_message(
                    "❌ Application no longer pending.",
                    ephemeral=True
                )
                return
            
            # Get team
            result = await session.execute(
                select(Team).where(Team.id == application.team_id)
            )
            team = result.scalar_one()
            
            # Check if owner
            if team.owner_id != interaction.user.id:
                await interaction.response.send_message(
                    "❌ Only the team owner can respond to applications.",
                    ephemeral=True
                )
                return
            
            # Deny application
            application.status = 'denied'
            await session.commit()
            
            # Disable buttons
            for child in self.children:
                child.disabled = True
            
            await interaction.response.edit_message(
                content=f"❌ Application denied by {interaction.user.mention}",
                view=self
            )


# ============================================================================
# Team Management Panel
# ============================================================================

class TeamManagementPanel(ui.View):
    """Main management panel for team owners."""
    
    def __init__(self, team_id: int):
        super().__init__(timeout=300)
        self.team_id = team_id
        
        # Create select menu
        options = [
            SelectOption(
                label="Edit Team Info",
                description="Change team name, description, or recruiting status",
                value="edit_info",
                emoji="✏️"
            ),
            SelectOption(
                label="Invite Member",
                description="Send an invitation to a user",
                value="invite",
                emoji="📤"
            ),
            SelectOption(
                label="Manage Members",
                description="View and manage team members",
                value="members",
                emoji="👥"
            ),
            SelectOption(
                label="View Applications",
                description="Review pending applications",
                value="applications",
                emoji="📨"
            ),
            SelectOption(
                label="View Invites",
                description="Check sent invitations",
                value="invites",
                emoji="📬"
            ),
            SelectOption(
                label="Transfer Ownership",
                description="Give ownership to another member",
                value="transfer",
                emoji="👑"
            ),
            SelectOption(
                label="Disband Team",
                description="Permanently delete the team",
                value="disband",
                emoji="🗑️"
            ),
        ]
        
        select = ui.Select(placeholder="Select an action...", options=options)
        select.callback = self.action_selected
        self.add_item(select)
    
    async def action_selected(self, interaction: Interaction):
        """Handle action selection."""
        action = self.children[0].values[0]
        
        if action == "edit_info":
            modal = EditTeamInfoModal(self.team_id)
            await interaction.response.send_modal(modal)
        
        elif action == "invite":
            view = InviteMemberView(self.team_id)
            await view.send(interaction)
        
        elif action == "members":
            await self.show_members(interaction)
        
        elif action == "applications":
            await self.show_applications(interaction)
        
        elif action == "invites":
            await self.show_invites(interaction)
        
        elif action == "transfer":
            await self.show_transfer_ownership(interaction)
        
        elif action == "disband":
            view = ConfirmDisbandView(self.team_id)
            await interaction.response.send_message(
                "⚠️ **WARNING**: This will permanently delete your team and archive the channel!\n\n"
                "Are you absolutely sure?",
                view=view,
                ephemeral=True
            )
    
    async def show_members(self, interaction: Interaction):
        """Show team members."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Team).where(Team.id == self.team_id)
            )
            team = result.scalar_one()
            
            # Get team members with auth data
            result = await session.execute(
                select(PlayerProfile, AuthenticatedUser)
                .join(AuthenticatedUser, AuthenticatedUser.user_id == PlayerProfile.user_id)
                .where(PlayerProfile.team_id == team.id)
            )
            member_data = result.all()
            
            embed = Embed(
                title=f"👥 {team.name} - Members",
                color=Color.blue()
            )
            
            member_list = []
            for member_profile, auth_user in member_data:
                user = interaction.guild.get_member(member_profile.user_id)
                if user:
                    owner_badge = " 👑" if member_profile.user_id == team.owner_id else ""
                    rootme = f" (`{auth_user.rootme_id}`)" if auth_user and auth_user.rootme_id else ""
                    member_list.append(f"• {user.mention}{owner_badge}{rootme}")
            
            if member_list:
                embed.description = "\n".join(member_list)
            else:
                embed.description = "No members"
            
            embed.set_footer(text=f"Total members: {len(member_data)}")
            
            # Add kick button if there are members other than owner
            kickable_members = [(m, a) for m, a in member_data if m.user_id != team.owner_id]
            if kickable_members:
                view = KickMemberView(self.team_id, kickable_members)
                await view.update_options(interaction)
                await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            else:
                await interaction.response.send_message(embed=embed, ephemeral=True)
    
    async def show_applications(self, interaction: Interaction):
        """Show pending applications."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(TeamApplication).where(
                    TeamApplication.team_id == self.team_id,
                    TeamApplication.status == 'pending'
                )
            )
            applications = result.scalars().all()
            
            if not applications:
                await interaction.response.send_message(
                    "ℹ️ No pending applications.",
                    ephemeral=True
                )
                return
            
            embed = Embed(
                title="📨 Pending Applications",
                description=f"You have {len(applications)} pending application(s).",
                color=Color.green()
            )
            
            for app in applications[:10]:  # Limit to 10
                user = interaction.guild.get_member(app.applicant_id)
                user_name = user.mention if user else f"User ID: {app.applicant_id}"
                
                embed.add_field(
                    name=user_name,
                    value=f"{app.reason[:200]}...\n\n*Check team inbox to respond*",
                    inline=False
                )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    async def show_invites(self, interaction: Interaction):
        """Show sent invitations."""
        async with AsyncSessionLocal() as session:
            # Get invites with authenticated user data
            result = await session.execute(
                select(TeamInvite, AuthenticatedUser).join(
                    AuthenticatedUser, 
                    AuthenticatedUser.user_id == TeamInvite.invitee_id
                ).where(
                    TeamInvite.team_id == self.team_id,
                    TeamInvite.status == 'pending'
                )
            )
            invite_data = result.all()
            
            if not invite_data:
                await interaction.response.send_message(
                    "ℹ️ No pending invitations.",
                    ephemeral=True
                )
                return
            
            embed = Embed(
                title="📬 Pending Invitations",
                description=f"You have {len(invite_data)} pending invitation(s).",
                color=Color.blue()
            )
            
            # French timezone
            fr_tz = pytz.timezone('Europe/Paris')
            
            for invite, auth_user in invite_data:
                # Get Discord member
                user = interaction.guild.get_member(auth_user.user_id)
                user_name = f"{auth_user.email} (ID: {auth_user.user_id})"
                
                # Convert to French timezone
                fr_time = invite.created_at.replace(tzinfo=pytz.UTC).astimezone(fr_tz)
                timestamp = int(fr_time.timestamp())
                
                embed.add_field(
                    name=user_name,
                    value=f"Sent <t:{timestamp}:R>",
                    inline=True
                )
            
            # Mention users outside the embed
            mentions = []
            for invite, auth_user in invite_data:
                user = interaction.guild.get_member(auth_user.user_id)
                if user:
                    mentions.append(user.mention)
            
            mention_text = " ".join(mentions) if mentions else ""
            content = f"**Invited users:** {mention_text}" if mention_text else ""
            
            await interaction.response.send_message(content=content, embed=embed, ephemeral=True)
    
    async def show_transfer_ownership(self, interaction: Interaction):
        """Show ownership transfer dialog."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Team).where(Team.id == self.team_id)
            )
            team = result.scalar_one()
            
            # Get other members with auth data
            result = await session.execute(
                select(PlayerProfile, AuthenticatedUser)
                .join(AuthenticatedUser, AuthenticatedUser.user_id == PlayerProfile.user_id)
                .where(PlayerProfile.team_id == team.id, PlayerProfile.user_id != team.owner_id)
            )
            other_members = result.all()
            
            if not other_members:
                await interaction.response.send_message(
                    "❌ No other members to transfer ownership to.",
                    ephemeral=True
                )
                return
            
            view = TransferOwnershipView(self.team_id, other_members)
            await view.update_options(interaction)
            await interaction.response.send_message(
                "👑 Select the new team owner:",
                view=view,
                ephemeral=True
            )


class EditTeamInfoModal(ui.Modal, title="Edit Team Info"):
    """Modal for editing team information."""
    
    team_name = ui.TextInput(
        label="Team Name",
        placeholder="Leave blank to keep current name",
        required=False,
        max_length=100
    )
    
    description = ui.TextInput(
        label="Description",
        placeholder="Leave blank to keep current description",
        required=False,
        style=TextStyle.paragraph,
        max_length=500
    )
    
    def __init__(self, team_id: int):
        super().__init__()
        self.team_id = team_id
    
    async def on_submit(self, interaction: Interaction):
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Team).where(Team.id == self.team_id)
            )
            team = result.scalar_one()
            
            changes = []
            
            # Update name if provided
            if self.team_name.value:
                # Check if name is taken
                result = await session.execute(
                    select(Team).where(
                        Team.name == self.team_name.value,
                        Team.id != self.team_id
                    )
                )
                existing = result.scalar_one_or_none()
                
                if existing:
                    await interaction.response.send_message(
                        f"❌ Team name `{self.team_name.value}` is already taken.",
                        ephemeral=True
                    )
                    return
                
                old_name = team.name
                team.name = self.team_name.value
                changes.append(f"Name: {old_name} → {self.team_name.value}")
                
                # Update team role name
                try:
                    guild = interaction.guild
                    old_role = next((r for r in guild.roles if r.name == f"CTF-{old_name}"), None)
                    if old_role:
                        await old_role.edit(name=f"CTF-{self.team_name.value}")
                except:
                    pass
                
                # Update channel name
                try:
                    channel = interaction.client.get_channel(team.channel_id)
                    if channel:
                        await channel.edit(name=f"🏆・team-{self.team_name.value.lower().replace(' ', '-')}")
                except:
                    pass
            
            # Update description if provided
            if self.description.value:
                team.description = self.description.value
                changes.append("Description updated")
            
            await session.commit()
            
            if changes:
                await interaction.response.send_message(
                    f"✅ Team updated!\n• " + "\n• ".join(changes),
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    "ℹ️ No changes made.",
                    ephemeral=True
                )


class InviteMemberView(ui.View):
    """View for inviting a member with user selection."""
    
    def __init__(self, team_id: int):
        super().__init__(timeout=300)
        self.team_id = team_id
    
    async def send(self, interaction: Interaction):
        """Send the invite member view."""
        async with AsyncSessionLocal() as session:
            # Get all authenticated users
            result = await session.execute(
                select(AuthenticatedUser).order_by(AuthenticatedUser.user_id)
            )
            users = result.scalars().all()
            
            if not users:
                await interaction.response.send_message(
                    "❌ No authenticated users found.",
                    ephemeral=True
                )
                return
            
            view = PaginatedUserSelectView(
                users=users,
                callback_func=self.invite_user,
                team_id=self.team_id
            )
            await view.send(interaction)
    
    async def invite_user(self, interaction: Interaction, user_id: int, team_id: int):
        """Handle user invitation."""
        async with AsyncSessionLocal() as session:
            # Get team
            result = await session.execute(
                select(Team).where(Team.id == team_id)
            )
            team = result.scalar_one()
            
            # Check if user already on a team
            result = await session.execute(
                select(PlayerProfile).where(PlayerProfile.user_id == user_id)
            )
            profile = result.scalar_one_or_none()
            
            if not profile:
                # Create profile
                profile = PlayerProfile(user_id=user_id)
                session.add(profile)
                await session.flush()
            
            if profile.team_id:
                target_user = interaction.guild.get_member(user_id)
                user_mention = target_user.mention if target_user else f"User ID: {user_id}"
                await interaction.response.send_message(
                    f"❌ {user_mention} is already on a team.",
                    ephemeral=True
                )
                return
            
            # Check if already invited
            result = await session.execute(
                select(TeamInvite).where(
                    TeamInvite.team_id == team_id,
                    TeamInvite.invitee_id == user_id,
                    TeamInvite.status == 'pending'
                )
            )
            existing_invite = result.scalar_one_or_none()
            
            if existing_invite:
                target_user = interaction.guild.get_member(user_id)
                user_mention = target_user.mention if target_user else f"User ID: {user_id}"
                await interaction.response.send_message(
                    f"❌ {user_mention} has already been invited.",
                    ephemeral=True
                )
                return
            
            # Create invite
            invite = TeamInvite(
                team_id=team_id,
                invitee_id=user_id,
                status='pending'
            )
            
            session.add(invite)
            await session.commit()
            
            # Send DM
            try:
                target_user = interaction.guild.get_member(user_id)
                if target_user:
                    dm_embed = Embed(
                        title="🎉 Team Invitation",
                        description=f"You've been invited to join **{team.name}**!",
                        color=Color.green()
                    )
                    if team.description:
                        dm_embed.add_field(name="About", value=team.description, inline=False)
                    
                    dm_embed.add_field(
                        name="Team Channel",
                        value=f"<#{team.channel_id}>",
                        inline=True
                    )
                    
                    view = InviteResponseView(invite.id)
                    await target_user.send(embed=dm_embed, view=view)
                    
                    await interaction.response.send_message(
                        f"✅ Invitation sent to {target_user.mention}!",
                        ephemeral=True
                    )
                else:
                    await interaction.response.send_message(
                        f"✅ Invitation created for User ID: {user_id}",
                        ephemeral=True
                    )
            
            except:
                await interaction.response.send_message(
                    f"✅ Invitation created, but couldn't send DM to User ID: {user_id}.\n"
                    f"They may have DMs disabled or left the server.",
                    ephemeral=True
                )


class InviteResponseView(ui.View):
    """View for responding to team invitation."""
    
    def __init__(self, invite_id: int):
        super().__init__(timeout=None)  # Persistent
        self.invite_id = invite_id
    
    @ui.button(label="✅ Accept", style=ButtonStyle.green, custom_id="invite_accept")
    async def accept(self, interaction: Interaction, button: ui.Button):
        """Accept the invitation."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(TeamInvite).where(TeamInvite.id == self.invite_id)
            )
            invite = result.scalar_one_or_none()
            
            if not invite or invite.status != 'pending':
                await interaction.response.send_message(
                    "❌ Invitation no longer valid.",
                    ephemeral=True
                )
                return
            
            # Get invitee profile
            result = await session.execute(
                select(PlayerProfile).where(PlayerProfile.user_id == invite.invitee_id)
            )
            profile = result.scalar_one_or_none()
            
            if not profile:
                await interaction.response.send_message(
                    "❌ Profile not found.",
                    ephemeral=True
                )
                return
            
            # Check if already on a team
            if profile.team_id:
                await interaction.response.send_message(
                    "❌ You're already on a team.",
                    ephemeral=True
                )
                return
            
            # Get team
            result = await session.execute(
                select(Team).where(Team.id == invite.team_id)
            )
            team = result.scalar_one()
            
            # Accept invite
            invite.status = 'accepted'
            profile.team_id = team.id
            await session.commit()
            
            # Add team role
            try:
                guild = interaction.guild
                member = guild.get_member(invite.invitee_id)
                team_role = next((r for r in guild.roles if r.name == f"CTF-{team.name}"), None)
                
                if member and team_role:
                    await member.add_roles(team_role, reason="Joined team")
                
                # Notify in team channel
                channel = interaction.client.get_channel(team.channel_id)
                if channel:
                    await channel.send(
                        f"🎉 Welcome {member.mention} to **{team.name}**!"
                    )
            
            except Exception as e:
                print(f"Error adding role: {e}")
            
            # Disable buttons
            for child in self.children:
                child.disabled = True
            
            await interaction.response.edit_message(
                content=f"✅ You've joined **{team.name}**!",
                view=self
            )
    
    @ui.button(label="❌ Decline", style=ButtonStyle.red, custom_id="invite_decline")
    async def decline(self, interaction: Interaction, button: ui.Button):
        """Decline the invitation."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(TeamInvite).where(TeamInvite.id == self.invite_id)
            )
            invite = result.scalar_one_or_none()
            
            if not invite or invite.status != 'pending':
                await interaction.response.send_message(
                    "❌ Invitation no longer valid.",
                    ephemeral=True
                )
                return
            
            # Decline invite
            invite.status = 'declined'
            await session.commit()
            
            # Disable buttons
            for child in self.children:
                child.disabled = True
            
            await interaction.response.edit_message(
                content="❌ Invitation declined.",
                view=self
            )


class KickMemberView(ui.View):
    """View for kicking a member."""
    
    def __init__(self, team_id: int, members: List[tuple]):
        super().__init__(timeout=300)
        self.team_id = team_id
        self.members = members
        
        # Create select menu
        select = ui.Select(placeholder="Select member to kick...", options=[])
        select.callback = self.member_selected
        self.add_item(select)
    
    async def update_options(self, interaction: Interaction):
        """Update select menu options with current guild members."""
        options = []
        for member_profile, auth_user in self.members[:25]:  # Discord limit
            user = interaction.guild.get_member(member_profile.user_id)
            display_name = user.display_name if user else f"User ID: {member_profile.user_id}"
            rootme_info = f" ({auth_user.rootme_id})" if auth_user and auth_user.rootme_id else " (No Root-Me)"
            
            options.append(SelectOption(
                label=display_name[:100],  # Discord limit
                description=f"Email: {auth_user.email if auth_user else 'Unknown'}{rootme_info}",
                value=str(member_profile.user_id)
            ))
        
        self.children[0].options = options
    
    async def member_selected(self, interaction: Interaction):
        """Handle member selection."""
        member_id = int(self.children[0].values[0])
        
        view = ConfirmKickView(self.team_id, member_id)
        member = interaction.guild.get_member(member_id)
        member_name = member.mention if member else f"User ID: {member_id}"
        
        await interaction.response.send_message(
            f"⚠️ Are you sure you want to kick {member_name}?",
            view=view,
            ephemeral=True
        )


class ConfirmKickView(ui.View):
    """Confirmation view for kicking a member."""
    
    def __init__(self, team_id: int, member_id: int):
        super().__init__(timeout=60)
        self.team_id = team_id
        self.member_id = member_id
    
    @ui.button(label="Confirm Kick", style=ButtonStyle.danger)
    async def confirm(self, interaction: Interaction, button: ui.Button):
        """Confirm kick."""
        async with AsyncSessionLocal() as session:
            # Get team
            result = await session.execute(
                select(Team).where(Team.id == self.team_id)
            )
            team = result.scalar_one()
            
            # Get member profile
            result = await session.execute(
                select(PlayerProfile).where(PlayerProfile.user_id == self.member_id)
            )
            profile = result.scalar_one_or_none()
            
            if not profile or profile.team_id != self.team_id:
                await interaction.response.send_message(
                    "❌ Member not found on this team.",
                    ephemeral=True
                )
                return
            
            # Remove from team
            profile.team_id = None
            await session.commit()
            
            # Remove team role
            try:
                guild = interaction.guild
                member = guild.get_member(self.member_id)
                team_role = next((r for r in guild.roles if r.name == f"CTF-{team.name}"), None)
                if team_role and member and team_role in member.roles:
                    await member.remove_roles(team_role, reason="Kicked from team")
                
                # DM the member
                try:
                    await member.send(
                        f"You've been removed from **{team.name}** by the team owner."
                    )
                except:
                    pass
                
                # Notify team channel
                channel = interaction.client.get_channel(team.channel_id)
                if channel:
                    await channel.send(
                        f"📤 {member.mention} has been removed from the team."
                    )
            
            except Exception as e:
                print(f"Error removing role: {e}")
            
            await interaction.response.send_message(
                f"✅ Member kicked from team.",
                ephemeral=True
            )
    
    @ui.button(label="Cancel", style=ButtonStyle.secondary)
    async def cancel(self, interaction: Interaction, button: ui.Button):
        """Cancel kick."""
        await interaction.response.send_message(
            "Kick cancelled.",
            ephemeral=True
        )


class TransferOwnershipView(ui.View):
    """View for transferring team ownership."""
    
    def __init__(self, team_id: int, members: List[tuple]):
        super().__init__(timeout=300)
        self.team_id = team_id
        self.members = members
        
        # Create select menu
        select = ui.Select(placeholder="Select new owner...", options=[])
        select.callback = self.member_selected
        self.add_item(select)
    
    async def update_options(self, interaction: Interaction):
        """Update select menu options with current guild members."""
        options = []
        for member_profile, auth_user in self.members[:25]:  # Discord limit
            user = interaction.guild.get_member(member_profile.user_id)
            display_name = user.display_name if user else f"User ID: {member_profile.user_id}"
            rootme_info = f" ({auth_user.rootme_id})" if auth_user and auth_user.rootme_id else " (No Root-Me)"
            
            options.append(SelectOption(
                label=display_name[:100],  # Discord limit
                description=f"Email: {auth_user.email if auth_user else 'Unknown'}{rootme_info}",
                value=str(member_profile.user_id)
            ))
        
        self.children[0].options = options
    
    async def member_selected(self, interaction: Interaction):
        """Handle member selection."""
        new_owner_id = int(self.children[0].values[0])
        
        view = ConfirmTransferView(self.team_id, new_owner_id)
        member = interaction.guild.get_member(new_owner_id)
        member_name = member.mention if member else f"User ID: {new_owner_id}"
        
        await interaction.response.send_message(
            f"⚠️ **WARNING**: This will transfer full ownership to {member_name}.\n\n"
            f"You will become a regular member and lose all owner privileges.\n\n"
            f"Are you absolutely sure?",
            view=view,
            ephemeral=True
        )


class ConfirmTransferView(ui.View):
    """Confirmation view for ownership transfer."""
    
    def __init__(self, team_id: int, new_owner_id: int):
        super().__init__(timeout=60)
        self.team_id = team_id
        self.new_owner_id = new_owner_id
    
    @ui.button(label="Confirm Transfer", style=ButtonStyle.danger)
    async def confirm(self, interaction: Interaction, button: ui.Button):
        """Confirm transfer."""
        async with AsyncSessionLocal() as session:
            # Get team
            result = await session.execute(
                select(Team).where(Team.id == self.team_id)
            )
            team = result.scalar_one()
            
            # Verify current owner
            if team.owner_id != interaction.user.id:
                await interaction.response.send_message(
                    "❌ Only the current owner can transfer ownership.",
                    ephemeral=True
                )
                return
            
            # Transfer ownership
            old_owner_id = team.owner_id
            team.owner_id = self.new_owner_id
            await session.commit()
            
            # Update channel permissions
            try:
                channel = interaction.client.get_channel(team.channel_id)
                if channel:
                    old_owner = interaction.guild.get_member(old_owner_id)
                    new_owner = interaction.guild.get_member(self.new_owner_id)
                    
                    if old_owner:
                        await channel.set_permissions(
                            old_owner,
                            read_messages=True,
                            send_messages=True
                        )
                    
                    if new_owner:
                        await channel.set_permissions(
                            new_owner,
                            read_messages=True,
                            send_messages=True,
                            manage_channels=True,
                            manage_messages=True
                        )
                    
                    # Announce in channel
                    await channel.send(
                        f"👑 Ownership of **{team.name}** has been transferred to {new_owner.mention}!"
                    )
            
            except Exception as e:
                print(f"Error updating permissions: {e}")
            
            await interaction.response.send_message(
                f"✅ Ownership transferred successfully!",
                ephemeral=True
            )
    
    @ui.button(label="Cancel", style=ButtonStyle.secondary)
    async def cancel(self, interaction: Interaction, button: ui.Button):
        """Cancel transfer."""
        await interaction.response.send_message(
            "Transfer cancelled.",
            ephemeral=True
        )


class ConfirmDisbandView(ui.View):
    """Confirmation view for team disbanding."""
    
    def __init__(self, team_id: int):
        super().__init__(timeout=60)
        self.team_id = team_id
    
    @ui.button(label="Yes, Disband Team", style=ButtonStyle.danger)
    async def confirm(self, interaction: Interaction, button: ui.Button):
        """Confirm disbanding."""
        await interaction.response.defer(ephemeral=True)
        
        async with AsyncSessionLocal() as session:
            # Get team
            result = await session.execute(
                select(Team).where(Team.id == self.team_id)
            )
            team = result.scalar_one_or_none()
            
            if not team:
                await interaction.followup.send(
                    "❌ Team not found.",
                    ephemeral=True
                )
                return
            
            # Verify owner
            if team.owner_id != interaction.user.id:
                await interaction.followup.send(
                    "❌ Only the team owner can disband the team.",
                    ephemeral=True
                )
                return
            
            try:
                # Remove all members from team
                for member_profile in team.members:
                    member_profile.team_id = None
                
                # Delete team role
                guild = interaction.guild
                team_role = next((r for r in guild.roles if r.name == f"CTF-{team.name}"), None)
                if team_role:
                    await team_role.delete(reason="Team disbanded")
                
                # Archive channel
                channel = interaction.client.get_channel(team.channel_id)
                if channel:
                    await channel.send(
                        f"⚠️ **{team.name}** has been disbanded by the owner.\n"
                        f"This channel will be archived."
                    )
                    # Move to archive category or delete
                    await channel.delete(reason="Team disbanded")
                
                # Delete team from database (cascade will handle related records)
                await session.delete(team)
                await session.commit()
                
                await interaction.followup.send(
                    f"✅ Team **{team.name}** has been disbanded.",
                    ephemeral=True
                )
            
            except Exception as e:
                await interaction.followup.send(
                    f"❌ Error disbanding team: {str(e)}",
                    ephemeral=True
                )
                raise
    
    @ui.button(label="Cancel", style=ButtonStyle.secondary)
    async def cancel(self, interaction: Interaction, button: ui.Button):
        """Cancel disbanding."""
        await interaction.response.send_message(
            "Team disbanding cancelled.",
            ephemeral=True
        )


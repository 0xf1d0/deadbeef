"""
UI components for authentication management.
Provides admin panels, modals, and views for managing users and professionals.
"""
from discord import ui, Interaction, Embed, Color, SelectOption, TextChannel, ButtonStyle, Member
from discord.ext import commands
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import datetime, timedelta

from db import AsyncSessionLocal
from db.models import AuthenticatedUser, Professional, ProfessionalCourseChannel, PendingAuth
from utils import ROLE_M1, ROLE_M2, ROLE_FI, ROLE_FA
from sqlalchemy import select as select_db


class AuthenticationAdminPanel(ui.View):
    """Main admin panel for authentication management."""
    
    def __init__(self):
        super().__init__(timeout=300)
        
        # Create select menu with all admin options
        options = [
            SelectOption(
                label="📊 View Statistics",
                description="Show authentication statistics",
                value="stats",
                emoji="📊"
            ),
            SelectOption(
                label="👥 View All Students",
                description="List all authenticated students",
                value="list_students",
                emoji="👥"
            ),
            SelectOption(
                label="👔 View All Professionals",
                description="List all registered professionals",
                value="list_professionals",
                emoji="👔"
            ),
            SelectOption(
                label="🔍 Search User",
                description="Search for a user by email or ID",
                value="search_user",
                emoji="🔍"
            ),
            SelectOption(
                label="➕ Register Professional",
                description="Add a new professional to the system",
                value="register_pro",
                emoji="➕"
            ),
            SelectOption(
                label="👁️ View Professional",
                description="View details of a specific professional",
                value="view_pro",
                emoji="👁️"
            ),
            SelectOption(
                label="🔑 Manage Course Access",
                description="Add/remove course access for a professional",
                value="manage_access",
                emoji="🔑"
            ),
            SelectOption(
                label="🗑️ Delete Professional",
                description="Remove a professional from the system",
                value="delete_pro",
                emoji="🗑️"
            ),
            SelectOption(
                label="❌ Deauthenticate User",
                description="Remove authentication from a user",
                value="deauth_user",
                emoji="❌"
            ),
            SelectOption(
                label="⏰ View Pending Auths",
                description="See pending authentication requests",
                value="pending_auths",
                emoji="⏰"
            ),
            SelectOption(
                label="🧹 Clear Expired Tokens",
                description="Remove expired authentication tokens",
                value="clear_tokens",
                emoji="🧹"
            ),
            SelectOption(
                label="🔄 Reset Roles",
                description="Remove M1/M2/FI/FA roles from all members",
                value="reset_roles",
                emoji="🔄"
            ),
        ]
        
        select = ui.Select(
            placeholder="Select an action...",
            options=options,
            custom_id="auth_admin_select"
        )
        select.callback = self.action_selected
        self.add_item(select)
    
    async def action_selected(self, interaction: Interaction):
        """Handle admin action selection."""
        action = self.children[0].values[0]
        
        if action == "stats":
            await self.show_stats(interaction)
        
        elif action == "list_students":
            await self.list_students(interaction)
        
        elif action == "list_professionals":
            await self.list_professionals(interaction)
        
        elif action == "search_user":
            modal = SearchUserModal()
            await interaction.response.send_modal(modal)
        
        elif action == "register_pro":
            modal = RegisterProfessionalModal()
            await interaction.response.send_modal(modal)
        
        elif action == "view_pro":
            # Open a select-based professional viewer instead of a modal with email
            view = ViewProfessionalSelectView()
            embed = Embed(
                title="👔 View Professional",
                description="Select a professional to view details.",
                color=Color.blue()
            )
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        
        elif action == "manage_access":
            view = ManageCourseAccessView()
            embed = Embed(
                title="🔑 Manage Course Access",
                description="Choose an action:",
                color=Color.blue()
            )
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        
        elif action == "delete_pro":
            modal = DeleteProfessionalModal()
            await interaction.response.send_modal(modal)
        
        elif action == "deauth_user":
            modal = DeauthenticateUserModal()
            await interaction.response.send_modal(modal)
        
        elif action == "pending_auths":
            await self.show_pending_auths(interaction)
        
        elif action == "clear_tokens":
            await self.clear_expired_tokens(interaction)
        
        elif action == "reset_roles":
            view = ResetRolesView()
            embed = Embed(
                title="🔄 Reset Roles",
                description="Select which role to remove from all members:",
                color=Color.orange()
            )
            embed.add_field(
                name="⚠️ Warning",
                value="This will remove the selected role from ALL members in the server. This action cannot be undone.",
                inline=False
            )
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    async def show_stats(self, interaction: Interaction):
        """Show authentication statistics."""
        async with AsyncSessionLocal() as session:
            # Count authenticated users
            student_count = await session.execute(
                select(func.count(AuthenticatedUser.user_id)).where(
                    AuthenticatedUser.user_type == 'student'
                )
            )
            total_students = student_count.scalar() or 0
            
            pro_count = await session.execute(
                select(func.count(Professional.id))
            )
            total_pros = pro_count.scalar() or 0
            
            # Count by grade and path
            m1_count = await session.execute(
                select(func.count(AuthenticatedUser.user_id)).where(
                    AuthenticatedUser.grade_level == 'M1'
                )
            )
            m1_total = m1_count.scalar() or 0
            
            m2_count = await session.execute(
                select(func.count(AuthenticatedUser.user_id)).where(
                    AuthenticatedUser.grade_level == 'M2'
                )
            )
            m2_total = m2_count.scalar() or 0
            
            fi_count = await session.execute(
                select(func.count(AuthenticatedUser.user_id)).where(
                    AuthenticatedUser.formation_type == 'FI'
                )
            )
            fi_total = fi_count.scalar() or 0
            
            fa_count = await session.execute(
                select(func.count(AuthenticatedUser.user_id)).where(
                    AuthenticatedUser.formation_type == 'FA'
                )
            )
            fa_total = fa_count.scalar() or 0
            
            # Count pending auths
            pending_count = await session.execute(
                select(func.count(PendingAuth.id))
            )
            total_pending = pending_count.scalar() or 0
            
            embed = Embed(
                title="📊 Authentication Statistics",
                description="Overview of the authentication system:",
                color=Color.blue()
            )
            
            embed.add_field(
                name="👥 Total Users",
                value=f"**Students:** {total_students}\n**Professionals:** {total_pros}",
                inline=False
            )
            
            embed.add_field(
                name="🎓 Students by Grade",
                value=f"**M1:** {m1_total}\n**M2:** {m2_total}",
                inline=True
            )
            
            embed.add_field(
                name="📚 Students by Path",
                value=f"**FI (Formation Initiale):** {fi_total}\n**FA (Formation Alternance):** {fa_total}",
                inline=True
            )
            
            embed.add_field(
                name="⏰ Pending Authentications",
                value=f"{total_pending} request(s)",
                inline=False
            )
            
            embed.set_footer(text=f"Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    async def list_students(self, interaction: Interaction):
        """List all authenticated students."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(AuthenticatedUser).where(
                    AuthenticatedUser.user_type == 'student'
                ).order_by(AuthenticatedUser.authenticated_at.desc())
            )
            students = result.scalars().all()
            
            if not students:
                await interaction.response.send_message(
                    "ℹ️ No authenticated students found.",
                    ephemeral=True
                )
                return
            
            # Paginate if there are many students
            students_per_page = 10
            total_pages = (len(students) + students_per_page - 1) // students_per_page
            
            view = StudentListView(students, page=0, total_pages=total_pages)
            embed = view.create_embed()
            
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    async def list_professionals(self, interaction: Interaction):
        """List all registered professionals."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Professional))
            professionals = result.scalars().all()
            
            if not professionals:
                await interaction.response.send_message(
                    "ℹ️ No professionals registered yet.",
                    ephemeral=True
                )
                return
            
            embed = Embed(
                title="👔 Registered Professionals",
                description=f"Total: {len(professionals)}",
                color=Color.blue()
            )
            
            for pro in professionals[:25]:  # Discord embed field limit
                # Count course channels
                course_count = len(pro.course_channels)
                
                # Check if authenticated
                result_user = await session.execute(
                    select(AuthenticatedUser).where(
                        AuthenticatedUser.email == pro.email,
                        AuthenticatedUser.user_type == 'professional'
                    )
                )
                auth_user = result_user.scalar_one_or_none()
                
                status = "✅ Authenticated" if auth_user else "⏳ Not authenticated"
                
                name = f"{pro.first_name or ''} {pro.last_name or ''}".strip() or "N/A"
                
                embed.add_field(
                    name=f"📧 {pro.email}",
                    value=f"**Name:** {name}\n**Courses:** {course_count}\n**Status:** {status}",
                    inline=False
                )
            
            if len(professionals) > 25:
                embed.set_footer(text=f"Showing first 25 of {len(professionals)} professionals")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    async def show_pending_auths(self, interaction: Interaction):
        """Show pending authentication requests."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(PendingAuth).order_by(PendingAuth.created_at.desc())
            )
            pending = result.scalars().all()
            
            if not pending:
                await interaction.response.send_message(
                    "ℹ️ No pending authentication requests.",
                    ephemeral=True
                )
                return
            
            embed = Embed(
                title="⏰ Pending Authentication Requests",
                description=f"Total: {len(pending)}",
                color=Color.orange()
            )
            
            now = datetime.now()
            
            for auth in pending[:25]:  # Discord embed field limit
                user = interaction.guild.get_member(auth.user_id)
                user_name = user.mention if user else f"User ID: {auth.user_id}"
                
                # Calculate time remaining
                expires_at = auth.created_at + timedelta(minutes=15)
                time_left = expires_at - now
                
                if time_left.total_seconds() <= 0:
                    status = "⏱️ Expired"
                else:
                    minutes_left = int(time_left.total_seconds() / 60)
                    status = f"⏳ {minutes_left} min left"
                
                embed.add_field(
                    name=f"{user_name}",
                    value=f"**Email:** {auth.email}\n"
                          f"**Type:** {auth.user_type.capitalize()}\n"
                          f"**Status:** {status}\n"
                          f"**Created:** <t:{int(auth.created_at.timestamp())}:R>",
                    inline=False
                )
            
            if len(pending) > 25:
                embed.set_footer(text=f"Showing first 25 of {len(pending)} requests")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    async def clear_expired_tokens(self, interaction: Interaction):
        """Clear expired authentication tokens."""
        async with AsyncSessionLocal() as session:
            # Get expired tokens (older than 15 minutes)
            cutoff_time = datetime.now() - timedelta(minutes=15)
            
            result = await session.execute(
                select(PendingAuth).where(PendingAuth.created_at < cutoff_time)
            )
            expired = result.scalars().all()
            
            count = len(expired)
            
            if count == 0:
                await interaction.response.send_message(
                    "ℹ️ No expired tokens to clear.",
                    ephemeral=True
                )
                return
            
            # Delete expired tokens
            for token in expired:
                await session.delete(token)
            
            await session.commit()
            
            await interaction.response.send_message(
                f"✅ Cleared {count} expired authentication token(s).",
                ephemeral=True
            )


class StudentListView(ui.View):
    """Paginated view for student list."""
    
    def __init__(self, students: List[AuthenticatedUser], page: int = 0, total_pages: int = 1):
        super().__init__(timeout=300)
        self.students = students
        self.page = page
        self.total_pages = total_pages
        self.students_per_page = 10
        
        # Update button states
        self.children[0].disabled = (page == 0)
        self.children[1].disabled = (page >= total_pages - 1)
    
    def create_embed(self) -> Embed:
        """Create embed for current page."""
        embed = Embed(
            title="👥 Authenticated Students",
            description=f"Page {self.page + 1}/{self.total_pages}",
            color=Color.green()
        )
        
        start_idx = self.page * self.students_per_page
        end_idx = start_idx + self.students_per_page
        page_students = self.students[start_idx:end_idx]
        
        for student in page_students:
            user_mention = f"<@{student.user_id}>"
            
            embed.add_field(
                name=f"{user_mention}",
                value=f"**Email:** {student.email}\n"
                      f"**Student ID:** {student.student_id or 'N/A'}\n"
                      f"**Grade:** {student.grade_level or 'N/A'}\n"
                      f"**Path:** {student.formation_type or 'N/A'}\n"
                      f"**Authenticated:** <t:{int(student.authenticated_at.timestamp())}:R>",
                inline=False
            )
        
        embed.set_footer(text=f"Total students: {len(self.students)}")
        
        return embed
    
    @ui.button(label="◀️ Previous", style=ButtonStyle.grey)
    async def previous_page(self, interaction: Interaction, button: ui.Button):
        """Go to previous page."""
        if self.page > 0:
            self.page -= 1
            self.children[0].disabled = (self.page == 0)
            self.children[1].disabled = False
            
            embed = self.create_embed()
            await interaction.response.edit_message(embed=embed, view=self)
    
    @ui.button(label="Next ▶️", style=ButtonStyle.grey)
    async def next_page(self, interaction: Interaction, button: ui.Button):
        """Go to next page."""
        if self.page < self.total_pages - 1:
            self.page += 1
            self.children[0].disabled = False
            self.children[1].disabled = (self.page >= self.total_pages - 1)
            
            embed = self.create_embed()
            await interaction.response.edit_message(embed=embed, view=self)


class SearchUserModal(ui.Modal, title="Search User"):
    """Modal for searching users."""
    
    search_term = ui.TextInput(
        label="Email or Student ID",
        placeholder="Enter email or student ID",
        required=True,
        max_length=100
    )
    
    async def on_submit(self, interaction: Interaction):
        async with AsyncSessionLocal() as session:
            # Search by email first
            result = await session.execute(
                select(AuthenticatedUser).where(
                    AuthenticatedUser.email.ilike(f"%{self.search_term.value}%")
                )
            )
            users = result.scalars().all()
            
            # If no results, try student ID
            if not users:
                result = await session.execute(
                    select(AuthenticatedUser).where(
                        AuthenticatedUser.student_id.ilike(f"%{self.search_term.value}%")
                    )
                )
                users = result.scalars().all()
            
            if not users:
                await interaction.response.send_message(
                    f"❌ No users found matching '{self.search_term.value}'.",
                    ephemeral=True
                )
                return
            
            embed = Embed(
                title="🔍 Search Results",
                description=f"Found {len(users)} user(s):",
                color=Color.blue()
            )
            
            for user in users[:10]:  # Limit to 10 results
                user_mention = f"<@{user.user_id}>"
                
                embed.add_field(
                    name=f"{user_mention}",
                    value=f"**Email:** {user.email}\n"
                          f"**Type:** {user.user_type.capitalize()}\n"
                          f"**Student ID:** {user.student_id or 'N/A'}\n"
                          f"**Grade:** {user.grade_level or 'N/A'}\n"
                          f"**Path:** {user.formation_type or 'N/A'}",
                    inline=False
                )
            
            if len(users) > 10:
                embed.set_footer(text=f"Showing first 10 of {len(users)} results")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)


class RegisterProfessionalModal(ui.Modal, title="Register Professional"):
    """Modal for registering a new professional."""
    
    email = ui.TextInput(
        label="Email Address",
        placeholder="teacher@example.com",
        required=True,
        max_length=100
    )
    
    first_name = ui.TextInput(
        label="First Name (optional)",
        placeholder="John",
        required=False,
        max_length=50
    )
    
    last_name = ui.TextInput(
        label="Last Name (optional)",
        placeholder="Doe",
        required=False,
        max_length=50
    )
    
    async def on_submit(self, interaction: Interaction):
        async with AsyncSessionLocal() as session:
            # Check if professional already exists
            result = await session.execute(
                select(Professional).where(Professional.email == self.email.value)
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                await interaction.response.send_message(
                    f"❌ Professional with email {self.email.value} already exists.",
                    ephemeral=True
                )
                return
            
            # Create new professional
            professional = Professional(
                email=self.email.value,
                first_name=self.first_name.value or None,
                last_name=self.last_name.value or None
            )
            
            session.add(professional)
            await session.commit()
            
            embed = Embed(
                title="✅ Professional Registered",
                color=Color.green()
            )
            embed.add_field(name="Email", value=self.email.value, inline=False)
            if self.first_name.value or self.last_name.value:
                name = f"{self.first_name.value or ''} {self.last_name.value or ''}".strip()
                embed.add_field(name="Name", value=name, inline=False)
            embed.add_field(
                name="Next Steps",
                value="Use 'Manage Course Access' to grant access to course channels.",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)


class ViewProfessionalModal(ui.Modal, title="View Professional"):
    """Modal for viewing a professional's details."""
    
    email = ui.TextInput(
        label="Professional's Email",
        placeholder="teacher@example.com",
        required=True,
        max_length=100
    )
    
    async def on_submit(self, interaction: Interaction):
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Professional).where(Professional.email == self.email.value)
            )
            pro = result.scalar_one_or_none()
            
            if not pro:
                await interaction.response.send_message(
                    f"❌ Professional not found.",
                    ephemeral=True
                )
                return
            
            # Check if authenticated
            result_user = await session.execute(
                select(AuthenticatedUser).where(
                    AuthenticatedUser.email == pro.email,
                    AuthenticatedUser.user_type == 'professional'
                )
            )
            auth_user = result_user.scalar_one_or_none()
            
            embed = Embed(
                title="👔 Professional Details",
                color=Color.blue()
            )
            
            embed.add_field(name="Email", value=pro.email, inline=False)
            
            if pro.first_name or pro.last_name:
                name = f"{pro.first_name or ''} {pro.last_name or ''}".strip()
                embed.add_field(name="Name", value=name, inline=False)
            
            if auth_user:
                embed.add_field(
                    name="Discord User",
                    value=f"<@{auth_user.user_id}>",
                    inline=False
                )
                embed.add_field(
                    name="Authenticated",
                    value=f"<t:{int(auth_user.authenticated_at.timestamp())}:R>",
                    inline=False
                )
            else:
                embed.add_field(name="Status", value="⏳ Not authenticated yet", inline=False)
            
            # List course channels
            if pro.course_channels:
                channels_text = ""
                for cc in pro.course_channels:
                    channel = interaction.guild.get_channel(cc.channel_id)
                    if channel:
                        channel_name = cc.channel_name or channel.name
                        channels_text += f"• {channel.mention} ({channel_name})\n"
                    else:
                        channel_name = cc.channel_name or "Unknown"
                        channels_text += f"• Channel ID: {cc.channel_id} ({channel_name})\n"
                
                embed.add_field(
                    name=f"Course Channels ({len(pro.course_channels)})",
                    value=channels_text or "None",
                    inline=False
                )
            else:
                embed.add_field(name="Course Channels", value="None", inline=False)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)


class ViewProfessionalSelectView(ui.View):
    """Select-based view to display a professional's details."""
    
    def __init__(self):
        super().__init__(timeout=300)
        self.select = ui.Select(placeholder="Select professional...", options=[])
        self.select.callback = self.professional_selected
        self.add_item(self.select)
    
    async def _ensure_options(self, interaction: Interaction):
        if self.select.options:
            return
        async with AsyncSessionLocal() as session:
            result = await session.execute(select_db(Professional))
            pros = result.scalars().all()[:25]
            options = []
            for pro in pros:
                label = (f"{pro.first_name or ''} {pro.last_name or ''}".strip() or pro.email)[:100]
                options.append(SelectOption(label=label, value=pro.email, description=pro.email[:100]))
            self.select.options = options
            try:
                await interaction.edit_original_response(view=self)
            except Exception:
                pass
    
    async def professional_selected(self, interaction: Interaction):
        await self._ensure_options(interaction)
        email = self.select.values[0]
        async with AsyncSessionLocal() as session:
            result = await session.execute(select_db(Professional).where(Professional.email == email))
            pro = result.scalar_one_or_none()
            if not pro:
                await interaction.response.send_message("❌ Professional not found.", ephemeral=True)
                return
            # Check if authenticated
            result_user = await session.execute(
                select_db(AuthenticatedUser).where(
                    AuthenticatedUser.email == pro.email,
                    AuthenticatedUser.user_type == 'professional'
                )
            )
            auth_user = result_user.scalar_one_or_none()
            embed = Embed(title="👔 Professional Details", color=Color.blue())
            embed.add_field(name="Email", value=pro.email, inline=False)
            if pro.first_name or pro.last_name:
                name = f"{pro.first_name or ''} {pro.last_name or ''}".strip()
                embed.add_field(name="Name", value=name, inline=False)
            if auth_user:
                embed.add_field(name="Discord User", value=f"<@{auth_user.user_id}>", inline=False)
                embed.add_field(name="Authenticated", value=f"<t:{int(auth_user.authenticated_at.timestamp())}:R>", inline=False)
            else:
                embed.add_field(name="Status", value="⏳ Not authenticated yet", inline=False)
            if pro.course_channels:
                channels_text = ""
                for cc in pro.course_channels:
                    channel = interaction.guild.get_channel(cc.channel_id)
                    if channel:
                        channel_name = cc.channel_name or channel.name
                        channels_text += f"• {channel.mention} ({channel_name})\n"
                    else:
                        channel_name = cc.channel_name or "Unknown"
                        channels_text += f"• Channel ID: {cc.channel_id} ({channel_name})\n"
                embed.add_field(name=f"Course Channels ({len(pro.course_channels)})", value=channels_text or "None", inline=False)
            else:
                embed.add_field(name="Course Channels", value="None", inline=False)
            await interaction.response.edit_message(embed=embed, view=self)


class ManageCourseAccessView(ui.View):
    """View for managing course access."""
    
    def __init__(self):
        super().__init__(timeout=300)
    
    @ui.button(label="➕ Add Course Access", style=ButtonStyle.green)
    async def add_access(self, interaction: Interaction, button: ui.Button):
        """Add course access (select professional and channel)."""
        # Preload professional options (max 25)
        from sqlalchemy import select as select_db
        options = []
        async with AsyncSessionLocal() as session:
            result = await session.execute(select_db(Professional))
            pros = result.scalars().all()[:25]
            for pro in pros:
                label = (f"{pro.first_name or ''} {pro.last_name or ''}".strip() or pro.email)[:100]
                options.append(SelectOption(label=label, value=pro.email, description=pro.email[:100]))
        view = AddCourseAccessView(options)
        embed = Embed(
            title="➕ Add Course Access",
            description="Select a professional and a course channel, then click Confirm.",
            color=Color.green()
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @ui.button(label="➖ Remove Course Access", style=ButtonStyle.red)
    async def remove_access(self, interaction: Interaction, button: ui.Button):
        """Remove course access (select professional and channel)."""
        # Preload professional options (max 25)
        from sqlalchemy import select as select_db
        options = []
        async with AsyncSessionLocal() as session:
            result = await session.execute(select_db(Professional))
            pros = result.scalars().all()[:25]
            for pro in pros:
                label = (f"{pro.first_name or ''} {pro.last_name or ''}".strip() or pro.email)[:100]
                options.append(SelectOption(label=label, value=pro.email, description=pro.email[:100]))
        view = RemoveCourseAccessView(options)
        embed = Embed(
            title="➖ Remove Course Access",
            description="Select a professional and a course channel, then click Confirm.",
            color=Color.red()
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class AddCourseAccessView(ui.View):
    """Select-based view to add course access to a professional."""
    
    def __init__(self, professional_options: list[SelectOption]):
        super().__init__(timeout=300)
        self.selected_professional_email: Optional[str] = None
        self.selected_channel_id: Optional[int] = None
        
        professional_select = ui.Select(placeholder="Select professional...", options=professional_options)
        professional_select.callback = self.professional_selected
        self.add_item(professional_select)
        
        channel_select = ui.ChannelSelect(placeholder="Select course channel...", min_values=1, max_values=1)
        channel_select.callback = self.channel_selected
        self.add_item(channel_select)
        
        self.confirm_button = ui.Button(label="Confirm", style=ButtonStyle.success, disabled=True)
        self.confirm_button.callback = self.confirm
        self.add_item(self.confirm_button)
    
    async def on_timeout(self) -> None:
        for item in self.children:
            item.disabled = True
    
    async def professional_selected(self, interaction: Interaction):
        self.selected_professional_email = self.children[0].values[0]
        self._update_confirm_state()
        await interaction.response.edit_message(view=self)
    
    async def channel_selected(self, interaction: Interaction):
        channel = self.children[1].values[0]
        self.selected_channel_id = channel.id
        self._update_confirm_state()
        await interaction.response.edit_message(view=self)
    
    def _update_confirm_state(self):
        self.confirm_button.disabled = not (self.selected_professional_email and self.selected_channel_id)
    
    async def confirm(self, interaction: Interaction):
        if not (self.selected_professional_email and self.selected_channel_id):
            await interaction.response.send_message("❌ Please select a professional and a channel.", ephemeral=True)
            return
        async with AsyncSessionLocal() as session:
            # Get professional
            result = await session.execute(
                select_db(Professional).where(Professional.email == self.selected_professional_email)
            )
            pro = result.scalar_one_or_none()
            if not pro:
                await interaction.response.send_message("❌ Professional not found.", ephemeral=True)
                return
            channel = interaction.guild.get_channel(self.selected_channel_id)
            if not channel:
                await interaction.response.send_message("❌ Channel not found in this server.", ephemeral=True)
                return
            # Check existing
            result = await session.execute(
                select_db(ProfessionalCourseChannel).where(
                    ProfessionalCourseChannel.professional_id == pro.id,
                    ProfessionalCourseChannel.channel_id == self.selected_channel_id
                )
            )
            existing = result.scalar_one_or_none()
            if existing:
                await interaction.response.send_message(f"❌ Professional already has access to {channel.mention}.", ephemeral=True)
                return
            # Create mapping
            mapping = ProfessionalCourseChannel(
                professional_id=pro.id,
                channel_id=self.selected_channel_id,
                channel_name=channel.name
            )
            session.add(mapping)
            await session.commit()
            # Grant perms if authenticated
            result_user = await session.execute(
                select_db(AuthenticatedUser).where(
                    AuthenticatedUser.email == self.selected_professional_email,
                    AuthenticatedUser.user_type == 'professional'
                )
            )
            auth_user = result_user.scalar_one_or_none()
            granted = False
            if auth_user:
                member = interaction.guild.get_member(auth_user.user_id)
                if member:
                    try:
                        await channel.set_permissions(member, view_channel=True)
                        granted = True
                    except Exception as e:
                        print(f"Error granting permissions: {e}")
            embed = Embed(title="✅ Course Access Added", color=Color.green())
            embed.add_field(name="Professional", value=self.selected_professional_email, inline=False)
            embed.add_field(name="Channel", value=channel.mention, inline=False)
            if granted:
                embed.add_field(name="Permissions", value="🔓 Discord permissions granted", inline=False)
            await interaction.response.edit_message(content=None, embed=embed, view=None)


class RemoveCourseAccessView(ui.View):
    """Select-based view to remove course access from a professional."""
    
    def __init__(self, professional_options: list[SelectOption]):
        super().__init__(timeout=300)
        self.selected_professional_email: Optional[str] = None
        self.selected_channel_id: Optional[int] = None
        
        professional_select = ui.Select(placeholder="Select professional...", options=professional_options)
        professional_select.callback = self.professional_selected
        self.add_item(professional_select)
        
        channel_select = ui.ChannelSelect(placeholder="Select course channel...", min_values=1, max_values=1)
        channel_select.callback = self.channel_selected
        self.add_item(channel_select)
        
        self.confirm_button = ui.Button(label="Confirm", style=ButtonStyle.danger, disabled=True)
        self.confirm_button.callback = self.confirm
        self.add_item(self.confirm_button)
    
    async def on_timeout(self) -> None:
        for item in self.children:
            item.disabled = True
    
    async def professional_selected(self, interaction: Interaction):
        self.selected_professional_email = self.children[0].values[0]
        self._update_confirm_state()
        await interaction.response.edit_message(view=self)
    
    async def channel_selected(self, interaction: Interaction):
        channel = self.children[1].values[0]
        self.selected_channel_id = channel.id
        self._update_confirm_state()
        await interaction.response.edit_message(view=self)
    
    def _update_confirm_state(self):
        self.confirm_button.disabled = not (self.selected_professional_email and self.selected_channel_id)
    
    async def confirm(self, interaction: Interaction):
        if not (self.selected_professional_email and self.selected_channel_id):
            await interaction.response.send_message("❌ Please select a professional and a channel.", ephemeral=True)
            return
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select_db(Professional).where(Professional.email == self.selected_professional_email)
            )
            pro = result.scalar_one_or_none()
            if not pro:
                await interaction.response.send_message("❌ Professional not found.", ephemeral=True)
                return
            channel = interaction.guild.get_channel(self.selected_channel_id)
            result = await session.execute(
                select_db(ProfessionalCourseChannel).where(
                    ProfessionalCourseChannel.professional_id == pro.id,
                    ProfessionalCourseChannel.channel_id == self.selected_channel_id
                )
            )
            course_channel = result.scalar_one_or_none()
            if not course_channel:
                await interaction.response.send_message("❌ Professional doesn't have access to this channel.", ephemeral=True)
                return
            # Remove permissions if authenticated
            result_user = await session.execute(
                select_db(AuthenticatedUser).where(
                    AuthenticatedUser.email == self.selected_professional_email,
                    AuthenticatedUser.user_type == 'professional'
                )
            )
            auth_user = result_user.scalar_one_or_none()
            removed = False
            if auth_user and channel:
                member = interaction.guild.get_member(auth_user.user_id)
                if member:
                    try:
                        await channel.set_permissions(member, overwrite=None)
                        removed = True
                    except Exception as e:
                        print(f"Error removing permissions: {e}")
            await session.delete(course_channel)
            await session.commit()
            embed = Embed(title="✅ Course Access Removed", color=Color.orange())
            embed.add_field(name="Professional", value=self.selected_professional_email, inline=False)
            embed.add_field(name="Channel", value=channel.mention if channel else f"ID: {self.selected_channel_id}", inline=False)
            if removed:
                embed.add_field(name="Permissions", value="🔒 Discord permissions removed", inline=False)
            await interaction.response.edit_message(content=None, embed=embed, view=None)


class DeleteProfessionalModal(ui.Modal, title="Delete Professional"):
    """Modal for deleting a professional."""
    
    email = ui.TextInput(
        label="Professional's Email",
        placeholder="teacher@example.com",
        required=True,
        max_length=100
    )
    
    async def on_submit(self, interaction: Interaction):
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Professional).where(Professional.email == self.email.value)
            )
            pro = result.scalar_one_or_none()
            
            if not pro:
                await interaction.response.send_message(
                    f"❌ Professional not found.",
                    ephemeral=True
                )
                return
            
            # Show confirmation
            view = ConfirmDeleteProfessionalView(pro.email, len(pro.course_channels))
            
            embed = Embed(
                title="⚠️ Confirm Deletion",
                description=f"Delete professional **{self.email.value}**?\n\n"
                           f"This will remove:\n"
                           f"• Professional record\n"
                           f"• {len(pro.course_channels)} course access(es)\n"
                           f"• Discord channel permissions\n\n"
                           f"**This action cannot be undone.**",
                color=Color.red()
            )
            
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class ConfirmDeleteProfessionalView(ui.View):
    """Confirmation view for deleting a professional."""
    
    def __init__(self, email: str, course_count: int):
        super().__init__(timeout=60)
        self.email = email
        self.course_count = course_count
    
    @ui.button(label="Confirm Delete", style=ButtonStyle.danger)
    async def confirm(self, interaction: Interaction, button: ui.Button):
        """Confirm deletion."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Professional).where(Professional.email == self.email)
            )
            pro = result.scalar_one_or_none()
            
            if not pro:
                await interaction.response.edit_message(
                    content="❌ Professional not found.",
                    embed=None,
                    view=None
                )
                return
            
            # Get the user who has this email
            result_user = await session.execute(
                select(AuthenticatedUser).where(
                    AuthenticatedUser.email == self.email,
                    AuthenticatedUser.user_type == 'professional'
                )
            )
            auth_user = result_user.scalar_one_or_none()
            
            # Remove permissions from all course channels
            removed_channels = []
            if auth_user:
                member = interaction.guild.get_member(auth_user.user_id)
                if member:
                    for course_channel in pro.course_channels:
                        channel = interaction.guild.get_channel(course_channel.channel_id)
                        if channel:
                            try:
                                await channel.set_permissions(member, overwrite=None)
                                removed_channels.append(channel.name)
                            except Exception as e:
                                print(f"Error removing permissions: {e}")
            
            # Delete the professional (cascade will delete course_channels)
            await session.delete(pro)
            await session.commit()
            
            message = f"✅ Professional {self.email} has been deleted."
            if removed_channels:
                message += f"\n\n🔒 Removed permissions from {len(removed_channels)} channel(s):\n• " + "\n• ".join(removed_channels)
            
            await interaction.response.edit_message(
                content=message,
                embed=None,
                view=None
            )
    
    @ui.button(label="Cancel", style=ButtonStyle.secondary)
    async def cancel(self, interaction: Interaction, button: ui.Button):
        """Cancel deletion."""
        await interaction.response.edit_message(
            content="Deletion cancelled.",
            embed=None,
            view=None
        )


class DeauthenticateUserModal(ui.Modal, title="Deauthenticate User"):
    """Modal for removing authentication from a user."""
    
    user_identifier = ui.TextInput(
        label="User Email or Student ID",
        placeholder="user@example.com or student ID",
        required=True,
        max_length=100
    )
    
    async def on_submit(self, interaction: Interaction):
        async with AsyncSessionLocal() as session:
            # Search by email first
            result = await session.execute(
                select(AuthenticatedUser).where(
                    AuthenticatedUser.email == self.user_identifier.value
                )
            )
            user = result.scalar_one_or_none()
            
            # If not found, try student ID
            if not user:
                result = await session.execute(
                    select(AuthenticatedUser).where(
                        AuthenticatedUser.student_id == self.user_identifier.value
                    )
                )
                user = result.scalar_one_or_none()
            
            if not user:
                await interaction.response.send_message(
                    f"❌ User not found.",
                    ephemeral=True
                )
                return
            
            # Show confirmation
            view = ConfirmDeauthView(user.user_id, user.email, user.user_type)
            
            member = interaction.guild.get_member(user.user_id)
            user_mention = member.mention if member else f"User ID: {user.user_id}"
            
            embed = Embed(
                title="⚠️ Confirm Deauthentication",
                description=f"Remove authentication from {user_mention}?\n\n"
                           f"**Email:** {user.email}\n"
                           f"**Type:** {user.user_type.capitalize()}\n\n"
                           f"This will remove their authentication record and associated roles.\n\n"
                           f"**This action cannot be undone.**",
                color=Color.orange()
            )
            
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class ConfirmDeauthView(ui.View):
    """Confirmation view for deauthenticating a user."""
    
    def __init__(self, user_id: int, email: str, user_type: str):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.email = email
        self.user_type = user_type
    
    @ui.button(label="Confirm Deauthenticate", style=ButtonStyle.danger)
    async def confirm(self, interaction: Interaction, button: ui.Button):
        """Confirm deauthentication."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(AuthenticatedUser).where(AuthenticatedUser.user_id == self.user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                await interaction.response.edit_message(
                    content="❌ User not found.",
                    embed=None,
                    view=None
                )
                return
            
            # Remove roles
            member = interaction.guild.get_member(self.user_id)
            removed_roles = []
            
            if member:
                roles_to_remove = []
                if user.grade_level == 'M1':
                    m1_role = interaction.guild.get_role(ROLE_M1.id)
                    if m1_role and m1_role in member.roles:
                        roles_to_remove.append(m1_role)
                elif user.grade_level == 'M2':
                    m2_role = interaction.guild.get_role(ROLE_M2.id)
                    if m2_role and m2_role in member.roles:
                        roles_to_remove.append(m2_role)
                
                if user.formation_type == 'FI':
                    fi_role = interaction.guild.get_role(ROLE_FI.id)
                    if fi_role and fi_role in member.roles:
                        roles_to_remove.append(fi_role)
                elif user.formation_type == 'FA':
                    fa_role = interaction.guild.get_role(ROLE_FA.id)
                    if fa_role and fa_role in member.roles:
                        roles_to_remove.append(fa_role)
                
                if roles_to_remove:
                    try:
                        await member.remove_roles(*roles_to_remove, reason="Deauthenticated by admin")
                        removed_roles = [role.name for role in roles_to_remove]
                    except Exception as e:
                        print(f"Error removing roles: {e}")
            
            # Delete authentication record
            await session.delete(user)
            await session.commit()
            
            message = f"✅ User <@{self.user_id}> has been deauthenticated."
            if removed_roles:
                message += f"\n\n🔒 Removed roles: {', '.join(removed_roles)}"
            
            await interaction.response.edit_message(
                content=message,
                embed=None,
                view=None
            )
    
    @ui.button(label="Cancel", style=ButtonStyle.secondary)
    async def cancel(self, interaction: Interaction, button: ui.Button):
        """Cancel deauthentication."""
        await interaction.response.edit_message(
            content="Deauthentication cancelled.",
            embed=None,
            view=None
        )


class ResetRolesView(ui.View):
    """View for resetting roles."""
    
    def __init__(self):
        super().__init__(timeout=300)
        
        options = [
            SelectOption(label="M1", description="Remove M1 role from all members", value="M1", emoji="🎓"),
            SelectOption(label="M2", description="Remove M2 role from all members", value="M2", emoji="🎓"),
            SelectOption(label="FI", description="Remove FI role from all members", value="FI", emoji="📚"),
            SelectOption(label="FA", description="Remove FA role from all members", value="FA", emoji="📚"),
        ]
        
        select = ui.Select(placeholder="Select role to reset...", options=options)
        select.callback = self.role_selected
        self.add_item(select)
    
    async def role_selected(self, interaction: Interaction):
        """Handle role selection."""
        role_type = self.children[0].values[0]
        
        # Get the role
        role_map = {
            'M1': ROLE_M1.id,
            'M2': ROLE_M2.id,
            'FI': ROLE_FI.id,
            'FA': ROLE_FA.id
        }
        
        role_id = role_map.get(role_type)
        role = interaction.guild.get_role(role_id)
        
        if not role:
            await interaction.response.send_message(
                f"❌ {role_type} role not found in this server.",
                ephemeral=True
            )
            return
        
        # Show confirmation
        view = ConfirmResetRolesView(role_type, role)
        
        embed = Embed(
            title="⚠️ Confirm Role Reset",
            description=f"Remove **{role.name}** role from all members?\n\n"
                       f"**Current members with this role:** {len(role.members)}\n\n"
                       f"**This action cannot be undone.**",
            color=Color.red()
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class ConfirmResetRolesView(ui.View):
    """Confirmation view for resetting roles."""
    
    def __init__(self, role_type: str, role):
        super().__init__(timeout=60)
        self.role_type = role_type
        self.role = role
    
    @ui.button(label="Confirm Reset", style=ButtonStyle.danger)
    async def confirm(self, interaction: Interaction, button: ui.Button):
        """Confirm role reset."""
        await interaction.response.defer(ephemeral=True)
        
        # Get all members with this role
        members_with_role = self.role.members
        count = 0
        
        for member in members_with_role:
            try:
                await member.remove_roles(self.role, reason=f"Role reset by admin")
                count += 1
            except Exception as e:
                print(f"Error removing role from {member}: {e}")
        
        await interaction.followup.send(
            f"✅ Removed **{self.role.name}** role from {count} member(s).",
            ephemeral=True
        )
    
    @ui.button(label="Cancel", style=ButtonStyle.secondary)
    async def cancel(self, interaction: Interaction, button: ui.Button):
        """Cancel role reset."""
        await interaction.response.edit_message(
            content="Role reset cancelled.",
            embed=None,
            view=None
        )


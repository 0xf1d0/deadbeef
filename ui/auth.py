"""
Authentication UI components.
Handles student and professional authentication with database storage.
"""
import re
from discord import ui, Interaction, ButtonStyle, Forbidden
from datetime import datetime, timedelta
from sqlalchemy import select
from typing import Optional

from db import AsyncSessionLocal
from db.models import AuthenticatedUser, Professional, PendingAuth
from utils import ROLE_FA, ROLE_FI, ROLE_PRO, ROLE_M1, ROLE_M2, ROLE_STUDENT, send_email, create_jwt, verify_jwt, ConfigManager
from utils.csv_parser import find_student_by_id
from api import RootMe

COOLDOWN_PERIOD = timedelta(hours=1)


class Authentication(ui.View):
    """Main authentication view with buttons for students, professionals, and profile linking."""
    
    def __init__(self):
        super().__init__(timeout=None)
    
    @ui.button(label="S'authentifier", style=ButtonStyle.success, emoji="<:upc_black:1367296895717736553>", custom_id="auth_main_button")
    async def authenticate(self, interaction: Interaction, _: ui.Button):
        """Handle authentication based on user's role."""
        user_roles = [role.id for role in interaction.user.roles]
        
        async with AsyncSessionLocal() as session:
            # Check if already authenticated
            result = await session.execute(
                select(AuthenticatedUser).where(AuthenticatedUser.user_id == interaction.user.id)
            )
            auth_user = result.scalar_one_or_none()
            
            if auth_user:
                await interaction.response.send_message(
                    "Vous êtes déjà authentifié.",
                    ephemeral=True
                )
                return
            
            # Check for pending authentication (allow token entry)
            result = await session.execute(
                select(PendingAuth).where(
                    PendingAuth.user_id == interaction.user.id,
                    PendingAuth.expires_at > datetime.now()
                )
            )
            pending = result.scalar_one_or_none()
            
            if pending:
                await interaction.response.send_modal(TokenModal())
                return
            
            # New authentication based on role
            if ROLE_PRO.id in user_roles:
                await interaction.response.send_modal(ProfessionalModal())
            elif ROLE_STUDENT.id in user_roles:
                await interaction.response.send_modal(StudentModal())
            else:
                await interaction.response.send_message(
                    "Vous n'avez pas le profil requis. Veuillez choisir un rôle (Étudiant ou Professionnel) avant de vous authentifier.",
                    ephemeral=True
                )
    
    @ui.button(label='Root-Me', style=ButtonStyle.primary, emoji="<:rootme:1366510489521356850>", custom_id="auth_rootme_button")
    async def rootme(self, interaction: Interaction, _: ui.Button):
        """Link Root-Me profile."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(AuthenticatedUser).where(AuthenticatedUser.user_id == interaction.user.id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                await interaction.response.send_message(
                    "❌ Vous devez d'abord vous authentifier.",
                    ephemeral=True
                )
                return
            
            modal = RootMeModal(user)
            await interaction.response.send_modal(modal)
    
    @ui.button(label='LinkedIn', style=ButtonStyle.secondary, emoji="<:linkedin:1366509373592961154>", custom_id="auth_linkedin_button")
    async def linkedin(self, interaction: Interaction, _: ui.Button):
        """Link LinkedIn profile."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(AuthenticatedUser).where(AuthenticatedUser.user_id == interaction.user.id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                await interaction.response.send_message(
                    "❌ Vous devez d'abord vous authentifier.",
                    ephemeral=True
                )
                return
            
            modal = LinkedinModal(user)
            await interaction.response.send_modal(modal)


class StudentModal(ui.Modal, title="Authentification Étudiant"):
    """Modal for student authentication (M1/M2)."""
    
    student_id = ui.TextInput(
        label="Numéro étudiant",
        placeholder="12345678",
        min_length=8,
        max_length=8
    )
    
    grade_level = ui.TextInput(
        label="Niveau (M1 ou M2)",
        placeholder="M1",
        min_length=2,
        max_length=2
    )
    
    async def on_submit(self, interaction: Interaction):
        """Process student authentication request."""
        grade = self.grade_level.value.upper()
        
        if grade not in ['M1', 'M2']:
            await interaction.response.send_message(
                "Niveau invalide. Veuillez entrer M1 ou M2.",
                ephemeral=True
            )
            return
        
        # Find student in CSV files
        student_info = find_student_by_id(self.student_id.value, grade)
        
        if not student_info:
            await interaction.response.send_message(
                f"Numéro étudiant invalide ou non trouvé dans les listes {grade}.",
                ephemeral=True
            )
            return
        
        await interaction.response.defer(ephemeral=True)
        
        async with AsyncSessionLocal() as session:
            # Check if already authenticated
            result = await session.execute(
                select(AuthenticatedUser).where(AuthenticatedUser.user_id == interaction.user.id)
            )
            if result.scalar_one_or_none():
                await interaction.followup.send(
                    "Vous êtes déjà authentifié.",
                    ephemeral=True
                )
                return
            
            # Create or update pending authentication
            result = await session.execute(
                select(PendingAuth).where(PendingAuth.user_id == interaction.user.id)
            )
            pending = result.scalar_one_or_none()
            
            # Generate JWT token
            token = create_jwt(student_info['email'])
            
            if pending:
                # Update existing
                pending.email = student_info['email']
                pending.token = token
                pending.user_type = 'student'
                pending.student_id = student_info['student_id']
                pending.grade_level = student_info['grade_level']
                pending.formation_type = student_info['formation_type']
                pending.first_name = student_info['first_name']
                pending.last_name = student_info['last_name']
                pending.created_at = datetime.now()
                pending.expires_at = datetime.now() + COOLDOWN_PERIOD
            else:
                # Create new
                pending = PendingAuth(
                    user_id=interaction.user.id,
                    email=student_info['email'],
                    token=token,
                    user_type='student',
                    student_id=student_info['student_id'],
                    grade_level=student_info['grade_level'],
                    formation_type=student_info['formation_type'],
                    first_name=student_info['first_name'],
                    last_name=student_info['last_name'],
                    created_at=datetime.now(),
                    expires_at=datetime.now() + COOLDOWN_PERIOD
                )
                session.add(pending)
            
            await session.commit()
            
            # Send email with token
            send_email(
                ConfigManager.get('email_object'),
                ConfigManager.get('email_body').format(token),
                student_info['email']
            )
            
            await interaction.followup.send(
                f"✉️ Mail envoyé à {student_info['email']}\n\nEntrez le jeton reçu en cliquant sur le bouton ci-dessous.",
                view=FeedbackView(),
                ephemeral=True
            )


class ProfessionalModal(ui.Modal, title="Authentification Professionnel"):
    """Modal for professional authentication."""
    
    email = ui.TextInput(
        label="Email",
        placeholder="prenom.nom@u-paris.fr",
        max_length=100
    )
    
    async def on_submit(self, interaction: Interaction):
        """Process professional authentication request."""
        await interaction.response.defer(ephemeral=True)
        
        async with AsyncSessionLocal() as session:
            # Check if already authenticated
            result = await session.execute(
                select(AuthenticatedUser).where(AuthenticatedUser.user_id == interaction.user.id)
            )
            if result.scalar_one_or_none():
                await interaction.followup.send(
                    "Vous êtes déjà authentifié.",
                    ephemeral=True
                )
                return
            
            # Check if professional exists in database
            result = await session.execute(
                select(Professional).where(Professional.email == self.email.value)
            )
            pro = result.scalar_one_or_none()
            
            if not pro:
                await interaction.followup.send(
                    "Email non reconnu. Un administrateur doit d'abord enregistrer votre adresse email.",
                    ephemeral=True
                )
                return
            
            # Check if email already used by someone else
            result = await session.execute(
                select(AuthenticatedUser).where(AuthenticatedUser.email == self.email.value)
            )
            existing = result.scalar_one_or_none()
            
            if existing and existing.user_id != interaction.user.id:
                await interaction.followup.send(
                    "Cet email est déjà associé à un autre compte Discord.",
                    ephemeral=True
                )
                return
            
            # Create or update pending authentication
            result = await session.execute(
                select(PendingAuth).where(PendingAuth.user_id == interaction.user.id)
            )
            pending = result.scalar_one_or_none()
            
            # Generate JWT token
            token = create_jwt(self.email.value)
            
            if pending:
                # Update existing
                pending.email = self.email.value
                pending.token = token
                pending.user_type = 'professional'
                pending.pro_id = pro.id
                pending.first_name = pro.first_name
                pending.last_name = pro.last_name
                pending.created_at = datetime.now()
                pending.expires_at = datetime.now() + COOLDOWN_PERIOD
            else:
                # Create new
                pending = PendingAuth(
                    user_id=interaction.user.id,
                    email=self.email.value,
                    token=token,
                    user_type='professional',
                    pro_id=pro.id,
                    first_name=pro.first_name,
                    last_name=pro.last_name,
                    created_at=datetime.now(),
                    expires_at=datetime.now() + COOLDOWN_PERIOD
                )
                session.add(pending)
            
            await session.commit()
            
            # Send email with token
            send_email(
                ConfigManager.get('email_object'),
                ConfigManager.get('email_body').format(token),
                self.email.value
            )
            
            await interaction.followup.send(
                f"✉️ Mail envoyé à {self.email.value}\n\nEntrez le jeton reçu en cliquant sur le bouton ci-dessous.",
                view=FeedbackView(),
                ephemeral=True
            )


class FeedbackView(ui.View):
    """View with button to enter token."""
    
    def __init__(self):
        super().__init__(timeout=None)
    
    @ui.button(label='Entrer le jeton', style=ButtonStyle.primary)
    async def enter_token(self, interaction: Interaction, _: ui.Button):
        await interaction.response.send_modal(TokenModal())


class TokenModal(ui.Modal, title="Validation"):
    """Modal for token entry."""
    
    token = ui.TextInput(
        label="Jeton",
        placeholder="Copiez le jeton reçu par email"
    )
    
    async def on_submit(self, interaction: Interaction):
        """Verify token and complete authentication."""
        async with AsyncSessionLocal() as session:
            # Get pending authentication
            result = await session.execute(
                select(PendingAuth).where(
                    PendingAuth.user_id == interaction.user.id,
                    PendingAuth.expires_at > datetime.now()
                )
            )
            pending = result.scalar_one_or_none()
            
            if not pending:
                await interaction.response.send_message(
                    "❌ Aucune demande d'authentification en cours ou jeton expiré.",
                    ephemeral=True
                )
                return
            
            # Verify JWT token
            if not verify_jwt(self.token.value, pending.email):
                await interaction.response.send_message(
                    "❌ Jeton invalide.",
                    ephemeral=True
                )
                return
            
            await interaction.response.defer(ephemeral=True)
            
            # Create authenticated user
            auth_user = AuthenticatedUser(
                user_id=interaction.user.id,
                email=pending.email,
                user_type=pending.user_type,
                authenticated_at=datetime.now()
            )
            
            if pending.user_type == 'student':
                auth_user.student_id = pending.student_id
                auth_user.grade_level = pending.grade_level
                auth_user.formation_type = pending.formation_type
                
                # Add appropriate roles
                try:
                    # Add grade level role (M1 or M2)
                    grade_role = ROLE_M1 if pending.grade_level == 'M1' else ROLE_M2
                    await interaction.user.add_roles(grade_role)
                    
                    # Add formation role (FI or FA)
                    formation_role = ROLE_FI if pending.formation_type == 'FI' else ROLE_FA
                    await interaction.user.add_roles(formation_role)
                    
                    # Set nickname
                    nick = f"{pending.first_name} {pending.last_name}".title()
                    try:
                        await interaction.user.edit(nick=nick)
                    except Forbidden:
                        pass  # Can't edit owner's nickname
                    
                except Exception as e:
                    print(f"Error adding roles: {e}")
            
            elif pending.user_type == 'professional':
                # Get professional's course channels
                result = await session.execute(
                    select(Professional).where(Professional.id == pending.pro_id)
                )
                pro = result.scalar_one_or_none()
                
                if pro:
                    try:
                        # Set channel permissions for each course
                        for course_channel in pro.course_channels:
                            channel = interaction.guild.get_channel(course_channel.channel_id)
                            if channel:
                                await channel.set_permissions(
                                    interaction.user,
                                    view_channel=True
                                )
                        
                        # Set nickname
                        if pending.first_name and pending.last_name:
                            nick = f"{pending.first_name} {pending.last_name}".title()
                            try:
                                await interaction.user.edit(nick=nick)
                            except Forbidden:
                                pass
                    
                    except Exception as e:
                        print(f"Error setting permissions: {e}")
            
            # Save authenticated user
            session.add(auth_user)
            
            # Delete pending authentication
            await session.delete(pending)
            
            await session.commit()
            
            await interaction.followup.send(
                "✅ Authentification réussie !",
                ephemeral=True
            )


class RootMeModal(ui.Modal, title="Lier son compte Root-Me"):
    """Modal for linking Root-Me profile."""
    
    uuid = ui.TextInput(
        label="Identifiant Root-Me",
        placeholder="123456 (voir https://www.root-me.org/?page=preferences)",
        min_length=1,
        max_length=10
    )
    
    def __init__(self, user: Optional[AuthenticatedUser]):
        super().__init__()
        if user and user.rootme_id:
            self.uuid.default = str(user.rootme_id)
    
    async def on_submit(self, interaction: Interaction):
        """Link Root-Me profile."""
        # Validate RootMe ID format
        rootme_id = self.uuid.value.strip()
        if not rootme_id.isdigit():
            await interaction.response.send_message(
                "❌ L'identifiant Root-Me doit être un nombre.",
                ephemeral=True
            )
            return
        
        if len(rootme_id) < 1 or len(rootme_id) > 10:
            await interaction.response.send_message(
                "❌ L'identifiant Root-Me doit contenir entre 1 et 10 chiffres.",
                ephemeral=True
            )
            return
        
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(AuthenticatedUser).where(AuthenticatedUser.user_id == interaction.user.id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                await interaction.response.send_message(
                    "❌ Vous devez d'abord vous authentifier.",
                    ephemeral=True
                )
                return
            
            # Check if this RootMe ID is already linked to another user
            result = await session.execute(
                select(AuthenticatedUser).where(
                    AuthenticatedUser.rootme_id == rootme_id,
                    AuthenticatedUser.user_id != interaction.user.id
                )
            )
            existing_user = result.scalar_one_or_none()
            
            if existing_user:
                await interaction.response.send_message(
                    "❌ Cet identifiant Root-Me est déjà lié à un autre compte.",
                    ephemeral=True
                )
                return
            
            await interaction.response.defer(ephemeral=True)
            
            try:
                # Verify Root-Me ID exists
                RootMe.setup()
                await RootMe.get_author(rootme_id)
                
                # Save Root-Me ID
                user.rootme_id = rootme_id
                await session.commit()
                
                await interaction.followup.send(
                    "✅ Compte Root-Me lié avec succès !",
                    ephemeral=True
                )
            
            except Exception as e:
                await interaction.followup.send(
                    f"❌ Erreur lors de la vérification de l'ID Root-Me: {str(e)}",
                    ephemeral=True
                )


class LinkedinModal(ui.Modal, title="Lier son compte LinkedIn"):
    """Modal for linking LinkedIn profile."""
    
    linkedin_url = ui.TextInput(
        label="URL LinkedIn",
        placeholder="https://www.linkedin.com/in/votre-profil",
        min_length=20,
        max_length=100
    )
    
    def __init__(self, user: Optional[AuthenticatedUser]):
        super().__init__()
        if user and user.linkedin_url:
            self.linkedin_url.default = user.linkedin_url
    
    async def on_submit(self, interaction: Interaction):
        """Link LinkedIn profile."""
        # Validate URL format
        pattern = r'https?://([a-z]{2,3}\.)?linkedin\.com/in/[^/]+/?'
        if not re.match(pattern, self.linkedin_url.value):
            await interaction.response.send_message(
                "❌ URL LinkedIn invalide. Format attendu: https://www.linkedin.com/in/votre-profil",
                ephemeral=True
            )
            return
        
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(AuthenticatedUser).where(AuthenticatedUser.user_id == interaction.user.id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                await interaction.response.send_message(
                    "❌ Vous devez d'abord vous authentifier.",
                    ephemeral=True
                )
                return
            
            # Update or set LinkedIn URL
            old_url = user.linkedin_url
            user.linkedin_url = self.linkedin_url.value
            await session.commit()
            
            if old_url:
                await interaction.response.send_message(
                    f"✅ Profil LinkedIn mis à jour !\nAncien: {old_url}\nNouveau: {self.linkedin_url.value}",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    "✅ Compte LinkedIn lié avec succès !",
                    ephemeral=True
                )

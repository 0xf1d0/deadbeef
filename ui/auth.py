from discord import ui, Interaction, ButtonStyle, Forbidden
from datetime import datetime, timedelta

from utils import ROLE_FA, ROLE_FI, ROLE_PRO, FI, HEADERS_FI, FA, HEADERS_FA, ROLE_M1, ROLE_STUDENT, ROLE_NOTABLE, send_email, create_jwt, verify_jwt, ConfigManager

COOLDOWN_PERIOD = timedelta(weeks=1)  # Cooldown de 1 semaine


class Authentication(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @ui.button(label='Identifiez-vous', style=ButtonStyle.primary)
    async def authenticate(self, interaction: Interaction, _: ui.Button):
        roles = [ROLE_PRO.id, ROLE_STUDENT.id]
        user_roles = [role.id for role in interaction.user.roles]
        
        if not any(role in user_roles for role in roles):
            await interaction.response.send_message("Vous n'avez pas le profil requis.", ephemeral=True)
            return
            
        modal = ProModal() if ROLE_PRO.id in user_roles else StudentModal()
        await interaction.response.send_modal(modal)


class ProModal(ui.Modal, title="Authentification"):
    email = ui.TextInput(label="Email", placeholder="académique / professionnel")
    firstname = ui.TextInput(label="Prénom", placeholder="Facultatif", required=False)
    lastname = ui.TextInput(label="Nom", placeholder="Facultatif", required=False)
    
    async def on_submit(self, interaction: Interaction):
        users = ConfigManager.get('users', [])
        current_user = next((u for u in users if u['id'] == interaction.user.id), None)
        if current_user:
            await interaction.response.send_message("Vous êtes déjà authentifié.", ephemeral=True)
            return
        
        existing_email_user = next((u for u in users if u['email'] == self.email.value and u['id'] is not None), None)
        if existing_email_user:
            await interaction.response.send_message("Cet email a déjà été enregistré.", ephemeral=True)
            return
        
        email_user = next((u for u in users if u['email'] == self.email.value), None)
        if not email_user:
            await interaction.response.send_message("Email non valide.", ephemeral=True)
            return
        
        if 'last_auth_request' in email_user:
            last_request = datetime.fromisoformat(email_user['last_auth_request'])
            if datetime.now() - last_request < COOLDOWN_PERIOD:
                await interaction.response.send_message("Veuillez attendre avant de demander un nouveau jeton.", ephemeral=True)
                return

        await interaction.response.defer()

        email_user['last_auth_request'] = datetime.now().isoformat()
        ConfigManager.set('users', users)
        
        send_email(
            ConfigManager.get('email_object'),
            ConfigManager.get('email_body').format(create_jwt(self.email.value)),
            self.email.value
        )

        await interaction.followup.send(
            f"Mail envoyé à {self.email.value}",
            view=Feedback(self.email.value, f'{self.firstname.value} {self.lastname.value}'.title()),
            ephemeral=True
        )


class Feedback(ui.View):
    def __init__(self, email, nick=None, role=None, student_id=None):
        super().__init__(timeout=None)
        self.email = email
        self.role = role
        self.student_id = student_id
        self.nick = nick
    
    @ui.button(label='Entrer le jeton', style=ButtonStyle.primary)
    async def feedback(self, interaction: Interaction, _: ui.Button):
        await interaction.response.send_modal(Token(self, self.email, self.nick, self.role, self.student_id))


class Token(ui.Modal):
    token = ui.TextInput(label="Jeton", placeholder="Jeton de validation")

    def __init__(self, view, email, nick=None, role=None, student_id=None):
        super().__init__(title="Authentification")
        self.view = view
        self.email = email
        self.role = role
        self.student_id = student_id
        self.nick = nick

    async def on_submit(self, interaction: Interaction):
        users = ConfigManager.get('users', [])
        user = next((u for u in users if u['id'] == interaction.user.id), None)
        if not user or not verify_jwt(self.token.value, self.email):
            await interaction.response.send_message("Token non valide.", ephemeral=True)
            return
        
        # Mise à jour des rôles et permissions
        if self.role in [ROLE_FI, ROLE_FA]:
            await interaction.user.add_roles(self.role, ROLE_M1)
            try:
                await interaction.user.edit(nick=self.nick)
            except Forbidden:
                pass
        else:
            await interaction.user.add_roles(ROLE_NOTABLE)
            try:
                await interaction.user.edit(nick=self.nick)
            except Forbidden:
                pass
            
            # Mise à jour des permissions des cours
            if 'courses' in user:
                guild = interaction.guild
                for channel_id in user['courses']:
                    channel = guild.get_channel(channel_id)
                    if channel:
                        await channel.set_permissions(interaction.user, view_channel=True)
                        
        await interaction.response.send_message("Authentification réussie.", ephemeral=True)
        self.view.stop()


class StudentModal(ui.Modal, title="Authentification"):
    email = ui.TextInput(label="Email", placeholder="prenom.nom@etu.u-paris.fr")
    student_id = ui.TextInput(label="Numéro étudiant", placeholder="12345678")

    async def on_submit(self, interaction: Interaction):
        users = ConfigManager.get('users', [])
        current_user = next((u for u in users if u['id'] == interaction.user.id), None)
        
        if current_user and current_user.get('studentId') == self.student_id.value:
            await interaction.response.send_message("Vous êtes déjà authentifié.", ephemeral=True)
            return
            
        if not self.email.value.endswith('@etu.u-paris.fr'):
            await interaction.response.send_message("Email non valide.", ephemeral=True)
            return
        
        # Vérification des listes FI/FA
        valid_user = None
        for data in [FI, FA]:
            headers = HEADERS_FI if data == FI else HEADERS_FA
            role = ROLE_FI if data == FI else ROLE_FA
            
            for row in data:
                if (f"{row[headers.index('Email')]}@etu.u-paris.fr" == self.email.value and
                    row[headers.index('N° étudiant')] == self.student_id.value):
                    
                    valid_user = {
                        'role': role,
                        'prenom': row[headers.index('Prénom')],
                        'nom': row[headers.index('Nom')]
                    }
                    break
            if valid_user:
                break

        if not valid_user:
            await interaction.response.send_message("Email ou numéro étudiant invalide.", ephemeral=True)
            return
        
        # Vérification du cooldown
        if current_user and 'last_auth_request' in current_user:
            last_request = datetime.fromisoformat(current_user['last_auth_request'])
            if datetime.now() - last_request < COOLDOWN_PERIOD:
                await interaction.response.send_message("Veuillez attendre avant de demander un nouveau jeton.", ephemeral=True)
                return
        
        await interaction.response.defer()
        
        # Mise à jour ou création de l'utilisateur
        if not current_user:
            current_user = {'id': interaction.user.id}
            users.append(current_user)
            
        current_user.update({
            'email': self.email.value,
            'studentId': self.student_id.value,
            'last_auth_request': datetime.now().isoformat()
        })
        ConfigManager.set('users', users)
        
        send_email(
            ConfigManager.get('email_object'),
            ConfigManager.get('email_body').format(create_jwt(self.email.value)),
            self.email.value
        )

        await interaction.followup.send(
            f"Mail envoyé à {self.email.value}",
            view=Feedback(self.email.value, f"{valid_user['prenom']} {valid_user['nom']}".title(), 
                          valid_user['role'], self.student_id.value),
            ephemeral=True
        )

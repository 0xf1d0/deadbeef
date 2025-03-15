from discord import ui, Interaction, ButtonStyle, Forbidden, Object, Role
from datetime import datetime, timedelta

from utils import ROLE_FA, ROLE_FI, ROLE_PRO, FI, HEADERS_FI, FA, HEADERS_FA, ROLE_M1, ROLE_STUDENT, ROLE_NOTABLE, send_email, create_jwt, verify_jwt, ConfigManager
from api.api import RootMe

COOLDOWN_PERIOD = timedelta(hours=1)


class Authentication(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @ui.button(label="S'authentifier", style=ButtonStyle.primary, emoji="🔒")
    async def authenticate(self, interaction: Interaction, _: ui.Button):
        user_roles = [role.id for role in interaction.user.roles]
        
        if ROLE_PRO.id in user_roles:
            if user := next((u for u in ConfigManager.get('users', []) if u['id'] == interaction.user.id), None):
                if 'last_auth_request' in user:
                    last_request = datetime.fromisoformat(user['last_auth_request'])
                    if datetime.now() - last_request < COOLDOWN_PERIOD:
                        await interaction.response.send_modal(Token())
                        return
                else:
                    await interaction.response.send_message("Vous êtes déjà authentifié.", ephemeral=True)
                    return
            
            await interaction.response.send_modal(ProModal())
        elif ROLE_STUDENT.id in user_roles:
            if user := next((u for u in ConfigManager.get('users', []) if u['id'] == interaction.user.id), None):
                if 'last_auth_request' in user:
                    last_request = datetime.fromisoformat(user['last_auth_request'])
                    if datetime.now() - last_request < COOLDOWN_PERIOD:
                        await interaction.response.send_modal(Token())
                        return
                else:
                    await interaction.response.send_message("Vous êtes déjà authentifié.", ephemeral=True)
                    return

            await interaction.response.send_modal(StudentModal())
        else:
            await interaction.response.send_message("Vous n'avez pas le profil requis.", ephemeral=True)
    
    @ui.button(label='Root-Me', style=ButtonStyle.primary, emoji="💀")
    async def rootme(self, interaction: Interaction, _: ui.Button):
        await interaction.response.send_modal(RootMeModal())


class ProModal(ui.Modal, title="Authentification"):
    email = ui.TextInput(label="Email", placeholder="académique / professionnel")
    firstname = ui.TextInput(label="Prénom", placeholder="Facultatif", required=False)
    lastname = ui.TextInput(label="Nom", placeholder="Facultatif", required=False)
    
    async def on_submit(self, interaction: Interaction):
        users = ConfigManager.get('users', [])
        
        existing_email_user = next((u for u in users if u['email'] == self.email.value and u['id'] is not None), None)
        if existing_email_user:
            await interaction.response.send_message("Cet email a déjà été enregistré.", ephemeral=True)
            return
        
        email_user = next((u for u in users if u['email'] == self.email.value), None)
        if not email_user:
            await interaction.response.send_message("Email non valide.", ephemeral=True)
            return

        await interaction.response.defer()

        email_user['last_auth_request'] = datetime.now().isoformat()
        email_user['id'] = interaction.user.id
        email_user['role'] = ROLE_NOTABLE.id
        email_user['nick'] = f'{self.firstname.value} {self.lastname.value}'.title() if self.firstname.value or self.lastname.value else None
        ConfigManager.set('users', users)
        
        send_email(
            ConfigManager.get('email_object'),
            ConfigManager.get('email_body').format(create_jwt(self.email.value)),
            self.email.value
        )

        await interaction.followup.send(
            f"Mail envoyé à {self.email.value}",
            view=Feedback(),
            ephemeral=True
        )


class Feedback(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @ui.button(label='Entrer le jeton', style=ButtonStyle.primary)
    async def feedback(self, interaction: Interaction, _: ui.Button):
        await interaction.response.send_modal(Token(self))


class Token(ui.Modal):
    token = ui.TextInput(label="Jeton", placeholder="Jeton de validation")

    def __init__(self, view=None):
        super().__init__(title="Authentification")
        self.view = view

    async def on_submit(self, interaction: Interaction):
        users = ConfigManager.get('users', [])
        user = next((u for u in users if u['id'] == interaction.user.id), None)
        if not user or not verify_jwt(self.token.value, user['email']):
            await interaction.response.send_message("Token non valide.", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        
        role = Object(user['role'], type=Role)
        
        await interaction.user.add_roles(role)
        
        if role in [ROLE_FA, ROLE_FI]:
            await interaction.user.add_roles(ROLE_M1)

        if user['nick']:
            try:
                await interaction.user.edit(nick=user['nick'])
            except Forbidden:
                pass

        if role == ROLE_NOTABLE:
            # Mise à jour des permissions des cours
            if 'courses' in user:
                guild = interaction.guild
                for channel_id in user['courses']:
                    channel = guild.get_channel(channel_id)
                    if channel:
                        await channel.set_permissions(interaction.user, view_channel=True)
                        
        await interaction.followup.send("Authentification réussie.", ephemeral=True)
        if 'nick' in user: del user['nick']
        if 'role' in user: del user['role']
        del user['last_auth_request']
        ConfigManager.set('users', users)
        if self.view:
            self.view.stop()


class StudentModal(ui.Modal, title="Authentification"):
    student_id = ui.TextInput(label="Numéro étudiant", placeholder="12345678")

    async def on_submit(self, interaction: Interaction):
        users = ConfigManager.get('users', [])
        current_user = next((u for u in users if u['id'] == interaction.user.id), None)
        
        # Vérification des listes FI/FA
        valid_user = None
        for data in [FI, FA]:
            headers = HEADERS_FI if data == FI else HEADERS_FA
            role = ROLE_FI if data == FI else ROLE_FA
            
            for row in data:
                if row[headers.index('N° étudiant')] == self.student_id.value:
                    valid_user = {
                        'last_auth_request': datetime.now().isoformat(),
                        'studentId': self.student_id.value,
                        'email': f"{row[headers.index('Email')]}@etu.u-paris.fr",
                        'role': role.id,
                        'nick': f"{row[headers.index('Prénom')]} {row[headers.index('Nom')]}".title(),
                    }
                    break
            if valid_user:
                break

        if not valid_user:
            await interaction.response.send_message("Numéro étudiant invalide.", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        # Mise à jour ou création de l'utilisateur
        if not current_user:
            current_user = {'id': interaction.user.id}
            users.append(current_user)
            
        current_user.update(valid_user)
        ConfigManager.set('users', users)
        
        send_email(
            ConfigManager.get('email_object'),
            ConfigManager.get('email_body').format(create_jwt(valid_user['email'])),
            valid_user['email']
        )

        await interaction.followup.send(
            f"Mail envoyé à {valid_user['email']}",
            view=Feedback(),
            ephemeral=True
        )
        

class RootMeModal(ui.Modal, title="Lier son compte Root-Me"):
    id = ui.TextInput(label="Identifiant", placeholder="123456")
    
    async def on_submit(self, interaction: Interaction):
        users = ConfigManager.get('users', [])
        user = next((u for u in users if u['id'] == interaction.user.id), None)
        if not user:
            await interaction.response.send_message("Vous n'êtes pas authentifié.", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        try:
            rootme = RootMe()
            rootme.get_authors(self.id.value)
            await rootme.session.close()
            
            user['rootme'] = self.id.value
            ConfigManager.set('users', users)
            
            await interaction.followup.send("Compte Root-Me lié.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(str(e), ephemeral=True)

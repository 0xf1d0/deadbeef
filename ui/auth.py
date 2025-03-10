from discord import ui, Interaction, ButtonStyle, Forbidden
from datetime import datetime, timedelta

from utils import ROLE_FA, ROLE_FI, ROLE_PRO, FI, HEADERS_FI, FA, HEADERS_FA, ROLE_M1, ROLE_STUDENT, send_email, create_jwt, verify_jwt, ConfigManager

COOLDOWN_PERIOD = timedelta(weeks=1)  # Cooldown de 1 semaine

class Authentication(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @ui.button(label='Identifiez-vous', style=ButtonStyle.primary)
    async def authenticate(self, interaction: Interaction, _: ui.Button):
        if interaction.user.get_role(ROLE_PRO.id):
            await interaction.response.send_modal(ProModal())
        elif interaction.user.get_role(ROLE_STUDENT.id):
            await interaction.response.send_modal(StudentModal())
        else:
            await interaction.response.send_message("Vous n'avez pas le profil requis.", ephemeral=True)


class ProModal(ui.Modal, title="Authentification"):
    email = ui.TextInput(label="Email", placeholder="académique / professionnel")
    firstname = ui.TextInput(label="Prénom", placeholder="Facultatif", required=False)
    lastname = ui.TextInput(label="Nom", placeholder="Facultatif", required=False)

    async def on_submit(self, interaction: Interaction):
        users = ConfigManager.get('users', [])
        for user in users:
            if user['id'] == interaction.user.id:
                await interaction.response.send_message("Vous êtes déjà authentifié.", ephemeral=True)
                break
        else:
            for user in users:
                if user['email'] == self.email.value:
                    last_request = user.get('last_auth_request')
                    if last_request:
                        last_request_time = datetime.fromisoformat(last_request)
                        if datetime.now() - last_request_time < COOLDOWN_PERIOD:
                            await interaction.response.send_message("Veuillez attendre avant de demander un nouveau jeton.", ephemeral=True)
                            return
                    send_email(ConfigManager.get('email_object'), ConfigManager.get('email_body').format(create_jwt(self.email.value)), self.email.value)
                    user['last_auth_request'] = datetime.now().isoformat()
                    ConfigManager.set('users', users)
                    await interaction.response.send_message(f"Vous allez recevoir un mail à l'adresse {self.email.value} contenant le jeton de validation.", view=Feedback(self.email.value, f'{self.firstname.value} {self.lastname.value}'.title()), ephemeral=True)
                    break
            else:
                await interaction.response.send_message("Email non valide.", ephemeral=True)


class Feedback(ui.View):
    def __init__(self, email, nick=None, role=None, student_id=None):
        super().__init__(timeout=None)
        self.email = email
        self.role = role
        self.student_id = student_id
        self.nick = nick
    
    @ui.button(label='Entrer le jeton', style=ButtonStyle.primary)
    async def feedback(self, interaction: Interaction, _: ui.Button):
        await interaction.response.send_modal(Token(self.email, self.nick, self.role, self.student_id))


class Token(ui.Modal):
    token = ui.TextInput(label="Jeton", placeholder="Jeton de validation")

    def __init__(self, email, nick=None, role=None, student_id=None):
        super().__init__(title="Authentification")
        self.email = email
        self.role = role
        self.student_id = student_id
        self.nick = nick

    async def on_submit(self, interaction: Interaction):
        if self.role in [ROLE_FI, ROLE_FA]:
            if verify_jwt(self.token.value, self.email) is not None:
                await interaction.user.add_roles(self.role, ROLE_M1)
                try:
                    await interaction.user.edit(nick=self.nick)
                except Forbidden:
                    pass
                users = ConfigManager.get('users', [])
                users.append({'id': interaction.user.id, 'email': self.email, 'studentId': self.student_id})
                ConfigManager.set('users', users)
            else:
                await interaction.response.send_message("Token non valide.", ephemeral=True)
                return
        else:
            users = ConfigManager.get('users', [])
            for user in users:
                if user['email'] == self.email:
                    if verify_jwt(self.token.value, self.email) is not None:
                        for channel_id in user['courses']:
                            interaction.guild.get_channel(channel_id).set_permissions(interaction.user, view_channel=True)
                        user['id'] = interaction.user.id
                        await interaction.user.edit(nick=self.nick)
                        ConfigManager.set('users', users)
                        break
            else:
                await interaction.response.send_message("Token non valide.", ephemeral=True)
                return
        await interaction.response.send_message("Authentification réussie.", ephemeral=True)
        self.view.stop()


class StudentModal(ui.Modal, title="Authentification"):
    email = ui.TextInput(label="Email", placeholder="prenom.nom@etu.u-paris.fr")
    student_id = ui.TextInput(label="Numéro étudiant", placeholder="12345678")

    async def on_submit(self, interaction: Interaction):
        users = ConfigManager.get('users', [])
        for user in users:
            if user['id'] == interaction.user.id or user.get('studentId') == self.student_id.value:
                await interaction.response.send_message("Vous êtes déjà authentifié.", ephemeral=True)
                break
        else:
            if self.email.value.endswith('@etu.u-paris.fr'):
                for row in FI:
                    if f"{row[HEADERS_FI.index('Email')]}@etu.u-paris.fr" == self.email.value and row[HEADERS_FI.index('N° étudiant')] == self.student_id.value:
                        last_request = user.get('last_auth_request')
                        if last_request:
                            last_request_time = datetime.fromisoformat(last_request)
                            if datetime.now() - last_request_time < COOLDOWN_PERIOD:
                                await interaction.response.send_message("Veuillez attendre avant de demander un nouveau jeton.", ephemeral=True)
                                return
                        send_email(ConfigManager.get('email_object'), ConfigManager.get('email_body').format(create_jwt(self.email.value)), self.email.value)
                        user['last_auth_request'] = datetime.now().isoformat()
                        ConfigManager.set('users', users)
                        await interaction.response.send_message(f"Vous allez recevoir un mail à l'adresse {self.email.value} contenant le jeton de validation.", view=Feedback(self.email.value, f"{row[HEADERS_FI.index('Prénom')]} {row[HEADERS_FI.index('Nom')]}".title(), ROLE_FI, self.student_id.value), ephemeral=True)
                        break
                else:
                    for row in FA:
                        if f"{row[HEADERS_FA.index('Email')]}@etu.u-paris.fr" == self.email.value and row[HEADERS_FA.index('N° étudiant')] == self.student_id.value:
                            last_request = user.get('last_auth_request')
                            if last_request:
                                last_request_time = datetime.fromisoformat(last_request)
                                if datetime.now() - last_request_time < COOLDOWN_PERIOD:
                                    await interaction.response.send_message("Veuillez attendre avant de demander un nouveau jeton.", ephemeral=True)
                                    return
                            send_email(ConfigManager.get('email_object'), ConfigManager.get('email_body').format(create_jwt(self.email.value)), self.email.value)
                            user['last_auth_request'] = datetime.now().isoformat()
                            ConfigManager.set('users', users)
                            await interaction.response.send_message(f"Vous allez recevoir un mail à l'adresse {self.email.value} contenant le jeton de validation.", view=Feedback(self.email.value, f"{row[HEADERS_FA.index('Prénom')]} {row[HEADERS_FA.index('Nom')]}".title(), ROLE_FA, self.student_id.value), ephemeral=True)
                            break
                    else:
                        await interaction.response.send_message("Email non valide.", ephemeral=True)
            else:
                await interaction.response.send_message("Email non valide.", ephemeral=True)

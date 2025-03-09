from discord import ui, Interaction, ButtonStyle

from utils import ROLE_FA, ROLE_FI, ROLE_PRO, FI, HEADERS_FI, FA, HEADERS_FA, ROLE_M1, send_email, create_jwt,verify_jwt, ConfigManager


class Authentication(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @ui.button(label='Identifiez-vous', style=ButtonStyle.primary)
    async def authenticate(self, interaction: Interaction, _: ui.Button):
        if interaction.user.get_role(ROLE_PRO.id):
            await interaction.response.send_modal(ProModal())
        else:
            await interaction.response.send_modal(StudentModal())


class ProModal(ui.Modal, title="Authentification"):
    email = ui.TextInput(label="Email", placeholder="académique / professionnel")
    lastname = ui.TextInput(label="Nom", placeholder="Facultatif", required=False)
    firstname = ui.TextInput(label="Prénom", placeholder="Facultatif", required=False)
    
    async def on_submit(self, interaction: Interaction):
        users = ConfigManager.get('users', [])
        for user in users:
            if user['id'] == interaction.user.id:
                await interaction.response.send_message("Vous êtes déjà authentifié.", ephemeral=True)
                break
        else:
            if self.email not in [user['email'] for user in users]:
                await interaction.response.send_message("Email non valide.", ephemeral=True)
            else:
                await interaction.response.send_modal(Token(self.email))


class Token(ui.Modal):
    token = ui.TextInput(label="Token")
    
    def __init__(self, email, role = None, student_id = None):
        super().__init__(title="Authentification")
        self.email = email
        self.role = role
        self.student_id = student_id
        
    async def on_submit(self, interaction: Interaction):
        if verify_jwt(self.token.value) is not None:
            users = ConfigManager.get('users', [])
            
            if self.role in [ROLE_FI, ROLE_FA]:
                await interaction.user.add_roles([self.role, ROLE_M1])
                users.append({'id': interaction.user.id, 'email': self.email, 'studentId': self.student_id})
                ConfigManager.set('users', users)
            else:
                for user in users:
                    if user['email'] == self.email:
                        for channel_id in user['courses']:
                            interaction.guild.get_channel(channel_id).set_permissions(interaction.user, view_channel=True)
                        user['id'] = interaction.user.id
                        ConfigManager.set('users', users)
                        break
            await interaction.response.send_message("Authentification réussie.", ephemeral=True)


class StudentModal(ui.Modal, title="Authentification"):
    email = ui.TextInput(label="Email", placeholder="UPC Cybersécurité")
    student_id = ui.TextInput(label="Numéro étudiant", placeholder="12345678")
    lastname = ui.TextInput(label="Nom", placeholder="Facultatif", required=False)
    firstname = ui.TextInput(label="Prénom", placeholder="Facultatif", required=False)
    
    async def on_submit(self, interaction: Interaction):
        for user in ConfigManager.get('users', []):
            if user['id'] == interaction.user.id or user.get('studentId') == self.student_id.value:
                await interaction.response.send_message("Vous êtes déjà authentifié.", ephemeral=True)
                break
        else:
            explode = self.email.split('.')
            if len(explode) > 1:
                if self.email.value.endswith('@etu.u-paris.fr'):
                    name = explode[1].lower().replace('-', ' ')
                    if name in [row[HEADERS_FI.index('Nom')].lower() for row in FI]:
                        send_email("UPC Cybersécurité Discord Verification", f"Token de validation: {create_jwt(self.email)}", self.email)
                        await interaction.response.send_modal(Token(self.email, ROLE_FI))
                    elif name in [row[HEADERS_FA.index('Nom')].lower() for row in FA]:
                        send_email("UPC Cybersécurité Discord Verification", f"Token de validation: {create_jwt(self.email)}", self.email)
                        await interaction.response.send_modal(Token(self.email, ROLE_FA))
                    else:
                        await interaction.response.send_message("Email non valide.", ephemeral=True)
                else:
                    await interaction.response.send_message("Email non valide.", ephemeral=True)
            else:
                await interaction.response.send_message("Email non valide.", ephemeral=True)


"""class AuthenticationButton(ui.Button):
    def __init__(self, label, style):
        super().__init__(label=label, style=style, disabled=True)

    async def callback(self, interaction: Interaction):
        pass
        # await interaction.response.send_message(f"Identifiez-vous via le menu déroulant ci-dessous.", view=DropDownView(), ephemeral=True)
"""

"""class DropDown(ui.Select):
    def __init__(self, options):
        super().__init__(placeholder='Choisir son identité', custom_id='dropdown', options=options, min_values=1, max_values=1)
    
    async def callback(self, interaction: Interaction):
        selected_value = self.values[0]
        if selected_value in [option.value for option in self.options]:
            view = ConfirmView(selected_value, self.view, interaction)
            await interaction.response.send_message(f"Confirmez-vous la sélection de {selected_value} ?", view=view, ephemeral=True)


class ConfirmView(ui.View):
    def __init__(self, selected_value, dropdown_view, based_interaction):
        super().__init__(timeout=None)
        self.selected_value = selected_value
        self.dropdown_view = dropdown_view
        self.add_item(ConfirmButton(label="Confirmer", style=ButtonStyle.success, based_interaction=based_interaction))
        self.add_item(CancelButton(label="Annuler", style=ButtonStyle.danger))


class ConfirmButton(ui.Button):
    def __init__(self, label, style, based_interaction):
        super().__init__(label=label, style=style)
        self.based_interaction = based_interaction

    async def callback(self, interaction: Interaction):
        selected_value = self.view.selected_value
        dropdown_view = self.view.dropdown_view
        if selected_value == 'Invité':
            await interaction.user.add_roles(ROLE_GUEST)
        else:
            dropdown_view.options = [option for option in dropdown_view.options if option.value != selected_value]
            dropdown_view.update_options()
            await interaction.user.edit(nick=selected_value)
            #  await self.based_interaction.message.edit(view=dropdown_view)
            await interaction.user.add_roles(ROLE_FI if self.view.selected_value in AuthenticationView.missing_members['FI'] else ROLE_FA)
        
        await interaction.response.edit_message(content=f'Sélection confirmée : {selected_value}', view=None)


class CancelButton(ui.Button):
    def __init__(self, label, style):
        super().__init__(label=label, style=style)

    async def callback(self, interaction: Interaction):
        await interaction.response.edit_message(content='Sélection annulée.', view=None)


class Dropdown(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.options = [SelectOption(label='Invité', value='Invité', emoji='👋')] + [SelectOption(label=f'FI - {name}', value=name, emoji='🎓') for name in AuthenticationView.missing_members['FI']] + [SelectOption(label=f'FA - {name}', value=name, emoji='🎓') for name in AuthenticationView.missing_members['FA']]
        self.current_page = 1
        self.per_page = 25
        self.update_options()
        
    @ui.select(placeholder='Choisir son identité')
    async def select_identity(self, interaction: Interaction, select: ui.Select):
        selected_value = select.values[0]
        if selected_value in [option.value for option in self.options]:
            view = ConfirmView(selected_value, self.view, interaction)
            await interaction.response.send_message(f"Confirmez-vous la sélection de {selected_value} ?", view=view, ephemeral=True)
        
    
    def update_options(self):
        total_options = len(self.options)
        total_pages = (total_options + self.per_page - 1) // self.per_page
        self.current_page = min(self.current_page, total_pages)
        start = (self.current_page - 1) * self.per_page
        end = start + self.per_page
        page_options = self.options[start:end]
        self.clear_items()
        self.add_item(DropDown(page_options))
        self.add_item(PreviousButton(disabled=self.current_page == 1))
        self.add_item(NextButton(disabled=self.current_page >= total_pages))


class PreviousButton(ui.Button):
    def __init__(self, disabled=False):
        super().__init__(label='<', style=ButtonStyle.primary, custom_id='previous_page', disabled=disabled)

    async def callback(self, interaction: Interaction):
        if self.view.current_page > 1:
            self.view.current_page -= 1
            self.view.update_options()
            await interaction.response.edit_message(view=self.view)


class NextButton(ui.Button):
    def __init__(self, disabled=False):
        super().__init__(label='>', style=ButtonStyle.primary, custom_id='next_page', disabled=disabled)

    async def callback(self, interaction: Interaction):
        total_options = len(self.view.options)
        total_pages = (total_options + self.view.per_page - 1) // self.view.per_page
        if self.view.current_page < total_pages:
            self.view.current_page += 1
            self.view.update_options()
            await interaction.response.edit_message(view=self.view)"""

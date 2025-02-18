from discord import ui, Interaction, ButtonStyle, SelectOption

from utils import ROLE_FA, ROLE_FI, ROLE_GUEST


class Authentication(ui.View):
    missing_members = None

    def __init__(self, members):
        super().__init__(timeout=None)
        Authentication.missing_members = members
        self.add_item(AuthenticationButton(label="Maintenance en cours...", style=ButtonStyle.gray))


class AuthenticationButton(ui.Button):
    def __init__(self, label, style):
        super().__init__(label=label, style=style, disabled=True)

    async def callback(self, interaction: Interaction):
        pass
        # await interaction.response.send_message(f"Identifiez-vous via le menu déroulant ci-dessous.", view=DropDownView(), ephemeral=True)


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

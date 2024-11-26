import re
from discord import app_commands, Interaction, ui, SelectOption, ButtonStyle, Member, Embed, File
from discord.ext import commands

from utils import CYBER, ROLE_FA, ROLE_FI, ROLE_GUEST, read_csv


class Common(commands.Cog):
    """
    @brief A class that contains common commands and listeners for the bot.
    This class defines several commands and event listeners that provide various functionalities such as managing LinkedIn profiles, assigning roles, sending invites, and more.
    """

    FI = read_csv('assets/cyber_sante.csv')
    FA = read_csv('assets/cyber.csv')
    
    def __init__(self, bot: commands.Bot):
        """
        @brief Initializes the common cog with the given bot instance.
        @param bot The bot instance to associate with this cog.
        """

        self.bot = bot
        self.guild = bot.guilds[0]
    
    def missing_member_names(self):
        names = {'FI': [], 'FA': []}
        roles = {'FI': ROLE_FI, 'FA': ROLE_FA}
        data = {'FI': Common.FI, 'FA': Common.FA}

        for key in data:
            for row in data[key]:
                name = f'{row[2]} {row[1]}'.title()
                member = self.guild.get_member_named(name)
                if not member or not member.get_role(roles[key]):
                    names[key].append(name)

        return names

    @app_commands.command(description="Affiche ou inscrit un profil LinkedIn.")
    @app_commands.describe(member='Le profil du membre à afficher', register='Inscrire un profil LinkedIn.')
    async def linkedin(self, ctx: Interaction, member: Member = None, register: str = ''):
        """
        @brief Handles LinkedIn profile registration and retrieval for users.
        @param ctx The interaction context.
        @param member The member whose LinkedIn profile is being registered or retrieved. Defaults to None.
        @param register The LinkedIn profile URL to register. Defaults to an empty string.
        This function allows users to register their LinkedIn profile URLs or retrieve the LinkedIn profiles of themselves or other members.
        If a LinkedIn profile URL is provided, it validates the URL and registers it for the user or the specified member.
        If no URL is provided, it retrieves the LinkedIn profile of the user or the specified member.
        The function performs the following actions:
        - If a LinkedIn profile URL is provided:
            - Validates the URL format.
            - Registers the URL for the user or the specified member.
            - Sends a confirmation message.
        - If no URL is provided:
            - Retrieves the LinkedIn profile of the user or the specified member.
            - Sends the LinkedIn profile or a message indicating that the profile was not found.
        @note Only users with the 'manage_roles' permission can register LinkedIn profiles for other members.
        @return None
        """
        
        if register:
            pattern = r'https?://([a-z]{2,3}\.)?linkedin\.com/in/[^/]+/?'
            if not re.match(pattern, register):
                await ctx.response.send_message('Le lien LinkedIn est invalide', ephemeral=True)
                return
            user = {'linkedin': register}
            if member and ctx.user.guild_permissions.manage_roles:
                user['id'] = member.id
            else:
                user['id'] = ctx.user.id
            self.bot.config.append("users", user)
            await ctx.response.send_message(f'Profil LinkedIn enregistré pour {member.display_name if member else ctx.user.display_name}.')
        elif member:
            user_profile = next((user for user in self.bot.config.get("users", []) if user["id"] == member.id), None)
            if user_profile:
                await ctx.response.send_message(f'Profil LinkedIn de {member.display_name}: {user_profile["linkedin"]}')
            else:
                await ctx.response.send_message(f'Profil LinkedIn pour {member.display_name} non trouvé.')
        else:
            user_profile = next((user for user in self.bot.config.get("users", []) if user["id"] == ctx.user.id), None)
            if user_profile:
                await ctx.response.send_message(f'Votre profil LinkedIn: {user_profile["linkedin"]}')
            else:
                await ctx.response.send_message('Votre profil LinkedIn non trouvé.')

    @app_commands.command(description="S'attribuer ou s'enlever le rôle de joueur.")
    async def gaming(self, ctx: Interaction):
        """
        @brief Toggles the 'gamer' role for the user who invoked the command.
        @param ctx The interaction context containing information about the command invocation.
        This function checks if the user already has the 'gamer' role. If the user has the role, it is removed and a confirmation message is sent. If the user does not have the role, it is added and a confirmation message is sent.
        """

        role = ctx.guild.get_role(1291867840067932304)
        if role in ctx.user.roles:
            await ctx.user.remove_roles(role)
            await ctx.response.send_message('Rôle de joueur retiré.', ephemeral=True)
        else:
            await ctx.user.add_roles(role)
            await ctx.response.send_message('Rôle de joueur attribué.', ephemeral=True)

    @app_commands.command(description="Affiche le lien d'invitation du serveur.")
    async def invite(self, ctx: Interaction):
        """
        @brief Sends an invitation embed with a QR code to join the Discord server.
        @param ctx The interaction context.
        This function creates an embed containing a QR code image and a description inviting users to join the Discord server for the Master Cybersécurité program at Université Paris Cité. The embed includes the server's icon and the number of non-bot members. The QR code image is attached to the message.
        """

        embed = Embed(title='Invitation', description='Scannez ce QR Code et rejoignez le serveur discord du Master Cybersécurité de Paris Cité.\n\nTous profils acceptés, curieux, intéressés ou experts en cybersécurité ! Bot multifonction intégré afin de dynamiser au maximum le serveur.', color=0x8B1538)
        file = File("assets/qrcode.png", filename="invite.png")
        embed.set_image(url='attachment://invite.png')
        embed.set_footer(text=f'Master Cybersécurité - Université Paris Cité - {len([member for member in ctx.guild.members if not member.bot])} membres', icon_url=ctx.guild.icon.url)
        await ctx.response.send_message(file=file, embed=embed)

    @app_commands.command(description="Affiche les informations sur le bot.")
    async def about(self, ctx: Interaction):
        """
        @brief Sends an embedded message with information about the bot.
        This asynchronous function sends an embedded message containing information about the bot,
        including its creator and purpose. The message includes a thumbnail image.
        @param ctx The interaction context in which the command was invoked.
        """

        embed = Embed(title='À propos de moi', description='Je suis un bot Discord créé par [Vincent Cohadon](https://fr.linkedin.com/in/vincent-cohadon) pour le Master Cybersécurité de Paris Cité.')
        file = File("assets/f1d0.png", filename="f1d0.png")
        embed.set_thumbnail(url='attachment://f1d0.png')
        await ctx.response.send_message(file=file, embed=embed)
    
    @app_commands.command(description="Liste les membres manquants.")
    async def missing_members_list(self, ctx: Interaction):
        """
        @brief Asynchronously generates a list of missing members and sends a message with the result.
        This function compares the members in the Discord guild with the names listed in two CSV files
        ('assets/cyber_sante.csv' and 'assets/cyber.csv'). It identifies members listed in the CSV files
        who are not present in the guild and sends a message with the list of missing members.
        @param ctx The interaction context from the Discord command.
        @return None
        """

        embed = Embed(title='Membres manquants')
        missing_members = self.missing_member_names()
        embed.add_field(name='FI', value=', '.join(missing_members['FI']) or 'Aucun')
        embed.add_field(name='FA', value=', '.join(missing_members['FA']) or 'Aucun')
        await ctx.response.send_message(embed=embed)

    @app_commands.command(description="Glossaire CYBER.")
    @app_commands.choices(option=[
        app_commands.Choice(name="view", value="1"),
        app_commands.Choice(name="add", value="2"),
        app_commands.Choice(name="remove", value="3")
    ])
    @app_commands.checks.has_any_role(1289241716985040960, 1289241666871627777)
    async def glossary(self, interaction: Interaction, option: app_commands.Choice[str], term: str = '', definition: str = ''):
        """
        @brief Handles glossary operations based on user interaction.
        @param interaction The interaction object representing the user's action.
        @param option The choice made by the user, determining the operation to perform.
        @param term The term to be added, retrieved, or deleted from the glossary.
        @param definition The definition of the term to be added to the glossary.
        @details
        This function performs different operations on a glossary based on the user's choice:
        - If option.value is '1', it retrieves and sends the definition of the specified term.
        - If option.value is '2', it adds the specified term and definition to the glossary.
        - If option.value is '3', it deletes the specified term from the glossary.
        - If the parameters are invalid, it sends an error message.
        @note The glossary is stored in the bot's configuration and is case-insensitive for term matching.
        @return None
        """

        glossary = self.bot.config.get('glossary', {})
        term_lower = term.lower()

        if option.value == '1':
            for key in glossary:
                if key.lower() == term_lower:
                    await interaction.response.send_message(glossary[key])
                    return
            await interaction.response.send_message('Terme non trouvé.', ephemeral=True)

        elif option.value == '2' and term and definition:
            glossary[term] = definition
            self.bot.config.set('glossary', glossary)
            await interaction.response.send_message(f'{term} ajouté au glossaire.')

        elif option.value == '3':
            for key in glossary:
                if key.lower() == term_lower:
                    del glossary[key]
                    self.bot.config.set('glossary', glossary)
                    await interaction.response.send_message(f'{term} retiré du glossaire.')
                    return
            await interaction.response.send_message('Terme non trouvé.', ephemeral=True)

        else:
            await interaction.response.send_message('Paramètres invalides.', ephemeral=True)

    @commands.Cog.listener()
    async def on_ready(self):
        """
        @brief This coroutine is called when the bot is ready.
        This method performs the following actions:
        - Retrieves the first guild the bot is connected to.
        - Gets the welcome channel by its ID.
        - Checks if a welcome message ID is stored in the bot's configuration.
        - If no welcome message ID is found, sends a welcome message to the welcome channel and stores its ID in the bot's configuration.
        - Adds a view to the bot with the specified message ID.
        @note This method assumes that the bot's configuration contains 'welcome_message' and 'welcome_message_id' keys.
        @param self The instance of the class.
        """

        welcome = self.guild.get_channel(1291494038427537559)
        message_id = self.bot.config.get('welcome_message_id')
        if not message_id:
            msg = await welcome.send(self.bot.config.get('welcome_message'), view=DropDownView(self.guild))
            self.bot.config.set('welcome_message_id', msg.id)
        self.bot.add_view(DropDownView(self.missing_member_names()), message_id=message_id)

    @commands.Cog.listener()
    async def on_member_remove(self, member: Member):
        """
        @brief Handles the event when a member leaves the guild.
        @param member The member who left the guild.
        This function sends an embed message to a specific channel with details about the member who left,
        including their name, display name, nickname, and roles. It also manages a welcome message in another
        channel, updating or setting it if necessary.
        """
        
        channel = member.guild.get_channel(1292059079287504930)
        embed = Embed(title=f'{member} ({member.id}) left')\
            .add_field(name='Name', value=member.name)\
            .add_field(name='Display Name', value=member.display_name)\
            .add_field(name='Nick', value=member.nick)\
            .add_field(name='Roles', value='\n'.join([f"{i+1}. {role.mention if role.name != '@everyone' else role.name} - {role.id}" for i, role in enumerate(member.roles)]))
        await channel.send(embed=embed)
        guild = member.guild
        welcome = guild.get_channel(1291494038427537559)
        message_id = self.bot.config.get('welcome_message_id')
        if not message_id:
            msg = await welcome.send(self.bot.config.get('welcome_message'), view=DropDownView(guild))
            self.bot.config.set('welcome_message_id', msg.id)
        self.bot.add_view(DropDownView(self.missing_member_names()), message_id=message_id)


class DropDown(ui.Select):
    """
    @class DropDown
    @brief A custom dropdown menu for user interaction.
    This class represents a dropdown menu that allows users to select an option from a list. It inherits from `ui.Select` and provides a callback method to handle the user's selection.
    """

    def __init__(self, options):
        """
        @brief Constructor for initializing the dropdown menu.
        @param options A list of options to be displayed in the dropdown menu.
        """

        super().__init__(placeholder='Se chercher', custom_id='dropdown', options=options, min_values=1, max_values=1)
    
    async def callback(self, interaction: Interaction):
        """
        @brief Handles the interaction callback when an option is selected.
        @param interaction The interaction object that triggered the callback.
        This method checks if the selected value is in the list of options. If it is,
        it creates a ConfirmView instance and sends a confirmation message to the user
        asking if they want to confirm their selection.
        """

        selected_value = self.values[0]
        if selected_value in [option.value for option in self.options]:
            view = ConfirmView(selected_value, self.view, interaction)
            await interaction.response.send_message(f"Confirmez-vous la sélection de {selected_value} ?", view=view, ephemeral=True)


class ConfirmView(ui.View):
    """
    @brief A view that presents confirmation and cancellation options.
    This class creates a view with two buttons: one for confirming an action and one for cancelling it.
    """

    def __init__(self, selected_value, dropdown_view, based_interaction):
        """
        Initializes the class with the selected value, dropdown view, and based interaction.
        @param selected_value: The value selected by the user.
        @param dropdown_view: The view containing the dropdown menu.
        @param based_interaction: The interaction that triggered the dropdown menu.
        """

        super().__init__(timeout=None)
        self.selected_value = selected_value
        self.dropdown_view = dropdown_view
        self.add_item(ConfirmButton(label="Confirmer", style=ButtonStyle.success, based_interaction=based_interaction))
        self.add_item(CancelButton(label="Annuler", style=ButtonStyle.danger))


class ConfirmButton(ui.Button):
    """
    @brief A button class for confirming a selection in a Discord bot.
    This class extends the ui.Button class and is used to handle the confirmation
    of a selection made by a user in a Discord bot. It updates the user's roles
    and nickname based on the selected value.
    """

    def __init__(self, label, style, based_interaction):
        """
        @brief Constructor for initializing the class with label, style, and based_interaction.
        @param label The label for the component.
        @param style The style of the component.
        @param based_interaction The interaction associated with the component.
        """

        super().__init__(label=label, style=style)
        self.based_interaction = based_interaction

    async def callback(self, interaction: Interaction):
        """
        @brief Handles the interaction callback for a dropdown selection.
        This method is triggered when a user selects an option from a dropdown menu.
        It updates the user's roles and nickname based on the selected value.
        @param interaction The interaction object containing details about the user's interaction.
        @details
        - If the selected value is 'Invité', the user is assigned a specific role.
        - Otherwise, the selected option is removed from the dropdown menu, the user's nickname is updated,
          and the user is assigned a role based on the selected value.
        @note The method also updates the message content to confirm the selection.
        @return None
        """

        selected_value = self.view.selected_value
        dropdown_view = self.view.dropdown_view
        if selected_value == 'Invité':
            await interaction.user.add_roles(ROLE_GUEST)
        else:
            dropdown_view.options = [option for option in dropdown_view.options if option.value != selected_value]
            dropdown_view.update_options()
            await interaction.user.edit(nick=selected_value)
            await self.based_interaction.message.edit(view=dropdown_view)
            await interaction.user.add_roles(ROLE_FI if selected_value.split(' ')[1] in Common.FI['Nom'].unique() else interaction.guild.get_role(1289241666871627777))
        
        await interaction.response.edit_message(content=f'Sélection confirmée : {selected_value}', view=None)


class CancelButton(ui.Button):
    """
    @brief A button that cancels the current selection when clicked.
    This class extends the ui.Button class to provide a button that, when clicked,
    will edit the message to indicate that the selection has been cancelled.
    """

    def __init__(self, label, style):
        """
        @brief Constructor for initializing the class with label and style.
        @param label The label to be used.
        @param style The style to be applied.
        """

        super().__init__(label=label, style=style)

    async def callback(self, interaction: Interaction):
        """
        @brief Handles the interaction callback to edit the message.
        This asynchronous method is triggered when an interaction occurs. It edits the message content to indicate that the selection has been canceled and removes the view.
        @param interaction The interaction object that triggered the callback.
        """

        await interaction.response.edit_message(content='Sélection annulée.', view=None)


class DropDownView(ui.View):
    """
    @brief A custom view for displaying a dropdown menu with pagination.
    This class creates a dropdown menu populated with options from two CSV files.
    It also includes pagination controls to navigate through the options.
    @details
    - Reads data from 'assets/cyber_sante.csv' and 'assets/cyber.csv'.
    - Combines the data and creates dropdown options for each unique name not present in the guild members.
    - Supports pagination with a fixed number of options per page.
    @note The dropdown options include an 'Invité' option by default.
    """

    def __init__(self, missing_members):

        super().__init__(timeout=None)
        
        self.options = [SelectOption(label='Invité', value='Invité', emoji='👋')] + [SelectOption(label='FI', value=name, emoji='🎓') for name in missing_members['FI']] + [SelectOption(label='FA', value=name, emoji='🎓') for name in missing_members['FA']]

        self.current_page = 1
        self.per_page = 25

        self.update_options()

    def update_options(self):
        """
        @brief Updates the options for the current page and manages pagination controls.
        This method calculates the total number of pages based on the number of options and the number of options per page.
        It then updates the current page to ensure it is within the valid range. The method slices the options list to get
        the options for the current page and clears any existing items. Finally, it adds the dropdown with the current page
        options and the previous/next buttons with appropriate enabled/disabled states.
        @param self The instance of the class containing options, per_page, current_page, and methods to clear and add items.
        """

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
    """
    @brief A button to navigate to the previous page in a paginated view.
    This button is used to decrement the current page number in a paginated view.
    It is disabled when the current page is the first page.
    """

    def __init__(self, disabled=False):
        """
        @brief Constructor for initializing the button.
        @param disabled A boolean indicating whether the button should be disabled. Default is False.
        """

        super().__init__(label='<', style=ButtonStyle.primary, custom_id='previous_page', disabled=disabled)

    async def callback(self, interaction: Interaction):
        """
        @brief Handles the interaction callback for updating the view.
        This asynchronous method is triggered when an interaction occurs. It checks if the current page
        is greater than 1, decrements the current page, updates the view options, and then edits the 
        message with the updated view.
        """
        
        if self.view.current_page > 1:
            self.view.current_page -= 1
            self.view.update_options()
            await interaction.response.edit_message(view=self.view)


class NextButton(ui.Button):
    """
    @brief A button to navigate to the next page in a paginated view.
    This button is used to navigate to the next page of options in a paginated view. 
    It inherits from the ui.Button class and is initialized with a label, style, 
    custom ID, and an optional disabled state.
    @note The callback method handles the interaction when the button is pressed, 
          updating the current page and refreshing the view.
    """

    def __init__(self, disabled=False):
        """
        Initializes the button with the specified parameters.
        @param disabled: A boolean indicating whether the button should be disabled. Defaults to False.
        """

        super().__init__(label='>', style=ButtonStyle.primary, custom_id='next_page', disabled=disabled)

    async def callback(self, interaction: Interaction):
        """
        @brief Handles the interaction callback for pagination.
        This asynchronous method is triggered when an interaction occurs. It calculates the total number of pages based on the number of options and the number of options per page. If the current page is less than the total number of pages, it increments the current page, updates the options in the view, and edits the message to reflect the changes.
        @param interaction The interaction that triggered the callback.
        """

        total_options = len(self.view.options)
        total_pages = (total_options + self.view.per_page - 1) // self.view.per_page
        if self.view.current_page < total_pages:
            self.view.current_page += 1
            self.view.update_options()
            await interaction.response.edit_message(view=self.view)


async def setup(bot: commands.Bot):
    """
    @brief Asynchronous function to set up the Common cog for the bot.
    @param bot The instance of the bot to which the cog will be added.
    This function is used to add the Common cog to the bot instance. It is 
    typically called during the bot's initialization process to ensure that 
    the Common cog is properly set up and ready to handle events and commands.
    """

    await bot.add_cog(Common(bot))
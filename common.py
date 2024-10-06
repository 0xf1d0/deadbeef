import pandas as pd
import re
from discord import app_commands, Interaction, Role, ui, SelectOption, ButtonStyle, Member
from discord.ext import commands

from music import restrict_channel


class Common(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(description="Annonce un message pour un rôle.")
    @commands.has_role(1291503961139838987)
    @restrict_channel(1291397502842703955)
    async def announce(self, ctx: Interaction, message: str, role: Role):
        await ctx.channel.send(f"Annonce: {message}\n\n{role.mention}")

    @app_commands.command(description="Affiche ou inscrit un profil LinkedIn.")
    @app_commands.describe(member='Le profil du membre à afficher', register='Inscrire un profil LinkedIn.')
    async def linkedin(self, ctx: Interaction, member: Member = None, register: str = ''):
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

    @app_commands.command(description="Efface un nombre de messages.")
    @commands.has_permissions(manage_messages=True)
    async def purge(self, ctx: Interaction, limit: int):
        await ctx.response.send_message(f'{limit} messages ont été effacés.', ephemeral=True)
        await ctx.channel.purge(limit=limit)

    @app_commands.command(description="S'attribuer ou s'enlever le rôle de joueur.")
    async def gaming(self, ctx: Interaction):
        role = ctx.guild.get_role(1291867840067932304)
        if role in ctx.user.roles:
            await ctx.user.remove_roles(role)
            await ctx.response.send_message('Rôle de joueur retiré.', ephemeral=True)
        else:
            await ctx.user.add_roles(role)
            await ctx.response.send_message('Rôle de joueur attribué.', ephemeral=True)

    @commands.Cog.listener()
    async def on_ready(self):
        welcome = self.bot.guilds[0].get_channel(1291494038427537559)
        message_id = self.bot.config.get('welcome_message_id')
        if not message_id:
            msg = await welcome.send(self.bot.config.get('welcome_message'), view=DropDownView())
            self.bot.config.set('welcome_message_id', msg.id)
        self.bot.add_view(DropDownView(), message_id=message_id)


class DropDown(ui.Select):
    def __init__(self, options):
        super().__init__(placeholder='Se chercher', custom_id='dropdown', options=options, min_values=1, max_values=1)
    
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
            await interaction.user.add_roles(interaction.guild.get_role(1291510062753517649))
        else:
            dropdown_view.options = [option for option in dropdown_view.options if option.value != selected_value]
            dropdown_view.update_options()
            #await interaction.user.edit(nick=selected_value.title())
            await self.based_interaction.message.edit(view=dropdown_view)
            await interaction.user.add_roles(interaction.guild.get_role(1289241716985040960) if selected_value.split(' ')[1] in dropdown_view.FI['Nom'].unique() else interaction.guild.get_role(1289241666871627777))
        
        await interaction.response.edit_message(content=f'Sélection confirmée : {selected_value}', view=None)


class CancelButton(ui.Button):
    def __init__(self, label, style):
        super().__init__(label=label, style=style)

    async def callback(self, interaction: Interaction):
        await interaction.response.edit_message(content='Sélection annulée.', view=None)

class DropDownView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

        self.FI = pd.read_csv('assets/students_cyber_sante.csv').iloc[:, 1:3]
        self.FA = pd.read_csv('assets/students_cyber.csv').iloc[:, 1:3]
        self.options = [SelectOption(label='Invité', value='Invité', emoji='👋')]
        
        for _, row in pd.concat([self.FI, self.FA]).iterrows():
            name = f'{row.iloc[1]} {row.iloc[0]}'
            self.options.append(SelectOption(label=name, value=name, emoji='🎓'))
        
        self.current_page = 1
        self.per_page = 25

        self.update_options()

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
            await interaction.response.edit_message(view=self.view)


async def setup(bot: commands.Bot):
    await bot.add_cog(Common(bot))
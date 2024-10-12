import pandas as pd
import re
from discord import app_commands, Interaction, ui, SelectOption, ButtonStyle, Member, Embed, File
from discord.ext import commands


class Common(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

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

    @app_commands.command(description="S'attribuer ou s'enlever le rôle de joueur.")
    async def gaming(self, ctx: Interaction):
        role = ctx.guild.get_role(1291867840067932304)
        if role in ctx.user.roles:
            await ctx.user.remove_roles(role)
            await ctx.response.send_message('Rôle de joueur retiré.', ephemeral=True)
        else:
            await ctx.user.add_roles(role)
            await ctx.response.send_message('Rôle de joueur attribué.', ephemeral=True)

    @app_commands.command(description="Affiche le lien d'invitation du serveur.")
    async def invite(self, ctx: Interaction):
        embed = Embed(title='Invitation', description='Scannez ce QR Code et rejoignez le serveur discord du Master Cybersécurité de Paris Cité.\n\nTous profils acceptés, curieux, intéressés ou experts en cybersécurité ! Bot multifonction intégré afin de dynamiser au maximum le serveur.', color=0x8B1538)
        file = File("assets/qrcode.png", filename="invite.png")
        embed.set_image(url='attachment://invite.png')
        embed.set_footer(text=f'Master Cybersécurité - Université Paris Cité - {len([member for member in ctx.guild.members if not member.bot])} membres', icon_url=ctx.guild.icon.url)
        await ctx.response.send_message(file=file, embed=embed)

    @app_commands.command(description="Affiche les informations sur le bot.")
    async def about(self, ctx: Interaction):
        embed = Embed(title='À propos de moi', description='Je suis un bot Discord créé par [Vincent Cohadon](https://fr.linkedin.com/in/vincent-cohadon) pour le Master Cybersécurité de Paris Cité.')
        file = File("assets/f1d0.png", filename="f1d0.png")
        embed.set_thumbnail(url='attachment://f1d0.png')
        await ctx.response.send_message(file=file, embed=embed)
    
    @app_commands.command(description="Liste les membres manquants.")
    async def missing_members_list(self, ctx: Interaction):
        missing_members = []
        member_names = [member.display_name for member in ctx.guild.members]
        FI = pd.read_csv('assets/students_cyber_sante.csv').iloc[:, 1:3]
        FA = pd.read_csv('assets/students_cyber.csv').iloc[:, 1:3]
        for _, row in pd.concat([FI, FA]).iterrows():
            name = f'{row.iloc[1]} {row.iloc[0]}'.title()
            if name not in member_names:
                missing_members.append(name)
        if missing_members:
            await ctx.response.send_message(f'**{len(missing_members)}** Personnes manquantes:\n' + ', '.join(missing_members))
        else:
            await ctx.response.send_message('Tous les membres sont présents.')

    @app_commands.command(description="Glossaire CYBER.")
    @app_commands.choices(option=[
        app_commands.Choice(name="view", value="1"),
        app_commands.Choice(name="add", value="2"),
        app_commands.Choice(name="remove", value="3")
    ])
    @app_commands.checks.has_any_role(1289241716985040960, 1289241666871627777)
    async def glossary(self, interaction: Interaction, option: app_commands.Choice[str], term: str = '', definition: str = ''):
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
        guild = self.bot.guilds[0]
        welcome = guild.get_channel(1291494038427537559)
        message_id = self.bot.config.get('welcome_message_id')
        if not message_id:
            msg = await welcome.send(self.bot.config.get('welcome_message'), view=DropDownView(guild))
            self.bot.config.set('welcome_message_id', msg.id)
        self.bot.add_view(DropDownView(guild), message_id=message_id)

    @commands.Cog.listener()
    async def on_member_remove(self, member: Member):
        channel = member.guild.get_channel(1292059079287504930)
        await channel.send(f'{member.display_name} ({member.mention} ; ({member.name}) ; ({member.nick}) ; ({member.roles} ; ({member.__str__}) a quitté le serveur.')
        guild = member.guild
        welcome = guild.get_channel(1291494038427537559)
        message_id = self.bot.config.get('welcome_message_id')
        if not message_id:
            msg = await welcome.send(self.bot.config.get('welcome_message'), view=DropDownView(guild))
            self.bot.config.set('welcome_message_id', msg.id)
        self.bot.add_view(DropDownView(guild), message_id=message_id)


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
            await interaction.user.edit(nick=selected_value)
            await self.based_interaction.message.edit(view=dropdown_view)
            await interaction.user.add_roles(interaction.guild.get_role(1289241716985040960) if selected_value.split(' ')[1] in dropdown_view.FI['Nom'].unique() else interaction.guild.get_role(1289241666871627777))
        
        await interaction.response.edit_message(content=f'Sélection confirmée : {selected_value}', view=None)


class CancelButton(ui.Button):
    def __init__(self, label, style):
        super().__init__(label=label, style=style)

    async def callback(self, interaction: Interaction):
        await interaction.response.edit_message(content='Sélection annulée.', view=None)


class DropDownView(ui.View):
    def __init__(self, guild):
        super().__init__(timeout=None)

        self.FI = pd.read_csv('assets/students_cyber_sante.csv').iloc[:, 1:3]
        self.FA = pd.read_csv('assets/students_cyber.csv').iloc[:, 1:3]
        self.options = [SelectOption(label='Invité', value='Invité', emoji='👋')]
        member_names = [member.display_name for member in guild.members]
        for _, row in pd.concat([self.FI, self.FA]).iterrows():
            name = f'{row.iloc[1]} {row.iloc[0]}'.title()
            if name not in member_names:
                self.options.append(SelectOption(label=name, value=name, emoji='🎓'))
        print(self.options)
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
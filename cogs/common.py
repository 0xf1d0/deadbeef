import re, aiohttp
from discord import Message, app_commands, Interaction, ui, SelectOption, ButtonStyle, Member, Embed, File, NotFound
from discord.ext import commands

from collections import defaultdict

from utils import CYBER, ROLE_FA, ROLE_FI, ROLE_GUEST, read_csv


class Common(commands.Cog):
    FI = read_csv('assets/cyber_sante.csv')
    FA = read_csv('assets/cyber.csv')
    
    def __init__(self, bot: commands.Bot):
        self.welcome_message_id = 1314385676107645010
        self.bot = bot
        self.conversations = defaultdict(dict)
        self.mistral_payload = lambda messages: {
            'messages': messages,
            'agent_id': 'ag:16fd7f20:20250215:deadbeef:d0525161'
        }

        self.mistral_headers = {
            'Authorization': f'Bearer {bot.config.get("mistral_key")}',
            'Content-Type': 'application/json'
        }
    
    def missing_member_names(self):
        names = {'FI': [], 'FA': []}
        roles = {'FI': ROLE_FI.id, 'FA': ROLE_FA.id}
        data = {'FI': Common.FI, 'FA': Common.FA}

        for key in data:
            for row in data[key]:
                name = f'{row[2]} {row[1]}'.title()
                member = self.bot.guilds[0].get_member_named(name)
                if not member or not member.get_role(roles[key]):
                    names[key].append(name)

        return names

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
        embed = Embed(title='Membres manquants')
        missing_members = self.missing_member_names()
        embed.add_field(name='FI', value=', '.join(missing_members['FI']) or 'Aucun')
        embed.add_field(name='FA', value=', '.join(missing_members['FA']) or 'Aucun')
        await ctx.response.send_message(embed=embed)

    @commands.Cog.listener()
    async def on_ready(self):
        welcome = self.bot.get_guild(CYBER.id).get_channel(1291494038427537559)
        welcome_message = await welcome.fetch_message(self.welcome_message_id)
        await welcome_message.edit(content=self.bot.config.get('welcome_message'), view=DropDownView(self.missing_member_names()))
        self.bot.add_view(DropDownView(self.missing_member_names()), message_id=self.welcome_message_id)

    @commands.Cog.listener()
    async def on_message(self, message: Message):
        if message.author.bot:
            return
        
        channel_id = message.channel.id
        
        if message.reference and message.reference.message_id:
            try:
                replied_message = await message.channel.fetch_message(message.reference.message_id)
                
                if replied_message.author == self.bot.user:
                    conversation = self.conversations[channel_id]
                    
                    conversation.append({
                        'role': 'user',
                        'content': message.content
                    })
                    
                    if len(conversation) > 10:
                        conversation = conversation[-10:]
                    
                    async with message.channel.typing():
                        async with aiohttp.ClientSession() as session:
                            async with session.post('https://api.mistral.ai/v1/agents/completions', headers=self.mistral_headers, json=self.mistral_payload(conversation)) as response:
                                if response.status == 200:
                                    data = await response.json()
                                    r = data['choices'][0]['message']['content']
                                    
                                    conversation.append({
                                        'role': 'assistant',
                                        'content': r
                                    })
                                else:
                                    r = "Sorry, I couldn't generate a response at this time."
                    
                                await message.reply(r)
                    return
            except NotFound:
                pass

        msg = message.content.lower()
        # Vérifier si le message contient "DeadBeef" (nouvelle conversation)
        if 'deadbeef' in msg or 'mistral' in msg:
            conversation = [{
                'role': 'user',
                'content': msg
            }]
            self.conversations[channel_id] = conversation
            async with message.channel.typing():
                async with aiohttp.ClientSession() as session:
                    async with session.post('https://api.mistral.ai/v1/agents/completions', headers=self.mistral_headers, json=self.mistral_payload(conversation)) as response:
                        if response.status == 200:
                            data = await response.json()
                            r = data['choices'][0]['message']['content']
                            conversation.append({
                                'role': 'assistant',
                                'content': r
                            })
                        else:
                            r = "Sorry, I couldn't generate a response at this time."
                        
                        await message.reply(r)

        await self.bot.process_commands(message)

    @commands.Cog.listener()
    async def on_member_remove(self, member: Member):
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
            msg = await welcome.send(self.bot.config.get('welcome_message'), view=DropDownView(self.missing_member_names()))
            self.bot.config.set('welcome_message_id', msg.id)
        self.bot.add_view(DropDownView(self.missing_member_names()), message_id=message_id)


class DropDown(ui.Select):
    def __init__(self, options, missing_members):
        super().__init__(placeholder='Choisir son statut', custom_id='dropdown', options=options, min_values=1, max_values=1)
        self.missing_members = missing_members
    
    async def callback(self, interaction: Interaction):
        selected_value = self.values[0]
        if selected_value in [option.value for option in self.options]:
            view = ConfirmView(selected_value, self.view, interaction, self.missing_members)
            await interaction.response.send_message(f"Confirmez-vous la sélection de {selected_value} ?", view=view, ephemeral=True)


class ConfirmView(ui.View):
    def __init__(self, selected_value, dropdown_view, based_interaction, missing_members):
        super().__init__(timeout=None)
        self.selected_value = selected_value
        self.dropdown_view = dropdown_view
        self.add_item(ConfirmButton(label="Confirmer", style=ButtonStyle.success, based_interaction=based_interaction, missing_members=missing_members))
        self.add_item(CancelButton(label="Annuler", style=ButtonStyle.danger))


class ConfirmButton(ui.Button):
    def __init__(self, label, style, based_interaction, missing_members):
        super().__init__(label=label, style=style)
        self.based_interaction = based_interaction
        self.missing_members = missing_members

    async def callback(self, interaction: Interaction):
        selected_value = self.view.selected_value
        dropdown_view = self.view.dropdown_view
        if selected_value == 'Invité':
            await interaction.user.add_roles(ROLE_GUEST)
        else:
            dropdown_view.options = [option for option in dropdown_view.options if option.value != selected_value]
            dropdown_view.update_options()
            await interaction.user.edit(nick=selected_value)
            await self.based_interaction.message.edit(view=dropdown_view)
            await interaction.user.add_roles(ROLE_FI if self.view.selected_value in self.missing_members['FI'] else ROLE_FA)
        
        await interaction.response.edit_message(content=f'Sélection confirmée : {selected_value}', view=None)


class CancelButton(ui.Button):
    def __init__(self, label, style):
        super().__init__(label=label, style=style)

    async def callback(self, interaction: Interaction):
        await interaction.response.edit_message(content='Sélection annulée.', view=None)


class DropDownView(ui.View):
    def __init__(self, missing_members):
        super().__init__(timeout=None)
        self.missing_members = missing_members
        self.options = [SelectOption(label='Invité', value='Invité', emoji='👋')] + [SelectOption(label=f'FI - {name}', value=name, emoji='🎓') for name in missing_members['FI']] + [SelectOption(label=f'FA - {name}', value=name, emoji='🎓') for name in missing_members['FA']]
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
        self.add_item(DropDown(page_options, self.missing_members))
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

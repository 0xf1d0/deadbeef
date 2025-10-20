import discord, re

from utils import CYBER_COLOR
from ui.confirm import Confirm


class Announcement(discord.ui.Modal, title="Annonce"):
    Title = discord.ui.TextInput(label="Titre", placeholder="Hello World !")
    Description = discord.ui.TextInput(label="Description", placeholder="<@id> to mention someone", style=discord.TextStyle.long)

    async def on_submit(self, interaction: discord.Interaction):
        embed = discord.Embed(title=self.Title.value, description=self.Description.value, color=CYBER_COLOR)
        embed.set_footer(text=f"Annoncé par {interaction.user.display_name}", icon_url=interaction.user.avatar.url)
        mentions = set(re.findall(r'<@\d+>', self.Description.value))
        await interaction.response.send_message('Quels rôles voulez-vous mentionner ?', view=AnnouncementInitialization(embed, mentions), ephemeral=True)


class AnnouncementInitialization(discord.ui.View):
    def __init__(self, embed, mentions):
        super().__init__(timeout=None)
        self.embed = embed
        self.mentions = mentions
    
    @discord.ui.select(cls=discord.ui.RoleSelect, placeholder='Choisissez un/des rôle/s', max_values=4)
    async def select_roles(self, interaction: discord.Interaction, select: discord.ui.RoleSelect):
        value = ' '.join([role.mention for role in select.values])
        self.embed.add_field(name='Rôles concernés', value=value)
        if self.mentions:
            value += ' ' + ' '.join(self.mentions)
        d = {'content': f'|| {value} ||', 'embed': self.embed}
        await interaction.response.send_message(**d, view=Confirm(**d), ephemeral=True)
        self.stop()

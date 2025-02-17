from discord import Embed, Member
from discord.ext import commands

from utils import FI, FA, ROLE_FI, ROLE_FA, WELCOME_MESSAGE
from ui.welcome import DropDownView


class Register(commands.Cog):
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    def missing_member_names(self):
        names = {'FI': [], 'FA': []}
        roles = {'FI': ROLE_FI.id, 'FA': ROLE_FA.id}
        data = {'FI': FI, 'FA': FA}

        for key in data:
            for row in data[key]:
                name = f'{row[2]} {row[1]}'.title()
                member = self.bot.guilds[0].get_member_named(name)
                if not member or not member.get_role(roles[key]):
                    names[key].append(name)

        return names
    
    @commands.Cog.listener()
    async def on_ready(self):
        welcome = self.bot.guilds[0].get_channel(1291494038427537559)
        welcome_message = await welcome.fetch_message(self.welcome_message_id)
        await welcome_message.edit(content=self.bot.config.get('welcome_message'), view=DropDownView(self.missing_member_names()))
        self.bot.add_view(DropDownView(self.missing_member_names()), message_id=self.welcome_message_id)
        
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
        
    
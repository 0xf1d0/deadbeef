from discord import Embed, Member
from discord.ext import commands

from utils import FI, FA, ROLE_FI, ROLE_FA, WELCOME_MESSAGE, WELCOME_CHANNEL, CYBER, ConfigManager
from ui.auth import Authentication


class Register(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.missing_members = None
    
    def missing_member_names(self):
        names = {'FI': [], 'FA': []}
        roles = {'FI': ROLE_FI.id, 'FA': ROLE_FA.id}
        data = {'FI': FI, 'FA': FA}

        for key in data:
            for row in data[key]:
                name = f'{row[2]} {row[1]}'.title()
                member = self.bot.cyber.get_member_named(name)
                if not member or not member.get_role(roles[key]):
                    names[key].append(name)

        return names
    
    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.cyber = self.bot.get_guild(CYBER.id)
        welcome = self.bot.cyber.get_channel(WELCOME_CHANNEL.id)
        self.welcome_message = await welcome.fetch_message(WELCOME_MESSAGE.id)

        await self.welcome_message.edit(content=ConfigManager.get('welcome_message'), view=Authentication(self.missing_member_names()))
        # self.bot.add_view(view, message_id=WELCOME_MESSAGE.id)

    @commands.Cog.listener()
    async def on_member_remove(self, member: Member):
        guild = member.guild
        channel = guild.get_channel(1292059079287504930)
        embed = Embed(title=f'{member} ({member.id}) left')\
            .add_field(name='Name', value=member.name)\
            .add_field(name='Display Name', value=member.display_name)\
            .add_field(name='Nick', value=member.nick)\
            .add_field(name='Roles', value='\n'.join([f"{i+1}. {role.mention if role.name != '@everyone' else role.name} - {role.id}" for i, role in enumerate(member.roles)]))

        await channel.send(embed=embed)
        
        # self.missing_members = self.missing_member_names()

        """view = AuthenticationView(self.missing_members)
        await self.welcome_message.edit(content=self.bot.config.get('welcome_message'), view=view)
        self.bot.add_view(view, message_id=WELCOME_CHANNEL.id)"""


async def setup(bot: commands.Bot):
    await bot.add_cog(Register(bot))

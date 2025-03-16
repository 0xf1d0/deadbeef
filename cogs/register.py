from discord import Embed, Member
from discord.ext import commands

from utils import WELCOME_MESSAGE, WELCOME_CHANNEL, CYBER, ConfigManager
from ui.auth import Authentication
from api.api import MistralAI, RootMe


class Register(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.cyber = self.bot.get_guild(CYBER.id)
        welcome = self.bot.cyber.get_channel(WELCOME_CHANNEL.id)
        self.welcome_message = await welcome.fetch_message(WELCOME_MESSAGE.id)
        
        self.bot.mistral = MistralAI()
        self.bot.rootme = RootMe()

        await self.welcome_message.edit(content=ConfigManager.get('welcome_message'), view=Authentication(self.bot.rootme))

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


async def setup(bot: commands.Bot):
    await bot.add_cog(Register(bot))

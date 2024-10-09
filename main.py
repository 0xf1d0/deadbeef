from discord.ext import commands
from discord import Intents, Object

from utils import ConfigManager

CYBER = Object(1289169690895323167)


class DeadBeef(commands.Bot):
    def __init__(self):
        intents = Intents.default()
        intents.message_content = True
        intents.members = True
        self.config = ConfigManager()
        super().__init__(command_prefix='!', intents=intents)

    async def setup_hook(self) -> None:
        await self.load_extension('music')
        await self.load_extension('common')
        await self.load_extension('admin')
        await self.load_extension('reminder')
        self.tree.copy_global_to(guild=CYBER)
        await self.tree.sync(guild=CYBER)


if __name__ == '__main__':
    bot = DeadBeef()
    bot.run(bot.config.get('token'))

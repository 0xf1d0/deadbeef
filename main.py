from discord.ext import commands
from discord import Intents
import os, re

from utils import ConfigManager, CYBER
from api.api import MistralAI, RootMe


class DeadBeef(commands.Bot):
    def __init__(self):
        intents = Intents.default()
        intents.message_content = True
        intents.members = True
        self.mistral = MistralAI()
        self.rootme = RootMe()
        ConfigManager.load()
        super().__init__(command_prefix='!', intents=intents)

    async def setup_hook(self) -> None:
        for file in os.listdir("cogs"):
            if not re.fullmatch(r"[a-z]*\.py", file):
                continue  # Skip non-python files

            name = file[:-3]
            await self.load_extension(f"cogs.{name}")
        self.tree.copy_global_to(guild=CYBER)
        await self.tree.sync(guild=CYBER)


if __name__ == '__main__':
    bot = DeadBeef()
    bot.run(ConfigManager.get('token'))

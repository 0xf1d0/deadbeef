from discord.ext import commands
from discord import Intents, Object
import os, re

from utils import ConfigManager

CYBER = Object(1289169690895323167)


class DeadBeef(commands.Bot):
    """
    @brief A custom Discord bot class that extends commands.Bot.
    This class initializes the bot with specific intents and loads command extensions from the 'cogs' directory.
    @details
    The bot is configured with message content and member intents enabled. It loads all Python files in the 'cogs' directory as command extensions and synchronizes the command tree with a specific guild.
    """

    def __init__(self):
        """
        Initializes the bot with specified intents and configuration.
        @details
        This constructor sets up the bot with default intents, enabling message content and member intents.
        It also initializes the configuration manager and calls the superclass constructor with a command prefix.
        @param None
        """

        intents = Intents.default()
        intents.message_content = True
        intents.members = True
        self.config = ConfigManager()
        super().__init__(command_prefix='!', intents=intents)

    async def setup_hook(self) -> None:
        """
        @brief Asynchronously sets up the bot by loading all extensions from the 'cogs' directory and synchronizing command trees.
        This method iterates through all files in the 'cogs' directory, and for each Python file, it loads the corresponding extension.
        After loading all extensions, it copies the global command tree to a specific guild and synchronizes it.
        @note Only files with names consisting of lowercase letters and ending with '.py' are considered as valid extensions.
        @exception Any exceptions raised during the loading of extensions or synchronization of the command tree will propagate up the call stack.
        @return None
        """

        for file in os.listdir("cogs"):
            if not re.fullmatch(r"[a-z]*\.py", file):
                continue  # Skip non-python files

            name = file[:-3]
            await self.load_extension(f"cogs.{name}")
        self.tree.copy_global_to(guild=CYBER)
        await self.tree.sync(guild=CYBER)


if __name__ == '__main__':
    
    bot = DeadBeef()
    bot.run(bot.config.get('token'))

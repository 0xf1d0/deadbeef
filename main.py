from discord.ext import commands
from discord import Intents, Interaction, app_commands
import os, re

from utils import ConfigManager, CYBER


class DeadBeef(commands.Bot):
    def __init__(self):
        intents = Intents.default()
        intents.message_content = True
        intents.members = True
        ConfigManager.load()
        super().__init__(command_prefix=commands.when_mentioned_or('!'), intents=intents)

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
    
    @bot.tree.error
    async def on_command_error(interaction: Interaction, error: app_commands.AppCommandError):
        """Error handler for application commands."""
        if isinstance(error, app_commands.errors.MissingPermissions):
            await interaction.response.send_message("Vous n'avez pas la permission d'exécuter cette commande.", ephemeral=True)
        else:
            await interaction.response.send_message(f"Une erreur est survenue : {str(error)}", ephemeral=True)
            raise error

    bot.run(ConfigManager.get('token'))

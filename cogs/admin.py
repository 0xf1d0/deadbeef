from discord.ext import commands
from discord import app_commands, Interaction, ui, ButtonStyle, Embed, SelectOption
import functools, re


def restrict_channel(channel_id):
    """
    @brief A decorator to restrict the usage of a command to a specific channel.
    @param channel_id The ID of the channel where the command is allowed to be used.
    @return A decorator that wraps the command function to enforce the channel restriction.
    The decorator checks if the command is invoked in the specified channel. If not, it sends a message to the user indicating that the command can only be used in the specified channel.
    """

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(self, ctx: Interaction, *args, **kwargs):
            if ctx.channel.id != channel_id:
                await ctx.response.send_message(f"Cette commande ne peut être utilisée que dans le salon <#{channel_id}>.", ephemeral=True)
                return
            return await func(self, ctx, *args, **kwargs)
        return wrapper
    return decorator

class Admin(commands.Cog):
    """
    @brief A class that represents administrative commands for a Discord bot.
    This class contains commands that can be used by administrators to manage the server,
    such as announcing messages and purging messages.
    """

    def __init__(self, bot: commands.Bot):
        """
        @brief Constructor for the admin cog.
        @param bot The bot instance that this cog will be attached to.
        """

        self.bot = bot
    
    @app_commands.command(description="Annoncer un message.")
    @app_commands.describe(title='Le titre de l\'annonce.', message='Le message à annoncer.')
    @app_commands.checks.has_any_role(1291503961139838987, 1293714448263024650)
    async def announce(self, ctx: Interaction, title: str, message: str):
        """
        @brief Sends an announcement message with an embed and optional role mentions.
        @param ctx The interaction context.
        @param title The title of the announcement.
        @param message The content of the announcement, where '\\n' will be replaced with newlines.
        This function creates an embed with the given title and message, sets the footer to display the announcer's name and avatar,
        and identifies any user mentions in the message. It then prompts the user to select roles to mention in the announcement.
        """

        embed = Embed(title=title, description=message.replace('\\n', '\n'), color=0x8B1538)
        embed.set_footer(text=f"Annoncé par {ctx.user.display_name}", icon_url=ctx.user.avatar.url)
        matches = []
        for match in re.finditer(r'<@(\d{17}|\d{18})>', message):
            if match.group(1) not in matches:
                matches.append(match)
        await ctx.response.send_message('Quels rôles voulez-vous mentionner ?', view=DropdownView(ctx.guild, embed, matches), ephemeral=True)
    
    @announce.error
    async def announce_error(self, interaction: Interaction, error: Exception):
        """
        @brief Sends an error message to the user if they lack the required role to use a command.
        @param interaction The interaction that triggered the error.
        @param error The exception that was raised.
        This function checks if the error is an instance of `app_commands.MissingAnyRole`. If so, it sends a message to the user indicating that they do not have permission to use the command.
        """

        if isinstance(error, app_commands.MissingAnyRole):
            await interaction.response.send_message("Vous n'avez pas la permission d'utiliser cette commande.", ephemeral=True)

    @app_commands.command(description="Efface un nombre de messages.")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def purge(self, ctx: Interaction, limit: int):
        """
        @brief Purges a specified number of messages from the channel.
        @param ctx The interaction context.
        @param limit The number of messages to purge.
        This function sends a confirmation message indicating the number of messages
        that have been deleted and then purges the specified number of messages from
        the channel.
        """

        await ctx.response.send_message(f'{limit} messages ont été effacés.', ephemeral=True)
        await ctx.channel.purge(limit=limit)

    @purge.error
    async def purge_error(self, interaction: Interaction, error: Exception):
        """
        Handles errors that occur during the execution of the purge command.
        @param interaction: The interaction that triggered the error.
        @type interaction: Interaction
        @param error: The exception that was raised.
        @type error: Exception
        If the error is due to missing permissions, sends a message to the user indicating they do not have permission to use the command.
        """

        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("Vous n'avez pas la permission d'utiliser cette commande.", ephemeral=True)


class DropdownView(ui.View):
    """
    @brief A custom view that contains a dropdown menu for selecting roles.
    This class creates a dropdown menu populated with roles from a given guild,
    excluding the '@everyone' and 'DeadBeef' roles. The selected roles are used
    to update an embed and mentions.
    """

    def __init__(self, guild, embed, mentions):
        """
        Initializes the admin cog with the given guild, embed, and mentions.
        @param guild: The guild object containing roles and other guild-specific information.
        @type guild: discord.Guild
        @param embed: The embed object to be used for displaying messages.
        @type embed: discord.Embed
        @param mentions: The mentions object containing user mentions.
        @type mentions: discord.Mentions
        """

        super().__init__()
        self.add_item(Dropdown([SelectOption(label=role.name, value=role.id) for role in guild.roles if role.name not in ['@everyone', 'DeadBeef']], len(guild.roles) - 2, embed, mentions))


class Dropdown(ui.Select):
    """
    @brief A custom dropdown menu for selecting roles in a Discord bot.
    This class extends the ui.Select class to create a dropdown menu that allows users to select roles.
    It also updates an embed with the selected roles and mentions if provided.
    @note This class is intended to be used within a Discord bot using the discord.py library.
    """

    def __init__(self, options, max_values, embed, mentions):
        """
        Initializes the admin cog with the given parameters.
        @param options: The list of options to be displayed.
        @param max_values: The maximum number of values that can be selected.
        @param embed: The embed object to be used.
        @param mentions: The mentions to be included.
        """

        super().__init__(placeholder='Choisissez un rôle', options=options, min_values=1, max_values=max_values)
        self.embed = embed
        self.mentions = mentions
    
    async def callback(self, interaction: Interaction):
        """
        @brief Handles the interaction callback for the admin cog.
        This method is triggered when an interaction occurs. It processes the roles
        selected by the user, constructs an embed message with the relevant roles,
        and sends a response message with a confirmation view.
        @param interaction The interaction object that triggered the callback.
        @return None
        """

        roles = [interaction.guild.get_role(int(value)) for value in self.values]
        value = ' '.join([role.mention for role in roles])
        self.embed.add_field(name='Rôles concernés', value=value)
        if self.mentions:
            value += ' ' + ' '.join([match.group(0) for match in self.mentions])
        await interaction.response.send_message(embed=self.embed, view=ConfirmView(self.embed, value), ephemeral=True)


class ConfirmView(ui.View):
    """
    @brief A custom view for confirmation with an embedded message.
    This class creates a view that includes a confirmation button. The button
    is initialized with an embed message and a value.
    """

    def __init__(self, embed, value):
        """
        @brief Constructor for the class.
        @param embed The embed object to be used.
        @param value The value to be passed to the ConfirmButton.
        """

        super().__init__()
        self.add_item(ConfirmButton(embed, value))


class ConfirmButton(ui.Button):
    """
    @brief A custom button class for confirming actions in a Discord bot.
    This class inherits from `ui.Button` and is used to create a button that,
    when clicked, sends a confirmation message along with an embed to the channel.
    """

    def __init__(self, embed, value):
        """
        @brief Constructor for the class.
        @param embed The embed object to be used.
        @param value The value to be set.
        """

        super().__init__(label='Confirmer', style=ButtonStyle.success)
        self.embed = embed
        self.value = value

    async def callback(self, interaction: Interaction):
        """
        @brief Handles the interaction callback.
        This asynchronous method sends a message to the interaction channel with the specified value and embed,
        and then sends a confirmation message to the user.
        @param interaction The interaction object that triggered the callback.
        @return None
        """

        await interaction.channel.send(f'|| {self.value} ||', embed=self.embed)
        await interaction.response.send_message('Annonce envoyée.', ephemeral=True)


async def setup(bot: commands.Bot):
    """
    @brief Asynchronous function to set up the Admin cog for the bot.
    @param bot The instance of the bot to which the Admin cog will be added.
    This function initializes the Admin cog and adds it to the bot.
    """

    await bot.add_cog(Admin(bot))

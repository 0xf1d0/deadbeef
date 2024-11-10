from discord.ext import commands
from discord import Interaction, Embed, NotFound, app_commands


def check_if_user_or_roles(interaction: Interaction) -> bool:
    """
    @brief Checks if the user has a specific ID or any of the specified role IDs.
    @param interaction The interaction object containing user information.
    @return True if the user's ID matches the specified ID or if the user has any of the specified role IDs, False otherwise.
    """

    return interaction.user.id == 454935749767200768 or any([role.id in [1293714448263024650, 1291503961139838987] for role in interaction.user.roles])

class Tools(commands.Cog):
    """
    @brief A class to manage tools within a Discord bot.
    This class provides commands to add, edit, and remove tools from a list,
    and updates an embed message in a specified channel with the current list of tools.
    """
    
    def __init__(self, bot: commands.Bot):
        """
        Initializes the Tools cog.
        @param bot: The bot instance that this cog will be attached to.
        @type bot: commands.Bot
        """

        self.bot = bot
        self.tools = self.load_tools()

    def load_tools(self):
        """
        @brief Loads the tools configuration for the bot.
        @return A list of tools from the bot's configuration. If no tools are configured, returns an empty list.
        """

        return self.bot.config.get('tools', [])

    def save_tools(self):
        """
        @brief Saves the current state of tools to the bot's configuration.
        This method updates the bot's configuration by setting the 'tools' key 
        to the current state of the tools attribute.
        @return None
        """

        self.bot.config.set('tools', self.tools)

    def update_embed(self, embed, category, tools):
        """
        @brief Updates or adds a field in the embed with the given category and tools.
        This method searches for a field in the embed with the name matching the given category.
        If found, it updates the field with the new list of tools. If not found, it adds a new field
        with the category name and the list of tools.
        @param embed The embed object to be updated.
        @param category The category name to be used as the field name in the embed.
        @param tools A list of dictionaries, where each dictionary represents a tool with 'tool' and 'description' keys.
        @return None
        """

        for index, field in enumerate(embed.fields):
            if field.name == f'__{category.upper()}__':
                new_value = "\n".join(
                    [f"{i+1}. **{tool['tool']}**{': ' + tool['description'] if tool['description'] else ''}" for i, tool in enumerate(tools)]
                )
                embed.set_field_at(index, name=field.name, value=new_value, inline=False)
                return
        new_value = "\n".join(
            [f"{i+1}. **{tool['tool']}**{': ' + tool['description'] if tool['description'] else ''}" for i, tool in enumerate(tools)]
        )
        embed.add_field(name=f'__{category.upper()}__', value=new_value, inline=False)

    @app_commands.command(description="Ajouter, modifier ou supprimer un outil.")
    @app_commands.describe(category="Choisir la catégorie.", tool="Nom de l'outil.", description="Description de l'outil.", index="Index de l'outil à modifier ou supprimer.")
    @app_commands.check(check_if_user_or_roles)
    @app_commands.choices(option=[
        app_commands.Choice(name="add", value="1"),
        app_commands.Choice(name="edit", value="2"),
        app_commands.Choice(name="remove", value="3")
    ])
    async def tool(self, interaction: Interaction, option: app_commands.Choice[str], category: str, tool: str = None, description: str = None, index: int = None):
        """
        @brief Handles the tool management commands (add, edit, remove) for the bot.
        @param interaction The interaction object that triggered this command.
        @param option The option chosen by the user (add, edit, remove).
        @param category The category of the tool.
        @param tool The name of the tool (optional for edit and remove).
        @param description The description of the tool (optional).
        @param index The index of the tool in the category (required for edit and remove).
        @return None
        This function handles three main operations:
        - Adding a new tool to a specified category.
        - Editing an existing tool in a specified category.
        - Removing an existing tool from a specified category.
        The function updates the message containing the tools list in the specified channel,
        and saves the updated tools list to the bot's configuration.
        """

        tools_channel = interaction.guild.get_channel(1294665610093138061)
        tools_message_id = self.bot.config.get('tools_message_id')
        msg = None

        if tools_message_id:
            try:
                msg = await tools_channel.fetch_message(tools_message_id)
            except NotFound:
                pass

        formatted_time = interaction.created_at.strftime("%Y-%m-%d %H:%M:%S")

        if option.value == "1":  # Add tool
            store = {
                "category": category,
                "fields": [
                    {
                        "tool": tool,
                        "description": description if description else ""
                    }
                ]
            }

            if msg:
                for existing_tool in self.tools:
                    if existing_tool['category'].lower() == category.lower():
                        existing_tool['fields'].append({
                            "tool": tool,
                            "description": description if description else ""
                        })
                        self.update_embed(msg.embeds[0], category, existing_tool['fields'])
                        msg.embeds[0].set_footer(text=f"Last update by {interaction.user.display_name} at {formatted_time}", icon_url=interaction.user.avatar.url)
                        await msg.edit(embeds=msg.embeds)
                        break
                else:
                    self.tools.append(store)
                    self.update_embed(msg.embeds[0], category, store['fields'])
                    msg.embeds[0].set_footer(text=f"Last update by {interaction.user.display_name} at {formatted_time}", icon_url=interaction.user.avatar.url)
                    await msg.edit(embeds=msg.embeds)
            else:
                embed = Embed(title='Cyber Tools', description='This embed contains a list of many hacking tools and websites to learn ethical hacking. The goal is to sumup in one place all the cybersecurity stuff !')
                self.update_embed(embed, category, store['fields'])
                embed.set_footer(text=f"Last update by {interaction.user.display_name} at {formatted_time}", icon_url=interaction.user.avatar.url)
                msg = await tools_channel.send(embeds=[embed])
                self.bot.config.set('tools_message_id', msg.id)

            self.save_tools()

            await interaction.response.send_message(f"Outil {tool} créé dans la catégorie {category}", ephemeral=True)

        elif option.value == "2":  # Edit tool
            if msg and index is not None:
                for existing_tool in self.tools:
                    if existing_tool['category'].lower() == category.lower():
                        if 0 <= index - 1 < len(existing_tool['fields']):
                            if tool is not None:
                                existing_tool['fields'][index - 1]['tool'] = tool
                            existing_tool['fields'][index - 1]['description'] = description if description else existing_tool['fields'][index - 1]['description']
                            self.update_embed(msg.embeds[0], category, existing_tool['fields'])
                            msg.embeds[0].set_footer(text=f"Last update by {interaction.user.display_name} at {formatted_time}", icon_url=interaction.user.avatar.url)
                            await msg.edit(embeds=msg.embeds)
                            self.save_tools()
                            await interaction.response.send_message(f"Outil {existing_tool['fields'][index - 1]['tool']} dans la catégorie {category} modifié.", ephemeral=True)
                            return
                await interaction.response.send_message("Index ou catégorie non trouvée.", ephemeral=True)
            else:
                await interaction.response.send_message("Aucun message de tool trouvé ou index non fourni.", ephemeral=True)

        elif option.value == "3":  # Remove tool
            if msg and index is not None:
                for existing_tool in self.tools:
                    if existing_tool['category'].lower() == category.lower():
                        if 0 <= index - 1 < len(existing_tool['fields']):
                            del existing_tool['fields'][index - 1]
                            if existing_tool['fields']:
                                self.update_embed(msg.embeds[0], category, existing_tool['fields'])
                            else:
                                for field_index, field in enumerate(msg.embeds[0].fields):
                                    if field.name == f'__{category.upper()}__':
                                        msg.embeds[0].remove_field(field_index)
                                        break
                            msg.embeds[0].set_footer(text=f"Last update by {interaction.user.display_name} at {formatted_time}", icon_url=interaction.user.avatar.url)
                            await msg.edit(embeds=msg.embeds)
                            self.save_tools()
                            await interaction.response.send_message(f"Outil dans la catégorie {category} supprimé.", ephemeral=True)
                            return
                await interaction.response.send_message("Index ou catégorie non trouvée.", ephemeral=True)
            else:
                await interaction.response.send_message("Aucun message de tool trouvé ou index non fourni.", ephemeral=True)

    @tool.error
    async def calendar_error(self, interaction: Interaction, error: Exception):
        """
        Handles errors that occur during the execution of calendar-related commands.
        This method is called when an error is raised while processing an interaction
        with a calendar command. It checks the type of error and sends an appropriate
        response message to the user.
        @param interaction: The interaction that triggered the error.
        @type interaction: Interaction
        @param error: The exception that was raised.
        @type error: Exception
        """

        if isinstance(error, app_commands.CheckFailure):
            await interaction.response.send_message("Vous n'avez pas la permission d'utiliser cette commande.", ephemeral=True)


async def setup(bot: commands.Bot):
    """
    @brief Asynchronous function to set up the Tools cog.
    This function is used to add the Tools cog to the bot.
    @param bot The instance of the bot to which the cog will be added.
    """

    await bot.add_cog(Tools(bot))
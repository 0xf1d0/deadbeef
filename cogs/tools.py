from discord.ext import commands
from discord import Interaction, Embed, NotFound, app_commands


def check_if_user_or_roles(interaction: Interaction) -> bool:
    return interaction.user.id == 454935749767200768 or any([role.id in [1293714448263024650, 1291503961139838987] for role in interaction.user.roles])

class Tools(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.tools = self.load_tools()

    def load_tools(self):
        return self.bot.config.get('tools', [])

    def save_tools(self):
        self.bot.config.set('tools', self.tools)

    def update_embed(self, embed, category, tools):
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
        if isinstance(error, app_commands.CheckFailure):
            await interaction.response.send_message("Vous n'avez pas la permission d'utiliser cette commande.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Tools(bot))
from discord.ext import commands
from discord import Interaction, app_commands


def check_if_user(interaction: Interaction) -> bool:
    return interaction.user.id in [454935749767200768, 253616158895243264]

class Tools(commands.Cog):
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.tools = bot.config.get('tools', [])
        
    def save_tools(self):
        self.bot.config.set('tools', self.tools)

    def update_embed(self, embed, category, tools):
        new_value = "\n".join(
            [f"{i+1}. **{tool['tool']}**{': ' + tool['description'] if tool['description'] else ''}" for i, tool in enumerate(tools)]
        )
        for index, field in enumerate(embed.fields):
            if field.name == f'__{category.upper()}__':
                embed.set_field_at(index, name=field.name, value=new_value, inline=False)
                break
        else:
            embed.add_field(name=f'__{category.upper()}__', value=new_value, inline=False)

    @app_commands.command(description="Ajouter, modifier ou supprimer un outil.")
    @app_commands.describe(category="Choisir la catégorie.", tool="Nom de l'outil.", description="Description de l'outil.", index="Index de l'outil à modifier ou supprimer.")
    @app_commands.check(check_if_user)
    @app_commands.choices(option=[
        app_commands.Choice(name="add", value="1"),
        app_commands.Choice(name="edit", value="modifié"),
        app_commands.Choice(name="remove", value="supprimé")
    ])
    async def tool(self, interaction: Interaction, option: app_commands.Choice[str], category: str, tool: str = None, description: str = '', index: int = 1):
        tools_channel = interaction.guild.get_channel(1294665610093138061)
        msg = await tools_channel.fetch_message(1294690496815566983)

        formatted_time = interaction.created_at.strftime("%Y-%m-%d %H:%M:%S")
        
        match option.name:
            case "add":
                store = {
                    "category": category,
                    "fields": [
                        {
                            "tool": tool,
                            "description": description
                        }
                    ]
                }
                
                for existing_tool in self.tools:
                    if existing_tool['category'].lower() == category.lower():
                        existing_tool['fields'].append(store['fields'][0])
                        self.update_embed(msg.embeds[0], category, existing_tool['fields'])
                        msg.embeds[0].set_footer(text=f"Last update by {interaction.user.display_name} at {formatted_time}", icon_url=interaction.user.avatar.url)
                        print(msg.embeds[0].footer)
                        await msg.edit(embeds=msg.embeds)
                        break
                else:
                    self.tools.append(store)
                    self.update_embed(msg.embeds[0], category, store['fields'])
                    msg.embeds[0].set_footer(text=f"Last update by {interaction.user.display_name} at {formatted_time}", icon_url=interaction.user.avatar.url)
                    await msg.edit(embeds=msg.embeds)
                
                self.save_tools()

                await interaction.response.send_message(f"Outil {tool} créé dans la catégorie {category}", ephemeral=True)
                
            case "edit" | "remove":
                for existing_tool in self.tools:
                    if existing_tool['category'].lower() == category.lower():
                        if 0 <= index - 1 < len(existing_tool['fields']):
                            t = existing_tool['fields'][index - 1]['tool']
                            if option.name == "edit":
                                if tool is not None:
                                    existing_tool['fields'][index - 1]['tool'] = tool
                                existing_tool['fields'][index - 1]['description'] = description if description else existing_tool['fields'][index - 1]['description']
                                self.update_embed(msg.embeds[0], category, existing_tool['fields'])
                            else:
                                del existing_tool['fields'][index - 1]
                                if existing_tool['fields']:
                                    self.update_embed(msg.embeds[0], category, existing_tool['fields'])
                                else:
                                    for field_index, field in enumerate(msg.embeds[0].fields):
                                        if field.name == f'__{category.upper()}__':
                                            msg.embeds[0].remove_field(field_index)
                                            break
                            await msg.edit(embeds=msg.embeds)
                            await interaction.response.send_message(f"Outil {t} dans la catégorie {category} {option.value}.", ephemeral=True)
                            msg.embeds[0].set_footer(text=f"Last update by {interaction.user.display_name} at {formatted_time}", icon_url=interaction.user.avatar.url)
                            self.save_tools()
                        else:
                            await interaction.response.send_message("Index non trouvé.", ephemeral=True)
                        break
                else:
                    await interaction.response.send_message("Catégorie non trouvée.", ephemeral=True)

    @tool.error
    async def calendar_error(self, interaction: Interaction, error: Exception):
        if isinstance(error, app_commands.CheckFailure):
            await interaction.response.send_message("Vous n'avez pas la permission d'utiliser cette commande.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Tools(bot))

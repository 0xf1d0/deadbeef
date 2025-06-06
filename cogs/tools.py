from discord.ext import commands
from discord import Interaction, app_commands, Embed

from utils import ConfigManager


def check_if_user(interaction: Interaction) -> bool:
    return interaction.user.id in [454935749767200768, 253616158895243264]

def update_embed(embeds, category, tools):
    new_value = "\n".join(
        [f"{i+1}. **{tool['tool']}**{': ' + tool['description'] if tool['description'] else ''}" for i, tool in enumerate(tools)]
    )
    for embed in embeds:
        for index, field in enumerate(embed.fields):
            if field.name == f'__{category.upper()}__':
                embed.set_field_at(index, name=field.name, value=new_value, inline=False)
                return
    for embed in embeds:
        if len(embed.fields) < 4:
            embed.add_field(name=f'__{category.upper()}__', value=new_value, inline=False)
            return
    new_embed = Embed()
    new_embed.add_field(name=f'__{category.upper()}__', value=new_value, inline=False)
    embeds.append(new_embed)


class Tools(commands.Cog):
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
        
        tools = ConfigManager.get('tools', [])

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
                
                for existing_tool in tools:
                    if existing_tool['category'].lower() == category.lower():
                        existing_tool['fields'].append(store['fields'][0])
                        update_embed(msg.embeds, category, existing_tool['fields'])
                        msg.embeds[-1].set_footer(text=f"Last update by {interaction.user.display_name} at {formatted_time}", icon_url=interaction.user.avatar.url)
                        await msg.edit(embeds=msg.embeds)
                        break
                else:
                    tools.append(store)
                    update_embed(msg.embeds, category, store['fields'])
                    msg.embeds[-1].set_footer(text=f"Last update by {interaction.user.display_name} at {formatted_time}", icon_url=interaction.user.avatar.url)
                    await msg.edit(embeds=msg.embeds)
                
                ConfigManager.set('tools', tools)

                await interaction.response.send_message(f"Outil {tool} créé dans la catégorie {category}", ephemeral=True)
                
            case "edit" | "remove":
                for existing_tool in tools:
                    if existing_tool['category'].lower() == category.lower():
                        if 0 <= index - 1 < len(existing_tool['fields']):
                            t = existing_tool['fields'][index - 1]['tool']
                            if option.name == "edit":
                                if tool is not None:
                                    existing_tool['fields'][index - 1]['tool'] = tool
                                existing_tool['fields'][index - 1]['description'] = description if description else existing_tool['fields'][index - 1]['description']
                                update_embed(msg.embeds, category, existing_tool['fields'])
                            else:
                                del existing_tool['fields'][index - 1]
                                if existing_tool['fields']:
                                    update_embed(msg.embeds, category, existing_tool['fields'])
                                else:
                                    for embed in msg.embeds:
                                        for field_index, field in enumerate(embed.fields):
                                            if field.name == f'__{category.upper()}__':
                                                embed.remove_field(field_index)
                                                break
                            msg.embeds[-1].set_footer(text=f"Last update by {interaction.user.display_name} at {formatted_time}", icon_url=interaction.user.avatar.url)
                            await msg.edit(embeds=msg.embeds)
                            await interaction.response.send_message(f"Outil {t} dans la catégorie {category} {option.value}.", ephemeral=True)
                            ConfigManager.set('tools', tools)
                        else:
                            await interaction.response.send_message("Index non trouvé.", ephemeral=True)
                        break
                else:
                    await interaction.response.send_message("Catégorie non trouvée.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Tools(bot))

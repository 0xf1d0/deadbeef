from discord.ext import commands, app_commands
from discord import Interaction, Embed, NotFound, TextChannel


class Tools(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.tools = self.load_tools()

    def load_tools(self):
        return self.bot.config.get('tools', [])

    def save_tools(self):
        self.bot.config.set('tools', self.tools)

    @app_commands.command(description="Ajouter ou modifier un outil.")
    @app_commands.describe(category="Choisir la catégorie.", tool="Nom de l'outil.", description="Description de l'outil.")
    @app_commands.checks.has_any_role(1291503961139838987, 1293714448263024650)
    @app_commands.choices(option=[
        app_commands.Choice(name="add", value="1"),
        app_commands.Choice(name="edit", value="2"),
        app_commands.Choice(name="remove", value="3")
    ])
    async def tool(self, interaction: Interaction, option: app_commands.Choice[str], category: str, tool: str, description: str = None):
        tools_channel = interaction.guild.get_channel(1294665610093138061)
        tools_message_id = self.bot.config.get('tools_message_id')
        msg = None

        if tools_message_id:
            try:
                msg = await tools_channel.fetch_message(tools_message_id)
            except NotFound:
                pass

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
                for field in msg.embeds[0].fields:
                    if field.name == f'__{category.upper()}__':
                        field.value += f"\n- **{tool}**{': ' + description if description else ''}"
                        await msg.edit(embeds=msg.embeds)
                        break
                else:
                    msg.embeds[0].add_field(name=f'__{category.upper()}__', value=f"- **{tool}**{': ' + description if description else ''}", inline=False)
                    await msg.edit(embeds=msg.embeds)
            else:
                embed = Embed(title='Cyber Tools')
                embed.add_field(name=f'__{category.upper()}__', value=f"- **{tool}**{': ' + description if description else ''}", inline=False)
                msg = await tools_channel.send(embeds=[embed])
                self.bot.config.set('tools_message_id', msg.id)

            for existing_tool in self.tools:
                if existing_tool['category'].lower() == category.lower():
                    existing_tool['fields'].append({
                        "tool": tool,
                        "description": description if description else ""
                    })
                    break
            else:
                self.tools.append(store)

            self.save_tools()

            await interaction.response.send_message(f"Outil {tool} créé dans la catégorie {category}", ephemeral=True)

        elif option.value == "2":  # Edit tool
            if msg:
                for field in msg.embeds[0].fields:
                    if field.name == f'__{category.upper()}__':
                        for tool_field in field.value.split('\n'):
                            if tool_field.startswith(f"- **{tool}**"):
                                field.value = field.value.replace(tool_field, f"- **{tool}**{': ' + description if description else ''}")
                                await msg.edit(embeds=msg.embeds)
                                break
                        break
                else:
                    await interaction.response.send_message("Catégorie non trouvée.", ephemeral=True)
                    return

                for existing_tool in self.tools:
                    if existing_tool['category'].lower() == category.lower():
                        for field in existing_tool['fields']:
                            if field['tool'].lower() == tool.lower():
                                field['description'] = description if description else ""
                                break
                        break

                self.save_tools()

                await interaction.response.send_message(f"Outil {tool} dans la catégorie {category} modifié.", ephemeral=True)
            else:
                await interaction.response.send_message("Aucun message de tool trouvé.", ephemeral=True)

        elif option.value == "3":  # Remove tool
            if msg:
                for field in msg.embeds[0].fields:
                    if field.name == f'__{category.upper()}__':
                        new_value = "\n".join(
                            tool_field for tool_field in field.value.split('\n') if not tool_field.startswith(f"- **{tool}**")
                        )
                        field.value = new_value
                        await msg.edit(embeds=msg.embeds)
                        break
                else:
                    await interaction.response.send_message("Catégorie non trouvée.", ephemeral=True)
                    return

                for existing_tool in self.tools:
                    if existing_tool['category'].lower() == category.lower():
                        existing_tool['fields'] = [field for field in existing_tool['fields'] if field['tool'].lower() != tool.lower()]
                        if not existing_tool['fields']:
                            self.tools.remove(existing_tool)
                        break

                self.save_tools()

                await interaction.response.send_message(f"Outil {tool} dans la catégorie {category} supprimé.", ephemeral=True)
            else:
                await interaction.response.send_message("Aucun message de tool trouvé.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Tools(bot))
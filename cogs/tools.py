from discord.ext import commands
from discord import Interaction, app_commands, Embed

from utils import ConfigManager
from db.database import SessionLocal
from db.models import Tool
from discord import ui, ButtonStyle
from datetime import datetime


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

        match option.name:
            case "add":
                with SessionLocal() as session:
                    # Determine next index for this category
                    existing = (
                        session.query(Tool)
                        .filter(Tool.category.ilike(category))
                        .order_by(Tool.index.asc())
                        .all()
                    )
                    next_index = existing[-1].index + 1 if existing else 0
                    new_tool = Tool(category=category, index=next_index, tool=tool, description=description)
                    session.add(new_tool)
                    session.commit()

                    # Rebuild category list for embed update
                    fields = [{"tool": t.tool, "description": t.description or ''} for t in (
                        session.query(Tool)
                        .filter(Tool.category.ilike(category))
                        .order_by(Tool.index.asc())
                        .all()
                    )]

                update_embed(msg.embeds, category, fields)
                msg.embeds[-1].set_footer(text=f"Last update by {interaction.user.display_name} at {formatted_time}", icon_url=interaction.user.avatar.url)
                await msg.edit(embeds=msg.embeds)
                await interaction.response.send_message(f"Outil {tool} créé dans la catégorie {category}", ephemeral=True)
                
            case "edit" | "remove":
                with SessionLocal() as session:
                    items = (
                        session.query(Tool)
                        .filter(Tool.category.ilike(category))
                        .order_by(Tool.index.asc())
                        .all()
                    )
                    if not items:
                        await interaction.response.send_message("Catégorie non trouvée.", ephemeral=True)
                        return
                    pos = index - 1
                    if pos < 0 or pos >= len(items):
                        await interaction.response.send_message("Index non trouvé.", ephemeral=True)
                        return
                    target = items[pos]
                    original_name = target.tool
                    if option.name == "edit":
                        if tool is not None:
                            target.tool = tool
                        if description:
                            target.description = description
                        session.commit()
                    else:
                        session.delete(target)
                        session.flush()
                        # Reindex remaining tools for the category to keep order contiguous
                        remaining = (
                            session.query(Tool)
                            .filter(Tool.category.ilike(category))
                            .order_by(Tool.index.asc())
                            .all()
                        )
                        for idx, row in enumerate(remaining):
                            row.index = idx
                        session.commit()

                    # Build fields for embed update
                    fields = [{"tool": t.tool, "description": t.description or ''} for t in (
                        session.query(Tool)
                        .filter(Tool.category.ilike(category))
                        .order_by(Tool.index.asc())
                        .all()
                    )]

                if fields:
                    update_embed(msg.embeds, category, fields)
                else:
                    for embed in msg.embeds:
                        for field_index, field in enumerate(embed.fields):
                            if field.name == f'__{category.upper()}__':
                                embed.remove_field(field_index)
                                break
                msg.embeds[-1].set_footer(text=f"Last update by {interaction.user.display_name} at {formatted_time}", icon_url=interaction.user.avatar.url)
                await msg.edit(embeds=msg.embeds)
                await interaction.response.send_message(f"Outil {original_name} dans la catégorie {category} {option.value}.", ephemeral=True)


    @app_commands.command(description="Gérer les outils via une interface interactive.")
    @app_commands.check(check_if_user)
    async def manage_tools(self, interaction: Interaction):
        from ui.tools import ToolsView  # lazy import to avoid circular
        view = ToolsView()
        await interaction.response.send_message("Gestion des outils", view=view, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Tools(bot))

from __future__ import annotations

from typing import Optional

from discord import ui, Interaction, ButtonStyle, Embed

from db.database import SessionLocal
from db.models import Tool


def _build_category_fields(session, category: str):
    rows = (
        session.query(Tool)
        .filter(Tool.category.ilike(category))
        .order_by(Tool.index.asc())
        .all()
    )
    return [{"tool": r.tool, "description": r.description or ''} for r in rows]


class ToolModal(ui.Modal, title="Ajouter / Modifier un outil"):
    def __init__(self, *, category: str, index: Optional[int] = None):
        super().__init__()
        self.category = category
        self.index = index
        self.tool = ui.TextInput(label="Nom", placeholder="Nom de l'outil", min_length=1, max_length=255)
        self.description = ui.TextInput(label="Description", style=ui.TextStyle.long, required=False, max_length=1000)
        self.add_item(self.tool)
        self.add_item(self.description)

    async def on_submit(self, interaction: Interaction):
        with SessionLocal() as session:
            if self.index is None:
                # create
                existing = (
                    session.query(Tool)
                    .filter(Tool.category.ilike(self.category))
                    .order_by(Tool.index.asc())
                    .all()
                )
                next_index = existing[-1].index + 1 if existing else 0
                row = Tool(category=self.category, index=next_index, tool=str(self.tool), description=str(self.description))
                session.add(row)
                session.commit()
            else:
                items = (
                    session.query(Tool)
                    .filter(Tool.category.ilike(self.category))
                    .order_by(Tool.index.asc())
                    .all()
                )
                if 0 <= self.index < len(items):
                    target = items[self.index]
                    target.tool = str(self.tool)
                    target.description = str(self.description)
                    session.commit()

        await interaction.response.edit_message(content=f"Outil enregistré dans {self.category}.", view=None)


class ToolsView(ui.View):
    def __init__(self, *, timeout: Optional[float] = 300):
        super().__init__(timeout=timeout)

        self.category = ui.TextInput(label="Catégorie", placeholder="Ex: Crypto", min_length=1, max_length=64)

    @ui.button(label="Ajouter", style=ButtonStyle.success)
    async def add_button(self, interaction: Interaction, _: ui.Button):
        await interaction.response.send_modal(ToolModal(category=self.category.value if hasattr(self.category, 'value') else ""))

    @ui.button(label="Modifier (index)", style=ButtonStyle.primary)
    async def edit_button(self, interaction: Interaction, _: ui.Button):
        class IndexModal(ui.Modal, title="Modifier un outil"):
            index = ui.TextInput(label="Index (1..n)")
            async def on_submit(self, sub_interaction: Interaction):
                try:
                    idx = int(str(self.index)) - 1
                except Exception:
                    await sub_interaction.response.send_message("Index invalide.", ephemeral=True)
                    return
                await sub_interaction.response.send_modal(ToolModal(category=view.category.value, index=idx))

        view = self
        await interaction.response.send_modal(IndexModal())

    @ui.button(label="Supprimer (index)", style=ButtonStyle.danger)
    async def remove_button(self, interaction: Interaction, _: ui.Button):
        class RemoveModal(ui.Modal, title="Supprimer un outil"):
            index = ui.TextInput(label="Index (1..n)")
            async def on_submit(self, sub_interaction: Interaction):
                try:
                    idx = int(str(self.index)) - 1
                except Exception:
                    await sub_interaction.response.send_message("Index invalide.", ephemeral=True)
                    return
                with SessionLocal() as session:
                    items = (
                        session.query(Tool)
                        .filter(Tool.category.ilike(view.category.value))
                        .order_by(Tool.index.asc())
                        .all()
                    )
                    if 0 <= idx < len(items):
                        session.delete(items[idx])
                        session.flush()
                        remaining = (
                            session.query(Tool)
                            .filter(Tool.category.ilike(view.category.value))
                            .order_by(Tool.index.asc())
                            .all()
                        )
                        for i, row in enumerate(remaining):
                            row.index = i
                        session.commit()
                        await sub_interaction.response.edit_message(content=f"Outil supprimé de {view.category.value}.", view=None)
                    else:
                        await sub_interaction.response.send_message("Index non trouvé.", ephemeral=True)

        view = self
        await interaction.response.send_modal(RemoveModal())



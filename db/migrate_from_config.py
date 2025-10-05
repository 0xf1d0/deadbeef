from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from .database import SessionLocal, init_db
from .models import User, Tool, CalendarEvent


def _parse_dt(value: str) -> datetime | None:
    if not value:
        return None
    try:
        # ISO8601 from config.json
        return datetime.fromisoformat(value)
    except Exception:
        try:
            # calendar uses "%Y-%m-%d %H:%M:%S"
            return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
        except Exception:
            return None


def migrate(config_path: str = "config.json") -> None:
    cfg_file = Path(config_path)
    if not cfg_file.exists():
        print(f"Config file not found: {config_path}")
        return

    data = json.loads(cfg_file.read_text(encoding="utf-8"))

    init_db()
    with SessionLocal() as session:
        _migrate_users(session, data.get("users", []))
        _migrate_tools(session, data.get("tools", []))
        _migrate_calendar(session, data.get("reminders", []))
        session.commit()
    print("Migration completed.")


def _migrate_users(session: Session, users: list[dict]) -> None:
    for u in users:
        discord_id = u.get("id")
        if discord_id is None:
            # For pre-auth emails that do not yet have a Discord id, skip
            continue
        user = session.get(User, discord_id)
        if not user:
            user = User(id=discord_id)
            session.add(user)

        user.email = u.get("email")
        user.studentId = u.get("studentId")
        user.linkedin = u.get("linkedin")
        user.rootme = u.get("rootme")
        user.role = u.get("role")
        user.nick = u.get("nick")
        user.last_auth_request = _parse_dt(u.get("last_auth_request"))
        # courses is a list of integers in config.json
        if isinstance(u.get("courses"), list):
            user.courses = u.get("courses")


def _migrate_tools(session: Session, tools_payload: list[dict]) -> None:
    for category_block in tools_payload:
        category = category_block.get("category")
        fields = category_block.get("fields", [])
        for idx, field in enumerate(fields):
            tool_name = field.get("tool")
            description = field.get("description")

            existing = (
                session.query(Tool)
                .filter(Tool.category == category, Tool.index == idx)
                .one_or_none()
            )
            if not existing:
                existing = Tool(category=category, index=idx)
                session.add(existing)

            existing.tool = tool_name
            existing.description = description


def _migrate_calendar(session: Session, reminders: list[dict]) -> None:
    for reminder in reminders:
        course_name = reminder.get("name")
        for field in reminder.get("fields", []):
            event_name = field.get("name")
            event_date = _parse_dt(field.get("date"))
            description = field.get("description")
            modality = field.get("modality")

            # Upsert based on course+name+date
            existing = (
                session.query(CalendarEvent)
                .filter(
                    CalendarEvent.course_name == course_name,
                    CalendarEvent.name == event_name,
                    CalendarEvent.date == event_date,
                )
                .one_or_none()
            )
            if not existing:
                existing = CalendarEvent(
                    course_name=course_name,
                    name=event_name,
                    date=event_date if event_date else datetime.utcnow(),
                )
                session.add(existing)

            existing.description = description
            existing.modality = modality


if __name__ == "__main__":
    migrate()



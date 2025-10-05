from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Integer, String, DateTime, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.sqlite import JSON

from .database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)  # Discord user id
    email: Mapped[Optional[str]] = mapped_column(String(255), index=True, unique=True, nullable=True)
    studentId: Mapped[Optional[str]] = mapped_column(String(64), index=True, nullable=True)
    linkedin: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    rootme: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    role: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    nick: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    last_auth_request: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    courses: Mapped[Optional[list[int]]] = mapped_column(JSON, nullable=True)


class Tool(Base):
    __tablename__ = "tools"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category: Mapped[str] = mapped_column(String(64), index=True)
    index: Mapped[int] = mapped_column(Integer, default=0)  # position within category
    tool: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("category", "index", name="uq_tool_category_index"),
    )


class CalendarEvent(Base):
    __tablename__ = "calendar_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    course_name: Mapped[str] = mapped_column(String(128), index=True)
    name: Mapped[str] = mapped_column(String(255))
    date: Mapped[datetime] = mapped_column(DateTime, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    modality: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)


class NewsEntry(Base):
    __tablename__ = "news_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    url: Mapped[str] = mapped_column(String(1024), index=True)
    guid: Mapped[Optional[str]] = mapped_column(String(1024), index=True, nullable=True)
    title: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    source: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)



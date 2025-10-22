"""
Database models with improved normalization, type safety, and best practices.
"""
from sqlalchemy import (
    Column, Integer, String, Text, ForeignKey, BigInteger,
    DateTime, Boolean, Index, UniqueConstraint, Enum as SQLEnum
)
from sqlalchemy.orm import relationship, declarative_base, Mapped
from sqlalchemy.sql import func
from datetime import datetime
from typing import List, Optional

from .constants import UserType, AssignmentStatus, SuggestionStatus, GradeLevel, FormationType

Base = declarative_base()


# ============================================================================
# Mixins for common functionality
# ============================================================================

class TimestampMixin:
    """Mixin to add created_at and updated_at timestamps."""
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


# ============================================================================
# Cybertools System Models
# ============================================================================

class Category(Base, TimestampMixin):
    """Category model for organizing cybersecurity tools."""
    __tablename__ = 'categories'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # Relationships
    tools: Mapped[List["Tool"]] = relationship(
        'Tool',
        back_populates='category',
        cascade='all, delete-orphan',
        lazy='selectin'
    )
    
    def __repr__(self) -> str:
        return f"<Category(id={self.id}, name='{self.name}')>"


class Tool(Base, TimestampMixin):
    """Tool model for storing cybersecurity tool information."""
    __tablename__ = 'tools'
    __table_args__ = (
        Index('ix_tools_category_name', 'category_id', 'name'),
    )
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=False)
    url = Column(String(500), nullable=False)
    category_id = Column(Integer, ForeignKey('categories.id', ondelete='CASCADE'), nullable=False)
    
    # Relationships
    category: Mapped["Category"] = relationship('Category', back_populates='tools')
    
    def __repr__(self) -> str:
        return f"<Tool(id={self.id}, name='{self.name}')>"


class ToolSuggestion(Base, TimestampMixin):
    """ToolSuggestion model for user-submitted tool suggestions."""
    __tablename__ = 'tool_suggestions'
    __table_args__ = (
        Index('ix_tool_suggestions_status', 'status'),
        Index('ix_tool_suggestions_suggester', 'suggester_id'),
    )
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    tool_name = Column(String(200), nullable=False)
    tool_description = Column(Text, nullable=False)
    tool_url = Column(String(500), nullable=False)
    category_suggestion = Column(String(100), nullable=False)
    suggester_id = Column(BigInteger, nullable=False, index=True)
    status = Column(
        SQLEnum(SuggestionStatus),
        default=SuggestionStatus.PENDING,
        nullable=False,
        index=True
    )
    
    def __repr__(self) -> str:
        return f"<ToolSuggestion(id={self.id}, name='{self.tool_name}', status='{self.status.value}')>"


# ============================================================================
# Homework To-Do System Models
# ============================================================================

class GradeChannelConfig(Base, TimestampMixin):
    """Configuration model mapping Discord channels to grade levels."""
    __tablename__ = 'grade_channels'
    
    channel_id = Column(BigInteger, primary_key=True)
    grade_level = Column(
        SQLEnum(GradeLevel),
        unique=True,
        nullable=False,
        index=True
    )
    message_id = Column(BigInteger, nullable=True)
    content_hash = Column(String, nullable=True)  # Track content changes to avoid unnecessary updates
    
    # Relationships
    courses: Mapped[List["Course"]] = relationship(
        'Course',
        back_populates='grade_channel',
        cascade='all, delete-orphan',
        lazy='selectin'
    )
    
    def __repr__(self) -> str:
        return f"<GradeChannelConfig(channel_id={self.channel_id}, grade_level='{self.grade_level.value}')>"


class Course(Base, TimestampMixin):
    """Course model for academic courses."""
    __tablename__ = 'courses'
    __table_args__ = (
        UniqueConstraint('channel_id', 'name', name='uq_course_per_channel'),
        Index('ix_courses_channel', 'channel_id'),
        Index('ix_courses_name', 'name'),
    )
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    channel_id = Column(
        BigInteger,
        ForeignKey('grade_channels.channel_id', ondelete='CASCADE'),
        nullable=False
    )  # Homework to-do channel
    course_channel_id = Column(BigInteger, nullable=False)  # Actual course channel (for permissions)
    
    # Relationships
    grade_channel: Mapped["GradeChannelConfig"] = relationship('GradeChannelConfig', back_populates='courses')
    assignments: Mapped[List["Assignment"]] = relationship(
        'Assignment',
        back_populates='course',
        cascade='all, delete-orphan',
        lazy='selectin'
    )
    
    def __repr__(self) -> str:
        return f"<Course(id={self.id}, name='{self.name}')>"


class Assignment(Base, TimestampMixin):
    """Assignment model for homework, projects, and exams."""
    __tablename__ = 'assignments'
    __table_args__ = (
        Index('ix_assignments_course_status', 'course_id', 'status'),
        Index('ix_assignments_due_date', 'due_date'),
        Index('ix_assignments_status', 'status'),
    )
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)
    due_date = Column(DateTime(timezone=True), nullable=False, index=True)
    modality = Column(String(100), nullable=True)
    status = Column(
        SQLEnum(AssignmentStatus),
        default=AssignmentStatus.ACTIVE,
        nullable=False,
        index=True
    )
    course_id = Column(Integer, ForeignKey('courses.id', ondelete='CASCADE'), nullable=False)
    
    # Relationships
    course: Mapped["Course"] = relationship('Course', back_populates='assignments')
    
    def __repr__(self) -> str:
        return f"<Assignment(id={self.id}, title='{self.title}', status='{self.status.value}')>"
    
    @property
    def is_overdue(self) -> bool:
        """Check if assignment is overdue."""
        return datetime.now() > self.due_date


# ============================================================================
# Schedule System Models
# ============================================================================

class ScheduleChannelConfig(Base, TimestampMixin):
    """Configuration model for schedule channels."""
    __tablename__ = 'schedule_channels'
    
    channel_id = Column(BigInteger, primary_key=True)
    grade_level = Column(
        SQLEnum(GradeLevel),
        unique=True,
        nullable=False,
        index=True
    )
    spreadsheet_url = Column(String(500), nullable=False)
    gid = Column(String(50), nullable=False)
    message_id = Column(BigInteger, nullable=True)
    last_schedule_hash = Column(String(64), nullable=True)  # MD5 hash
    is_active = Column(Boolean, default=True, nullable=False)
    classes_per_day = Column(Integer, default=2, nullable=False)  # Number of time slots per day (2 for M1, 3 for M2)
    start_day_index = Column(Integer, default=0, nullable=False)  # 0=Monday, 1=Tuesday, etc.
    end_day_index = Column(Integer, default=1, nullable=False)  # Inclusive end day
    
    def __repr__(self) -> str:
        return f"<ScheduleChannelConfig(channel_id={self.channel_id}, grade_level='{self.grade_level.value}')>"


# ============================================================================
# News System Models
# ============================================================================

class NewsChannel(Base, TimestampMixin):
    """Configuration model for news channels."""
    __tablename__ = 'news_channels'
    
    channel_id = Column(BigInteger, primary_key=True)
    name = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    feeds: Mapped[List["NewsFeed"]] = relationship(
        'NewsFeed',
        back_populates='channel',
        cascade='all, delete-orphan',
        lazy='selectin'
    )
    
    def __repr__(self) -> str:
        return f"<NewsChannel(channel_id={self.channel_id}, name='{self.name}')>"


class NewsFeed(Base, TimestampMixin):
    """RSS/Atom feed configuration."""
    __tablename__ = 'news_feeds'
    __table_args__ = (
        UniqueConstraint('channel_id', 'url', name='uq_feed_per_channel'),
        Index('ix_news_feeds_channel_active', 'channel_id', 'is_active'),
    )
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    channel_id = Column(
        BigInteger,
        ForeignKey('news_channels.channel_id', ondelete='CASCADE'),
        nullable=False
    )
    name = Column(String(200), nullable=False)
    url = Column(String(500), nullable=False)
    color = Column(String(7), nullable=True)  # Hex color (e.g., "#FF0000")
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    channel: Mapped["NewsChannel"] = relationship('NewsChannel', back_populates='feeds')
    sent_entries: Mapped[List["SentNewsEntry"]] = relationship(
        'SentNewsEntry',
        back_populates='feed',
        cascade='all, delete-orphan',
        lazy='selectin'
    )
    
    def __repr__(self) -> str:
        return f"<NewsFeed(id={self.id}, name='{self.name}')>"


class SentNewsEntry(Base):
    """Track sent news entries to prevent duplicates."""
    __tablename__ = 'sent_news_entries'
    __table_args__ = (
        UniqueConstraint('feed_id', 'entry_id', name='uq_feed_entry'),
        Index('ix_sent_entries_feed', 'feed_id'),
        Index('ix_sent_entries_sent_at', 'sent_at'),
    )
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    feed_id = Column(Integer, ForeignKey('news_feeds.id', ondelete='CASCADE'), nullable=False)
    entry_id = Column(String(500), nullable=False)
    sent_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    feed: Mapped["NewsFeed"] = relationship('NewsFeed', back_populates='sent_entries')
    
    def __repr__(self) -> str:
        return f"<SentNewsEntry(feed_id={self.feed_id}, entry_id='{self.entry_id[:50]}...')>"


# ============================================================================
# Authentication System Models
# ============================================================================

class AuthenticatedUser(Base, TimestampMixin):
    """Store authenticated users (students and professionals)."""
    __tablename__ = 'authenticated_users'
    __table_args__ = (
        Index('ix_auth_users_email', 'email'),
        Index('ix_auth_users_type', 'user_type'),
        Index('ix_auth_users_student_id', 'student_id'),
    )
    
    user_id = Column(BigInteger, primary_key=True)
    email = Column(String(200), nullable=False, index=True)
    user_type = Column(SQLEnum(UserType), nullable=False)
    
    # Student-specific fields
    student_id = Column(String(20), nullable=True, index=True)
    grade_level = Column(SQLEnum(GradeLevel), nullable=True)
    formation_type = Column(SQLEnum(FormationType), nullable=True)
    
    # Optional profile links
    rootme_id = Column(String(10), nullable=True)
    linkedin_url = Column(String(300), nullable=True)
    
    # Timestamps (authenticated_at uses custom name instead of created_at)
    authenticated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    ctf_profile: Mapped[Optional["PlayerProfile"]] = relationship('PlayerProfile', back_populates='user', uselist=False)
    rootme_cache: Mapped[Optional["RootMeCache"]] = relationship('RootMeCache', back_populates='user', uselist=False)
    
    def __repr__(self) -> str:
        return f"<AuthenticatedUser(user_id={self.user_id}, type='{self.user_type.value}')>"


class RootMeCache(Base, TimestampMixin):
    """Cache for RootMe user statistics to reduce API calls."""
    __tablename__ = 'rootme_cache'
    __table_args__ = (
        Index('ix_rootme_cache_user_id', 'user_id'),
        Index('ix_rootme_cache_rootme_id', 'rootme_id'),
        Index('ix_rootme_cache_last_updated', 'last_updated'),
    )
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey('authenticated_users.user_id', ondelete='CASCADE'), nullable=False, unique=True)
    rootme_id = Column(String(10), nullable=False, index=True)
    
    # Cached RootMe data
    pseudo = Column(String(100), nullable=False)
    score = Column(Integer, nullable=False, default=0)
    position = Column(Integer, nullable=True)
    rank = Column(String(50), nullable=True)
    challenge_count = Column(Integer, nullable=False, default=0)
    
    # Cache metadata
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    cache_duration_hours = Column(Integer, nullable=False, default=6)  # Default 6 hours cache
    
    # Relationships
    user: Mapped["AuthenticatedUser"] = relationship('AuthenticatedUser', back_populates='rootme_cache')
    
    @property
    def is_expired(self) -> bool:
        """Check if cache is expired based on cache_duration_hours."""
        from datetime import datetime, timedelta
        return datetime.now() - self.last_updated > timedelta(hours=self.cache_duration_hours)
    
    def __repr__(self) -> str:
        return f"<RootMeCache(user_id={self.user_id}, rootme_id='{self.rootme_id}', score={self.score})>"


class Professional(Base, TimestampMixin):
    """Pre-registered professionals (teachers) with course access."""
    __tablename__ = 'professionals'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(200), unique=True, nullable=False, index=True)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    
    # Relationships
    course_channels: Mapped[List["ProfessionalCourseChannel"]] = relationship(
        'ProfessionalCourseChannel',
        back_populates='professional',
        cascade='all, delete-orphan',
        lazy='selectin'
    )
    
    @property
    def full_name(self) -> str:
        """Get full name."""
        parts = [self.first_name, self.last_name]
        return " ".join(p for p in parts if p) or "Unknown"
    
    def __repr__(self) -> str:
        return f"<Professional(email='{self.email}', name='{self.full_name}')>"


class ProfessionalCourseChannel(Base, TimestampMixin):
    """Mapping between professionals and Discord course channels."""
    __tablename__ = 'professional_course_channels'
    __table_args__ = (
        UniqueConstraint('professional_id', 'channel_id', name='uq_pro_channel'),
        Index('ix_pro_channels_professional', 'professional_id'),
    )
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    professional_id = Column(
        Integer,
        ForeignKey('professionals.id', ondelete='CASCADE'),
        nullable=False
    )
    channel_id = Column(BigInteger, nullable=False)
    channel_name = Column(String(100), nullable=True)
    
    # Relationships
    professional: Mapped["Professional"] = relationship('Professional', back_populates='course_channels')
    
    def __repr__(self) -> str:
        return f"<ProfessionalCourseChannel(pro_id={self.professional_id}, channel_id={self.channel_id})>"


class PendingAuth(Base):
    """Temporary authentication requests with tokens."""
    __tablename__ = 'pending_auths'
    __table_args__ = (
        Index('ix_pending_auth_user_expires', 'user_id', 'expires_at'),
        Index('ix_pending_auth_expires', 'expires_at'),
    )
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    email = Column(String(200), nullable=False)
    token = Column(String(500), nullable=False)
    user_type = Column(SQLEnum(UserType), nullable=False)
    
    # Student-specific data
    student_id = Column(String(20), nullable=True)
    grade_level = Column(SQLEnum(GradeLevel), nullable=True)
    formation_type = Column(SQLEnum(FormationType), nullable=True)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    
    # Professional-specific data
    pro_id = Column(Integer, ForeignKey('professionals.id', ondelete='CASCADE'), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    
    @property
    def is_expired(self) -> bool:
        """Check if the authentication request has expired."""
        return datetime.now() > self.expires_at
    
    def __repr__(self) -> str:
        return f"<PendingAuth(user_id={self.user_id}, type='{self.user_type.value}')>"


# ============================================================================
# CTF Team Management System Models
# ============================================================================

class PlayerProfile(Base, TimestampMixin):
    """CTF player profile for authenticated users."""
    __tablename__ = 'ctf_player_profiles'
    __table_args__ = (
        Index('ix_ctf_players_team', 'team_id'),
        Index('ix_ctf_players_status', 'status'),
    )
    
    user_id = Column(BigInteger, ForeignKey('authenticated_users.user_id', ondelete='CASCADE'), primary_key=True)
    team_id = Column(Integer, ForeignKey('ctf_teams.id', ondelete='SET NULL'), nullable=True)
    status = Column(String(50), default='Idle', nullable=False)  # 'Idle', 'Looking for Team'
    
    # Relationships
    user: Mapped["AuthenticatedUser"] = relationship('AuthenticatedUser', back_populates='ctf_profile')
    team: Mapped["Team"] = relationship('Team', back_populates='members', foreign_keys=[team_id])
    owned_team: Mapped["Team"] = relationship('Team', back_populates='owner', foreign_keys='Team.owner_id', uselist=False)
    sent_invites: Mapped[List["TeamInvite"]] = relationship(
        'TeamInvite',
        foreign_keys='TeamInvite.invitee_id',
        back_populates='invitee',
        cascade='all, delete-orphan'
    )
    applications: Mapped[List["TeamApplication"]] = relationship(
        'TeamApplication',
        back_populates='applicant',
        cascade='all, delete-orphan'
    )
    
    @property
    def discord_id(self) -> int:
        """Get Discord ID from associated user."""
        return self.user.user_id
    
    @property
    def rootme_username(self) -> Optional[str]:
        """Get Root-Me username from associated user's rootme_id."""
        return self.user.rootme_id
    
    def __repr__(self) -> str:
        return f"<PlayerProfile(user_id={self.user_id}, team_id={self.team_id}, status='{self.status}')>"


class Team(Base, TimestampMixin):
    """CTF team with associated Discord channel and members."""
    __tablename__ = 'ctf_teams'
    __table_args__ = (
        Index('ix_ctf_teams_owner', 'owner_id'),
        Index('ix_ctf_teams_recruiting', 'is_recruiting'),
    )
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    owner_id = Column(BigInteger, ForeignKey('ctf_player_profiles.user_id', ondelete='CASCADE'), nullable=False)
    channel_id = Column(BigInteger, unique=True, nullable=False)
    inbox_thread_id = Column(BigInteger, unique=True, nullable=True)
    is_recruiting = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    owner: Mapped["PlayerProfile"] = relationship('PlayerProfile', foreign_keys=[owner_id], back_populates='owned_team')
    members: Mapped[List["PlayerProfile"]] = relationship(
        'PlayerProfile',
        foreign_keys='PlayerProfile.team_id',
        back_populates='team',
        lazy='selectin'
    )
    invites: Mapped[List["TeamInvite"]] = relationship(
        'TeamInvite',
        back_populates='team',
        cascade='all, delete-orphan',
        lazy='selectin'
    )
    applications: Mapped[List["TeamApplication"]] = relationship(
        'TeamApplication',
        back_populates='team',
        cascade='all, delete-orphan',
        lazy='selectin'
    )
    
    def __repr__(self) -> str:
        return f"<Team(id={self.id}, name='{self.name}', owner_id={self.owner_id})>"


class TeamInvite(Base, TimestampMixin):
    """Track pending invitations from teams to potential members."""
    __tablename__ = 'ctf_team_invites'
    __table_args__ = (
        UniqueConstraint('team_id', 'invitee_id', name='uq_team_invitee'),
        Index('ix_ctf_invites_team_status', 'team_id', 'status'),
        Index('ix_ctf_invites_invitee_status', 'invitee_id', 'status'),
    )
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    team_id = Column(Integer, ForeignKey('ctf_teams.id', ondelete='CASCADE'), nullable=False)
    invitee_id = Column(BigInteger, ForeignKey('ctf_player_profiles.user_id', ondelete='CASCADE'), nullable=False)
    status = Column(String(20), default='pending', nullable=False)  # 'pending', 'accepted', 'declined'
    
    # Relationships
    team: Mapped["Team"] = relationship('Team', back_populates='invites')
    invitee: Mapped["PlayerProfile"] = relationship('PlayerProfile', foreign_keys=[invitee_id], back_populates='sent_invites')
    
    def __repr__(self) -> str:
        return f"<TeamInvite(id={self.id}, team_id={self.team_id}, invitee_id={self.invitee_id}, status='{self.status}')>"


class TeamApplication(Base, TimestampMixin):
    """Track pending applications from users wishing to join a team."""
    __tablename__ = 'ctf_team_applications'
    __table_args__ = (
        UniqueConstraint('team_id', 'applicant_id', name='uq_team_applicant'),
        Index('ix_ctf_apps_team_status', 'team_id', 'status'),
        Index('ix_ctf_apps_applicant_status', 'applicant_id', 'status'),
    )
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    team_id = Column(Integer, ForeignKey('ctf_teams.id', ondelete='CASCADE'), nullable=False)
    applicant_id = Column(BigInteger, ForeignKey('ctf_player_profiles.user_id', ondelete='CASCADE'), nullable=False)
    reason = Column(Text, nullable=False)
    status = Column(String(20), default='pending', nullable=False)  # 'pending', 'approved', 'denied'
    
    # Relationships
    team: Mapped["Team"] = relationship('Team', back_populates='applications')
    applicant: Mapped["PlayerProfile"] = relationship('PlayerProfile', back_populates='applications')
    
    def __repr__(self) -> str:
        return f"<TeamApplication(id={self.id}, team_id={self.team_id}, applicant_id={self.applicant_id}, status='{self.status}')>"


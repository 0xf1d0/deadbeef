from sqlalchemy import Column, Integer, String, Text, ForeignKey, BigInteger, DateTime
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime

Base = declarative_base()


# ============================================================================
# Cybertools System Models
# ============================================================================

class Category(Base):
    """Category model for organizing cybersecurity tools."""
    __tablename__ = 'categories'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(Text)
    
    # Relationship to tools
    tools = relationship('Tool', back_populates='category', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f"<Category(id={self.id}, name='{self.name}')>"


class Tool(Base):
    """Tool model for storing cybersecurity tool information."""
    __tablename__ = 'tools'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(Text, nullable=False)
    url = Column(String, nullable=False)
    category_id = Column(Integer, ForeignKey('categories.id'), nullable=False)
    
    # Relationship to category
    category = relationship('Category', back_populates='tools')
    
    def __repr__(self):
        return f"<Tool(id={self.id}, name='{self.name}', category_id={self.category_id})>"


class ToolSuggestion(Base):
    """ToolSuggestion model for user-submitted tool suggestions."""
    __tablename__ = 'tool_suggestions'
    
    id = Column(Integer, primary_key=True)
    tool_name = Column(String, nullable=False)
    tool_description = Column(Text, nullable=False)
    tool_url = Column(String, nullable=False)
    category_suggestion = Column(String, nullable=False)
    suggester_id = Column(BigInteger, nullable=False)
    status = Column(String, default='pending', nullable=False)  # 'pending', 'approved', 'denied'
    
    def __repr__(self):
        return f"<ToolSuggestion(id={self.id}, tool_name='{self.tool_name}', status='{self.status}')>"


# ============================================================================
# Homework To-Do System Models
# ============================================================================

class GradeChannelConfig(Base):
    """Configuration model mapping Discord channels to grade levels."""
    __tablename__ = 'grade_channels'
    
    channel_id = Column(BigInteger, primary_key=True)
    grade_level = Column(String, unique=True, nullable=False)
    message_id = Column(BigInteger, nullable=True)
    
    # Relationship to courses
    courses = relationship('Course', back_populates='grade_channel', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f"<GradeChannelConfig(channel_id={self.channel_id}, grade_level='{self.grade_level}')>"


class Course(Base):
    """Course model for academic courses."""
    __tablename__ = 'courses'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    channel_id = Column(BigInteger, ForeignKey('grade_channels.channel_id'), nullable=False)
    
    # Relationships
    grade_channel = relationship('GradeChannelConfig', back_populates='courses')
    assignments = relationship('Assignment', back_populates='course', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f"<Course(id={self.id}, name='{self.name}', channel_id={self.channel_id})>"


class Assignment(Base):
    """Assignment model for homework, projects, and exams."""
    __tablename__ = 'assignments'
    
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(Text)
    due_date = Column(DateTime, nullable=False)
    modality = Column(String)
    status = Column(String, default='active', nullable=False)  # 'active', 'completed', 'past_due'
    course_id = Column(Integer, ForeignKey('courses.id'), nullable=False)
    
    # Relationship to course
    course = relationship('Course', back_populates='assignments')
    
    def __repr__(self):
        return f"<Assignment(id={self.id}, title='{self.title}', status='{self.status}')>"


# ============================================================================
# Schedule System Models
# ============================================================================

class ScheduleChannelConfig(Base):
    """Configuration model for schedule channels."""
    __tablename__ = 'schedule_channels'
    
    channel_id = Column(BigInteger, primary_key=True)
    grade_level = Column(String, unique=True, nullable=False)  # M1, M2, etc.
    spreadsheet_url = Column(String, nullable=False)
    gid = Column(String, nullable=False)  # Google Sheets gid parameter
    message_id = Column(BigInteger, nullable=True)
    last_schedule_hash = Column(String, nullable=True)  # Hash of last schedule for change detection
    
    def __repr__(self):
        return f"<ScheduleChannelConfig(channel_id={self.channel_id}, grade_level='{self.grade_level}')>"


# ============================================================================
# News System Models
# ============================================================================

class NewsChannel(Base):
    """Configuration model for news channels."""
    __tablename__ = 'news_channels'
    
    channel_id = Column(BigInteger, primary_key=True)
    name = Column(String, nullable=False)  # Friendly name for the channel
    is_active = Column(String, default='true', nullable=False)  # 'true' or 'false'
    
    # Relationship to feeds
    feeds = relationship('NewsFeed', back_populates='channel', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f"<NewsChannel(channel_id={self.channel_id}, name='{self.name}')>"


class NewsFeed(Base):
    """RSS/Atom feed configuration."""
    __tablename__ = 'news_feeds'
    
    id = Column(Integer, primary_key=True)
    channel_id = Column(BigInteger, ForeignKey('news_channels.channel_id'), nullable=False)
    name = Column(String, nullable=False)  # Display name (e.g., "CERT-FR")
    url = Column(String, nullable=False)  # RSS feed URL
    color = Column(String, nullable=True)  # Hex color for embeds (e.g., "#FF0000")
    is_active = Column(String, default='true', nullable=False)  # 'true' or 'false'
    
    # Relationship
    channel = relationship('NewsChannel', back_populates='feeds')
    sent_entries = relationship('SentNewsEntry', back_populates='feed', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f"<NewsFeed(id={self.id}, name='{self.name}', channel_id={self.channel_id})>"


class SentNewsEntry(Base):
    """Track sent news entries to prevent duplicates."""
    __tablename__ = 'sent_news_entries'
    
    id = Column(Integer, primary_key=True)
    feed_id = Column(Integer, ForeignKey('news_feeds.id'), nullable=False)
    entry_id = Column(String, nullable=False)  # RSS entry ID/GUID
    sent_at = Column(DateTime, nullable=False)  # When it was sent
    
    # Relationship
    feed = relationship('NewsFeed', back_populates='sent_entries')
    
    def __repr__(self):
        return f"<SentNewsEntry(feed_id={self.feed_id}, entry_id='{self.entry_id}')>"


# ============================================================================
# Authentication System Models
# ============================================================================

class AuthenticatedUser(Base):
    """Store authenticated users (students and professionals)."""
    __tablename__ = 'authenticated_users'
    
    user_id = Column(BigInteger, primary_key=True)  # Discord user ID
    email = Column(String, nullable=False)
    user_type = Column(String, nullable=False)  # 'student' or 'professional'
    
    # Student-specific fields
    student_id = Column(String, nullable=True)  # Student number (only for students)
    grade_level = Column(String, nullable=True)  # 'M1' or 'M2' (for students)
    formation_type = Column(String, nullable=True)  # 'FI' or 'FA' (for students)
    
    # Optional profile links
    rootme_id = Column(String, nullable=True)  # Root-Me user ID
    linkedin_url = Column(String, nullable=True)  # LinkedIn profile URL
    
    # Timestamps
    authenticated_at = Column(DateTime, nullable=False, default=datetime.now)
    
    def __repr__(self):
        return f"<AuthenticatedUser(user_id={self.user_id}, type='{self.user_type}')>"


class Professional(Base):
    """Pre-registered professionals (teachers) with course access."""
    __tablename__ = 'professionals'
    
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    
    # Relationship to course channels
    course_channels = relationship('ProfessionalCourseChannel', back_populates='professional', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f"<Professional(email='{self.email}', name='{self.first_name} {self.last_name}')>"


class ProfessionalCourseChannel(Base):
    """Mapping between professionals and Discord course channels."""
    __tablename__ = 'professional_course_channels'
    
    id = Column(Integer, primary_key=True)
    professional_id = Column(Integer, ForeignKey('professionals.id'), nullable=False)
    channel_id = Column(BigInteger, nullable=False)  # Discord channel ID
    channel_name = Column(String, nullable=True)  # Friendly name for reference
    
    # Relationship
    professional = relationship('Professional', back_populates='course_channels')
    
    def __repr__(self):
        return f"<ProfessionalCourseChannel(pro_id={self.professional_id}, channel_id={self.channel_id})>"


class PendingAuth(Base):
    """Temporary authentication requests with tokens."""
    __tablename__ = 'pending_auths'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, nullable=False)  # Discord user ID
    email = Column(String, nullable=False)
    token = Column(String, nullable=False)  # JWT token
    user_type = Column(String, nullable=False)  # 'student' or 'professional'
    
    # Student-specific data (for pending student auths)
    student_id = Column(String, nullable=True)
    grade_level = Column(String, nullable=True)  # 'M1' or 'M2'
    formation_type = Column(String, nullable=True)  # 'FI' or 'FA'
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    
    # Professional-specific data (for pending pro auths)
    pro_id = Column(Integer, ForeignKey('professionals.id'), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    expires_at = Column(DateTime, nullable=False)
    
    def __repr__(self):
        return f"<PendingAuth(user_id={self.user_id}, type='{self.user_type}')>"


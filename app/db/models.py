"""Database models for persistent storage."""
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime
import os

Base = declarative_base()


class SessionModel(Base):
    """Database model for conversation sessions."""
    __tablename__ = 'sessions'
    
    id = Column(Integer, primary_key=True)
    session_id = Column(String, unique=True, nullable=False, index=True)
    scam_detected = Column(Boolean, default=False)
    scam_type = Column(String, nullable=True)
    agent_type = Column(String, nullable=True)
    start_time = Column(DateTime, default=datetime.now)
    end_time = Column(DateTime, nullable=True)
    total_messages = Column(Integer, default=0)
    intelligence_count = Column(Integer, default=0)
    engagement_duration = Column(Integer, default=0)  # seconds
    success_score = Column(Float, default=0.0)  # RL reward
    is_complete = Column(Boolean, default=False)
    
    # Relationships
    messages = relationship("MessageModel", back_populates="session", cascade="all, delete-orphan")
    intelligence_items = relationship("IntelligenceModel", back_populates="session", cascade="all, delete-orphan")
    rl_data = relationship("RLTrainingDataModel", back_populates="session", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Session {self.session_id} - {self.scam_type}>"


class MessageModel(Base):
    """Database model for individual messages."""
    __tablename__ = 'messages'
    
    id = Column(Integer, primary_key=True)
    session_id = Column(String, ForeignKey('sessions.session_id'), nullable=False, index=True)
    sender = Column(String, nullable=False)  # 'scammer' or 'user'
    text = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.now)
    
    # Relationship
    session = relationship("SessionModel", back_populates="messages")
    
    def __repr__(self):
        return f"<Message from {self.sender}: {self.text[:30]}...>"


class IntelligenceModel(Base):
    """Database model for extracted intelligence."""
    __tablename__ = 'intelligence'
    
    id = Column(Integer, primary_key=True)
    session_id = Column(String, ForeignKey('sessions.session_id'), nullable=False, index=True)
    type = Column(String, nullable=False)  # 'upi', 'phone', 'url', 'bank_account', 'keyword'
    value = Column(String, nullable=False)
    extracted_at = Column(DateTime, default=datetime.now)
    
    # Relationship
    session = relationship("SessionModel", back_populates="intelligence_items")
    
    def __repr__(self):
        return f"<Intelligence {self.type}: {self.value}>"


class RLTrainingDataModel(Base):
    """Database model for reinforcement learning training data."""
    __tablename__ = 'rl_training_data'
    
    id = Column(Integer, primary_key=True)
    session_id = Column(String, ForeignKey('sessions.session_id'), nullable=False, index=True)
    turn_number = Column(Integer, nullable=False)
    state = Column(Text, nullable=False)  # JSON string
    action = Column(String, nullable=False)
    reward = Column(Float, nullable=False)
    next_state = Column(Text, nullable=True)  # JSON string
    created_at = Column(DateTime, default=datetime.now)
    
    # Relationship
    session = relationship("SessionModel", back_populates="rl_data")
    
    def __repr__(self):
        return f"<RLData turn {self.turn_number}: action={self.action}, reward={self.reward}>"


# Database setup
def get_database_url():
    """Get database URL from environment or use default."""
    db_path = os.getenv('DATABASE_PATH', 'honeypot.db')
    return f'sqlite:///{db_path}'


def init_database():
    """Initialize database and create tables."""
    engine = create_engine(get_database_url(), echo=False)
    Base.metadata.create_all(engine)
    return engine


def get_session_maker():
    """Get SQLAlchemy session maker."""
    engine = init_database()
    return sessionmaker(bind=engine)


# Global session maker
SessionLocal = get_session_maker()

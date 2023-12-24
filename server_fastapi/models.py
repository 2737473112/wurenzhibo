from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.sqlite import JSON

Base = declarative_base()

class User(Base):
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True)
    username = Column(String(20), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    speech_libraries = relationship('SpeechLibrary', backref='author', lazy='dynamic')
    qa_libraries = relationship('QALibrary', backref='author', lazy='dynamic')

class SpeechLibrary(Base):
    __tablename__ = 'speech_library'
    id = Column(Integer, primary_key=True)
    data = Column(JSON, nullable=False)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)

class QALibrary(Base):
    __tablename__ = 'qa_library'
    id = Column(Integer, primary_key=True)
    data = Column(JSON, nullable=False)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)

class UserStatus(Base):
    __tablename__ = 'user_status'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    is_live_streaming = Column(Boolean, default=False)
    is_danmaku_reply_enabled = Column(Boolean, default=False)
    voice = Column(String(255))
    speech_speed = Column(Float)
    broadcast_strategy = Column(String(255))
    ai_rewrite = Column(Boolean, default=False)
    is_broadcasting = Column(Boolean, default=False)
    current_audio_timestamp = Column(Float, default=0.0)
    audio_playback_status = Column(String(50))

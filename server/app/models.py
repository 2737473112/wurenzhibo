from . import db
#from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy import JSON

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    speech_libraries = db.relationship('SpeechLibrary', backref='author', lazy=True)
    qa_libraries = db.relationship('QALibrary', backref='author', lazy=True)

class SpeechLibrary(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(JSON, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class QALibrary(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(JSON, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class UserStatus(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    is_live_streaming = db.Column(db.Boolean, default=False)
    is_danmaku_reply_enabled = db.Column(db.Boolean, default=False)
    voice = db.Column(db.String(255))
    speech_speed = db.Column(db.Float)
    broadcast_strategy = db.Column(db.String(255))
    ai_rewrite = db.Column(db.Boolean, default=False)
    is_broadcasting = db.Column(db.Boolean, default=False)  # 是否开始直播
    current_audio_timestamp = db.Column(db.Float, default=0.0)  # 当前用户音频时间戳
    audio_playback_status = db.Column(db.String(50))  # 当前用户音频播放状态

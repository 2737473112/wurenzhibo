from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from .config import Config
from .ws import socketio, setup_websocket_events

from datetime import datetime, timedelta
from threading import Thread
import time



db = SQLAlchemy()
jwt = JWTManager()
migrate = Migrate()

def monitor_user_statuses(app):
    from .models import UserStatus
    with app.app_context():
        while True:
            now = datetime.utcnow()
            user_statuses = UserStatus.query.all()

            for status in user_statuses:
                if status.is_broadcasting:
                    if status.current_audio_timestamp is None:
                        #print(f"用户 {status.user_id} 的 current_audio_timestamp 为 None，跳过此用户")
                        continue

                    last_update_time = datetime.utcfromtimestamp(status.current_audio_timestamp)
                    time_diff = (now - last_update_time).total_seconds()

                    #print(f"正在检查用户 {status.user_id} 的状态，上次更新时间: {last_update_time}, 时间差: {time_diff}秒")

                    if time_diff > 60:
                        status.audio_playback_status = "用户音频可能已断开"
                        #print(f"用户 {status.user_id} 的状态已更改为 '用户音频可能已断开'")
                    else:
                        status.audio_playback_status = "正常直播"
                        #print(f"用户 {status.user_id} 的状态已确认为 '正常'")
                else:
                    # 如果用户不在直播，更新状态为未直播
                    status.audio_playback_status = "未直播"
                    #print(f"用户 {status.user_id} 的状态已更新为 '未直播'")

            db.session.commit()
            time.sleep(5)  # 每5秒检查一次





# def create_app():
#     app = Flask(__name__)
#     app.config.from_object(Config)

#     db.init_app(app)
#     migrate.init_app(app, db)
#     CORS(app)
#     jwt.init_app(app)

#     from .routes import main as main_blueprint
#     app.register_blueprint(main_blueprint)

#     socketio.init_app(app)
#     setup_websocket_events(app)

#     # # 启动用户状态监控线程
#     # thread = Thread(target=monitor_user_statuses, args=(app,))
#     # thread.daemon = True
#     # thread.start()

#     return app

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    migrate.init_app(app, db)
    CORS(app)
    jwt.init_app(app)

    from .routes import main as main_blueprint
    app.register_blueprint(main_blueprint)

    # # 启动用户状态监控线程
    # thread = Thread(target=monitor_user_statuses, args=(app,))
    # thread.daemon = True
    # thread.start()

    return app
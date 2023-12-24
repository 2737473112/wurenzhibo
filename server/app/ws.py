from flask_socketio import SocketIO, emit, join_room, leave_room, disconnect
from flask_jwt_extended import decode_token
import time
import os
import base64
# 初始化SocketIO，但不绑定app，在create_app中绑定
socketio = SocketIO(cors_allowed_origins="*")
    

def setup_websocket_events(app):
    from .models import User, UserStatus,SpeechLibrary,QALibrary
    from . import db
    from .services.live_service import LiveService  # 引入LiveService类
    from .services.danmu_service import DanmuService  # 引入DanmuService类
    
    # 全局字典来保存用户实例
    user_instances = {}    

    @socketio.on('connect')
    def handle_connect(auth):
        token = auth.get('token') if auth else None
        if not token:
            disconnect()
            return
        try:
            # 解码 JWT token 并提取用户 ID
            user_identity = decode_token(token)['sub']
            join_room(user_identity)
        except:
            disconnect()
            return

        # 使用用户 ID 查询数据库
        user = User.query.filter_by(id=user_identity).first()
        user_status = UserStatus.query.filter_by(user_id=user_identity).first()
        speech_libraries = SpeechLibrary.query.filter_by(user_id=user_identity).all()
        
        if user and user_status:
            #打印 UserStatus 的完整内容
            # 打印 UserStatus 的完整内容
            print(f"UserStatus: is_live_streaming={user_status.is_live_streaming}, "
                f"is_danmaku_reply_enabled={user_status.is_danmaku_reply_enabled}, "
                f"voice={user_status.voice}, speech_speed={user_status.speech_speed}, "
                f"broadcast_strategy={user_status.broadcast_strategy}, "
                f"ai_rewrite={user_status.ai_rewrite}, "
                f"is_broadcasting={user_status.is_broadcasting}, "
                f"current_audio_timestamp={user_status.current_audio_timestamp}, "
                f"audio_playback_status={user_status.audio_playback_status}")

            speech_library_data = speech_libraries[0].data if speech_libraries else None
            #print("现在正在使用的数据",speech_library_data)

            if user_identity not in user_instances:
                user_instances[user_identity] = LiveService(
                    user_id=user_identity,
                    voice=user_status.voice,
                    speech_speed=user_status.speech_speed,
                    broadcast_strategy=user_status.broadcast_strategy,
                    ai_rewrite=user_status.ai_rewrite,
                    speech_library=speech_library_data
                )
            else:
                # 直接更新已存在实例的属性
                live_service = user_instances[user_identity]
                live_service.voice = user_status.voice
                live_service.speech_speed = user_status.speech_speed
                live_service.broadcast_strategy = user_status.broadcast_strategy
                live_service.ai_rewrite = user_status.ai_rewrite
                live_service.speech_library = speech_library_data
        else:
            print(f"User ID {user_identity} not found or no status available.")
        
    @socketio.on('current_time')
    def handle_current_time(data):
        token = data.get('token') if data else None
        current_time = data.get('currentTime') if data else None
        if not token or current_time is None:
            print("无效的数据或未提供token")
            return
        try:
            # 解码 JWT token 并提取用户 ID
            user_identity = decode_token(token)['sub']
        except:
            print("Token解码失败")
            return
        # 查询数据库并更新 UserStatus
        user_status = UserStatus.query.filter_by(user_id=user_identity).first()
        if user_status:
            user_status.current_audio_timestamp = current_time
            db.session.commit()  # 提交更改到数据库
            #print(f"用户 {user_identity} 的音频播放时间戳已更新: {current_time} 秒")
        else:
            print(f"未找到用户 {user_identity} 的状态记录")


    @socketio.on('send_danmu')
    def handle_send_danmu(data):
        token = data.get('token')
        danmu_text = data.get('danmu_text')

        if not token:
            print("No token provided.")
            return
    
        try:
            # 解码 JWT token 并提取用户 ID
            user_id = decode_token(token)['sub']
        except Exception as e:
            print(f"Token decoding failed: {e}")
            return
        
        # 从数据库获取用户状态和弹幕库
        user_status = UserStatus.query.filter_by(user_id=user_id).first()
        qa_libraries = QALibrary.query.filter_by(user_id=user_id).all()
        
        
        if not user_status or not qa_libraries:
            print(f"User ID {user_id} not found or no QA library available.")
            return
        
       
        if True:
            # 初始化 DanmuService
            qa_library = qa_libraries[0].data if qa_libraries else None
            danmu_service = DanmuService(
                user_id=user_id,
                voice=user_status.voice,
                speech_speed=user_status.speech_speed,
                qa_library=qa_library  
            )
            
            audio_path=danmu_service.generate_danmu_audio(danmu_text)
            if audio_path:
                audio_full_path = os.path.join('/www/wwwroot/wurenzhibo/server', audio_path)
                # 读取音频文件内容
                try:
                    with open(audio_full_path, 'rb') as audio_file:
                        audio_data = audio_file.read()
                        # 发送音频二进制数据
                        socketio.emit('danmu_audio_response', {'audio_data': audio_data}, room=user_id)
                except Exception as e:
                    print(f"Error reading audio file {audio_full_path}: {e}")
                    
        else:
            print("Danmaku reply is not enabled for this user.")


    @socketio.on('check_audio_stream')
    def handle_check_audio_stream(data):
        token = data.get('token')
        current_stream_length = data.get('current_stream_length')
        if not token:
            print("No token provided.")
            return
        try:
            user_id = decode_token(token)['sub']
        except Exception as e:
            print(f"Token decoding failed: {e}")
            return
        # 从内存中获取用户的 live_service 实例
        live_service = user_instances.get(user_id)
        if not live_service:
            print(f"No live service instance found for User ID {user_id}")
            return
        if current_stream_length < 5:
            audio_path = live_service.generate_normal_audio()
            if audio_path:
                audio_full_path = os.path.join('/www/wwwroot/wurenzhibo/server', audio_path)
                try:
                    with open(audio_full_path, 'rb') as audio_file:
                        audio_data = audio_file.read()
                        encoded_audio = base64.b64encode(audio_data).decode('utf-8')
                        socketio.emit('danmu_audio_response', {'audio_data': encoded_audio}, room=user_id)
                except Exception as e:
                    print(f"Error reading audio file {audio_full_path}: {e}")
            else:
                print("No audio generated or audio generation failed.")
        elif current_stream_length >= 10:
            print("Stream length exceeds threshold, no audio generated.")

        # 重置音频处理标志
        live_service.is_live_streaming = False

    @socketio.on('disconnect')
    def handle_disconnect():
        print('链接断开')

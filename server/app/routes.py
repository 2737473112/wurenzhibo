from flask import Blueprint, request, jsonify, send_file, make_response, send_from_directory
from werkzeug.security import check_password_hash,generate_password_hash
from .models import User
from . import db
from flask_jwt_extended import create_access_token
from flask_jwt_extended import jwt_required, get_jwt_identity
from .services.live_service import LiveService  # 引入LiveService类
from .services.danmu_service import DanmuService  # 引入DanmuService类
from .services.service_factory import ServiceFactory  # 引入DanmuService类
from .models import User, SpeechLibrary,QALibrary,UserStatus
from flask import Flask, request, jsonify
from threading import Thread
import os
import io
from datetime import datetime
import traceback  # Import traceback module
from threading import Timer
from flask import render_template_string

import logging
import logging
from werkzeug.serving import WSGIRequestHandler
from threading import Timer
from datetime import datetime, timedelta
import base64
# 设置 Werkzeug 日志级别
WSGIRequestHandler.log = lambda self, type, message, *args: \
    logging.getLogger(type).log(logging.ERROR if type == 'error' else logging.NOTSET, message, *args)
main = Blueprint('main', __name__)

# 全局字典来存储 live_service 实例
live_services = {}
# 全局字典来存储 DanmuService 实例
danmu_services = {}

@main.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    print("收到登录请求，请求数据: ", data)

    if 'username' not in data or 'password' not in data:
        print("请求数据缺少用户名或密码字段")
        return jsonify({"message": "请求中缺少必要的用户名或密码字段"}), 400

    user = User.query.filter_by(username=data['username']).first()

    if user:
        print(f"找到用户: {user.username}, 正在验证密码...")
        if check_password_hash(user.password, data['password']):
            access_token = create_access_token(identity=user.id)
            print(f"用户 {user.username} 登录成功，生成的 JWT 令牌: {access_token}")
            return jsonify({"access_token": access_token}), 200
        else:
            print(f"用户 {user.username} 的密码验证失败")
    else:
        print(f"未找到用户名为 {data['username']} 的用户")

    return jsonify({"message": "用户名或密码错误"}), 401


@main.route('/register', methods=['POST'])
def register():
    data = request.get_json()

    # 检查用户名是否已存在
    existing_user = User.query.filter_by(username=data['username']).first()
    if existing_user:
        return jsonify({"message": "Username already exists"}), 400

    # 创建新用户并存储到数据库
    hashed_password = generate_password_hash(data['password'], method='pbkdf2:sha256')
    new_user = User(username=data['username'], password=hashed_password)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": "User successfully registered"}), 201


@main.route('/start_live', methods=['POST'])
@jwt_required()
def start_live():
    current_user_id = get_jwt_identity()
    data = request.get_json()
    print("接收到请求")
    # 检查必要的数据字段
    required_fields = ['voice', 'speechSpeed', 'broadcastStrategy', 'aiRewrite']
    if not all(field in data for field in required_fields):
        return jsonify({"message": "Missing required data fields"}), 400

    # 转换 ai_rewrite 从 '是'/'否' 字符串到布尔值
    ai_rewrite_bool = data['aiRewrite'] == '是'
    speech_libraries = SpeechLibrary.query.filter_by(user_id=current_user_id).all()
    speech_library = speech_libraries[0].data if speech_libraries else None
    
    try:
        user_status = UserStatus.query.filter_by(user_id=current_user_id).first()
        if not user_status:
            user_status = UserStatus(
                user_id=current_user_id,
                is_live_streaming=False,
                voice=data['voice'],
                speech_speed=data['speechSpeed'],
                broadcast_strategy=data['broadcastStrategy'],
                ai_rewrite=ai_rewrite_bool,
                is_broadcasting=True,  # 设置 is_broadcasting 为 True
                audio_playback_status="正常"
            )
            db.session.add(user_status)
        else:
            user_status.is_live_streaming = False  # 是否正在合成音频流，一开始要是false
            user_status.voice = data['voice']
            user_status.speech_speed = data['speechSpeed']
            user_status.broadcast_strategy = data['broadcastStrategy']
            user_status.ai_rewrite = ai_rewrite_bool
            user_status.is_broadcasting = True  # 更新 is_broadcasting 为 True
            user_status.audio_playback_status="正常"
        db.session.commit()
        print("更新数据完成,开始创建实例")
        # 创建或更新 live_service 实例
        live_services[current_user_id] = LiveService(
            user_id=current_user_id,
            voice=data['voice'],
            speech_speed=data['speechSpeed'],
            broadcast_strategy=data['broadcastStrategy'],
            ai_rewrite=ai_rewrite_bool,
            speech_library=speech_library  # 添加缺失的参数
        )

        qa_libraries = QALibrary.query.filter_by(user_id=current_user_id).all()
        qa_library = qa_libraries[0].data if qa_libraries else None
        danmu_services[current_user_id] = DanmuService(
            user_id=current_user_id,
            voice=data['voice'],
            speech_speed=data['speechSpeed'],
            qa_library=qa_library  # 假设 DanmuService 需要 qa_library 作为参数
        )

        print("创建直播实例和弹幕实例成功")
        return jsonify({"message": "Live settings updated", "connectWebSocket": True}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Error updating live settings: " + str(e)}), 500

@main.route('/stop_live', methods=['POST'])
@jwt_required()
def stop_live():
    current_user_id = get_jwt_identity()

    try:
        user_status = UserStatus.query.filter_by(user_id=current_user_id).first()
        if user_status:
            user_status.is_live_streaming = False
            user_status.voice = None
            user_status.speech_speed = None
            user_status.broadcast_strategy = None
            user_status.ai_rewrite = False
            user_status.is_broadcasting = False  # 更新 is_broadcasting 状态
            db.session.commit()
        print("停止成功")
        return jsonify({"message": "Live stopped"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Error stopping live: " + str(e)}), 500



#负责接收用户音频长度，合成普通音频给他
@main.route('/check_audio_stream', methods=['POST'])
@jwt_required()
def check_audio_stream():
    current_user_id = get_jwt_identity()
    data = request.get_json()

    # 检查是否有 'current_stream_length' 字段
    if 'current_stream_length' not in data:
        return jsonify({"message": "Missing 'current_stream_length' field"}), 400
    #获取到用户传入的音频长度
    current_stream_length = data['current_stream_length']

    #这里从全局实例数组中取出需要的实例
    live_service = live_services.get(current_user_id)
    print("开始合成音频",current_stream_length)
    if current_stream_length < 5:
        audio_path = live_service.generate_normal_audio()
        print("合成出来的音频",audio_path)
        if audio_path:
            audio_full_path = os.path.join('/www/wwwroot/wurenzhibo/server', audio_path)
            try:
                with open(audio_full_path, 'rb') as audio_file:
                    audio_data = audio_file.read()
                    encoded_audio = base64.b64encode(audio_data).decode('utf-8')
                    return jsonify({"audio_data": encoded_audio}), 200
            except Exception as e:
                return jsonify({"message": f"Error reading audio file {audio_full_path}: {str(e)}"}), 500
        else:
            return jsonify({"message": "No audio generated or audio generation failed"}), 500
    elif current_stream_length >= 10:
        return jsonify({"message": "Stream length exceeds threshold, no audio generated"}), 200

    return jsonify({"message": "Audio stream check complete"}), 200



@main.route('/send_danmu', methods=['POST'])
@jwt_required()
def send_danmu():
    current_user_id = get_jwt_identity()
    data = request.get_json()

    # 检查弹幕文本是否存在
    danmu_text = data.get('danmu_text')
    if not danmu_text:
        return jsonify({"message": "Missing danmu text"}), 400

    # 检查全局实例中是否存在对应用户的 DanmuService
    if current_user_id not in danmu_services:
        return jsonify({"message": "Danmu service not initialized"}), 404
    print("收到弹幕",danmu_text)
    try:
        # 使用全局实例处理弹幕
        danmu_service = danmu_services[current_user_id]
        audio_path = danmu_service.generate_danmu_audio(danmu_text)

        if audio_path:
            audio_full_path = os.path.join('/www/wwwroot/wurenzhibo/server', audio_path)
            try:
                with open(audio_full_path, 'rb') as audio_file:
                    audio_data = audio_file.read()
                    # 对音频数据进行 Base64 编码
                    encoded_audio = base64.b64encode(audio_data).decode('utf-8')
                    print("发送弹幕音频")
                    return jsonify({"audio_data": encoded_audio}), 200
            except Exception as e:
                return jsonify({"message": f"Error reading audio file {audio_full_path}: {str(e)}"}), 500
        else:
            return jsonify({"message": "No audio generated or audio generation failed"}), 500
    except Exception as e:
        return jsonify({"message": f"Error processing danmu: {str(e)}"}), 500




@main.route('/update_speech_library', methods=['POST'])
@jwt_required()
def update_speech_library():
    current_user_id = get_jwt_identity()
    data = request.get_json()

    # 检查 JSON 数据的格式
    if not data or "paragraphs" not in data:
        return jsonify({"message": "Invalid data format"}), 400

    # 查询当前用户的话术库
    speech_library = SpeechLibrary.query.filter_by(user_id=current_user_id).first()
    
    if speech_library:
        # 如果话术库存在，则更新数据
        speech_library.data = data
    else:
        # 如果话术库不存在，创建新的话术库
        speech_library = SpeechLibrary(user_id=current_user_id, data=data)
        db.session.add(speech_library)

    db.session.commit()
    return jsonify({"message": "Speech library updated successfully"}), 200

@main.route('/get_speech_library', methods=['GET'])
@jwt_required()
def get_speech_library():
    current_user_id = get_jwt_identity()

    # 查询当前用户的话术库
    speech_library = SpeechLibrary.query.filter_by(user_id=current_user_id).first()

    if speech_library:
        # 如果话术库存在，返回数据
        return jsonify(speech_library.data), 200
    else:
        # 如果话术库不存在，返回空数据或适当的消息
        return jsonify({"message": "No speech library found for the user"}), 404
    

@main.route('/update_qa_library', methods=['POST'])
@jwt_required()
def update_qa_library():
    current_user_id = get_jwt_identity()
    data = request.get_json()

    if not data or "questions_answers" not in data:
        return jsonify({"message": "Invalid data format"}), 400

    qa_library = QALibrary.query.filter_by(user_id=current_user_id).first()
    
    if qa_library:
        qa_library.data = data
    else:
        qa_library = QALibrary(user_id=current_user_id, data=data)
        db.session.add(qa_library)

    db.session.commit()
    return jsonify({"message": "QA library updated successfully"}), 200

@main.route('/get_qa_library', methods=['GET'])
@jwt_required()
def get_qa_library():
    current_user_id = get_jwt_identity()
    qa_library = QALibrary.query.filter_by(user_id=current_user_id).first()
    result=jsonify(qa_library.data)
    print(result.data)
    if qa_library:
        return jsonify(qa_library.data), 200
    else:
        return jsonify({"message": "No QA library found for the user"}), 404


@main.route('/all_user_statuses', methods=['GET'])
@jwt_required()
def all_user_statuses():
    return jsonify({"message": "Unauthorized access"}), 403
    # try:
    #     current_user_id = get_jwt_identity()
    #     # 检查用户ID是否为1 2 
    #     if current_user_id != 1 and current_user_id != 2:
    #         return jsonify({"message": "Unauthorized access"}), 403

    #     with db.session.begin():
    #         # 查询所有用户状态，同时获取关联的用户名
    #         user_statuses = db.session.query(UserStatus, User.username).join(User, UserStatus.user_id == User.id).all()

    #         # 格式化数据为列表的字典
    #         statuses = []
    #         for status, username in user_statuses:
    #             status_data = {
    #                 "user_id": status.user_id,
    #                 "username": username,  # 添加用户名
    #                 "is_live_streaming": status.is_live_streaming,
    #                 "is_danmaku_reply_enabled": status.is_danmaku_reply_enabled,
    #                 "voice": status.voice,
    #                 "speech_speed": status.speech_speed,
    #                 "broadcast_strategy": status.broadcast_strategy,
    #                 "ai_rewrite": status.ai_rewrite,
    #                 "is_broadcasting": status.is_broadcasting,
    #                 "current_audio_timestamp": status.current_audio_timestamp,
    #                 "audio_playback_status": status.audio_playback_status
    #             }
    #             statuses.append(status_data)

    #     return jsonify(statuses), 200
    # except Exception as e:
    #     # 获取异常的堆栈跟踪作为字符串
    #     tb = traceback.format_exc()
    #     return jsonify({"message": "Error retrieving user statuses", "error": str(e), "traceback": tb}), 500

@main.route('/get_self_status', methods=['GET'])
@jwt_required()
def get_self_status():
    try:
        current_user_id = get_jwt_identity()
        
        # 查询当前用户的状态
        user_status = db.session.query(UserStatus).filter_by(user_id=current_user_id).first()
        
        if not user_status:
            return jsonify({"message": "User status not found"}), 404

        # 将状态信息格式化为字典
        status_data = {
            "user_id": user_status.user_id,
            "is_live_streaming": user_status.is_live_streaming,
            "is_danmaku_reply_enabled": user_status.is_danmaku_reply_enabled,
            "voice": user_status.voice,
            "speech_speed": user_status.speech_speed,
            "broadcast_strategy": user_status.broadcast_strategy,
            "ai_rewrite": user_status.ai_rewrite,
            "is_broadcasting": user_status.is_broadcasting,
            "current_audio_timestamp": user_status.current_audio_timestamp,
            "audio_playback_status": user_status.audio_playback_status
        }

        return jsonify(status_data), 200
    except Exception as e:
        return jsonify({"message": "Error retrieving user status: " + str(e)}), 500



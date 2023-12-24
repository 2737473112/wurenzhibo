import sys
sys.path.append('/www/wwwroot/wurenzhibo')
from server_fastapi.models import User, SpeechLibrary, QALibrary
import random
from server_fastapi.config import Config  # 导入配置文件
import requests
import json
import time
import uuid
import os
from flask import stream_with_context, Response
import queue
from threading import Thread
import httpx
import asyncio
class DanmuService:
    def __init__(self, user_id, voice='huoguo', speech_speed=1,qa_library=''):
        self.user_id = user_id
        self.danmu_queue = []  # 用来存储弹幕消息的队列
        self.qa_library = qa_library
        self.audio_queue = queue.Queue()  # 音频队列
        self.voice = voice  # 使用传入的 voice 参数，如果没有提供，则默认为 'huoguo'
        self.speech_speed = speech_speed  # 使用传入的 speech_speed 参数，如果没有提供，则默认为 1


    def get_qa_data(self):
        # 根据 user_id 从数据库中提取问答库数据
        qa_data = QALibrary.query.filter_by(user_id=self.user_id).first()

        if qa_data:
            # 处理和打印QA数据，根据需要调整
            print("QA Data:", qa_data.data)
        else:
            print("未找到与该UserID相关的QA数据")

        return qa_data
    
    def add_danmu(self, danmu_str):
        # 解析弹幕字符串
        if danmu_str.startswith("弹幕"):
            # 假设弹幕格式为 "弹幕：用户 {nickname} 说：{content}"
            parts = danmu_str.split("：", 2)
            if len(parts) == 3:
                nickname = parts[1][3:].strip()  # 提取昵称
                content = parts[2].strip()  # 提取内容
                danmu_data = {"nickname": nickname, "content": content}
                self.danmu_queue.append(danmu_data)

    def respond_to_danmu(self, danmu_data):
        # 拆分字符串获取昵称和内容
        
        parts = danmu_data.split('说：')
        nickname_part = parts[0].split('：')[-1].strip()
        content = parts[1] if len(parts) > 1 else ""

        # 从昵称部分中去除 "用户 " 前缀和后面的点号
        nickname = nickname_part.replace("用户", "").replace(".", "").strip()
        #print("弹幕内容",content)
        # 进行关键词匹配
        for qa_pair in self.qa_library['questions_answers']:
            question_keywords = qa_pair['main'].split()

            if any(keyword in content for keyword in question_keywords):
                reply = random.choice(qa_pair['sub'])
                response = f"{nickname}宝宝，{reply}"
                return response

        return None  # 如果没有找到匹配的回复，则返回 None
    #音频合成
    async def synthesize_audio(self, text):
        server_url = Config.AUDIO_SYNTHESIS_SERVER_URL
        timeout_seconds = 50
        predict_data = {
            "text_content": text,
            "model_name": self.voice,
            "speaking_length": 1
        }

        output_folder = 'audio'
        timestamp = int(time.time())
        unique_id = uuid.uuid4()
        output_file_path = os.path.join(output_folder, f'output_{timestamp}_{unique_id}.wav')

        os.makedirs(output_folder, exist_ok=True)

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(server_url, json=predict_data, timeout=timeout_seconds)
                if response.status_code == 200:
                    with open(output_file_path, "wb") as f:
                        f.write(response.content)
                    print(f"弹幕音频文件已保存：{output_file_path}")
                    return output_file_path
                else:
                    print(f"音频推理失败，错误信息：{response.text}")
                    return None
        except httpx.TimeoutException:
            print("音频推理请求超时，请检查服务器是否可达或增加超时时间。")
            return None
        except httpx.RequestError as e:
            print(f"音频推理发生请求异常：{str(e)}")
            return None


    async def generate_danmu_audio(self, danmu_data):
        try:
            reply = self.respond_to_danmu(danmu_data)
            #print("回复",reply)
            if reply:
                print("回复弹幕:", reply)
                audio_path = await self.synthesize_audio(reply)
                return audio_path
            else:
                return None
        except Exception as e:
            print(f"Error processing danmu: {e}")
            return None

from ..models import User, SpeechLibrary
import random
from ..config import Config  # 导入配置文件
import requests
import json
import time
import uuid
import os
from flask import stream_with_context, Response
import queue
import time
import threading
class LiveService:
    def __init__(self, user_id, voice, speech_speed, broadcast_strategy, ai_rewrite, speech_library):
        self.user_id = user_id
        self.voice = voice
        self.speech_speed = speech_speed
        self.broadcast_strategy = broadcast_strategy
        self.ai_rewrite = ai_rewrite

        self.speech_library = speech_library  # 直接赋值
        self.current_position = 0  # 初始化抽取位置为0

        self.audio_queue = queue.Queue()  # 音频队列

        self.running = True
        self.audio_synthesis_paused = threading.Event()
        self.audio_synthesis_paused.set()  # 默认设置为不暂停
        
    #数据库获取文案
    def get_speech_data(self):
        # 根据 user_id 从数据库中提取话术
        #print("开始从数据库提取数据", self.user_id)
        speech_data = SpeechLibrary.query.filter_by(user_id=self.user_id).first()

        # if speech_data:
        #    # print("提取到的数据内容:")
        #    # print("ID:", speech_data.id)
        #     #print("Data:", speech_data.data)
        #    # print("UserID:", speech_data.user_id)
        # else:
        #     print("未找到与该UserID相关的数据")

        return speech_data

    #抽取文案    
    def extract_text(self):
        # 从 self.speech_library 获取话术段落列表
        speech_data = self.speech_library
        paragraphs = speech_data.get('paragraphs', [])
        
        if not paragraphs:
            return "没有找到话术内容"

        main_text = ''
        sub_texts = []
       # print(self.broadcast_strategy)
        if self.broadcast_strategy == '顺序播报':
            # 顺序播放模式
          
            if self.current_position >= len(paragraphs):
                self.current_position = 0

            current_paragraph = paragraphs[self.current_position]
            main_text = current_paragraph.get('main', '')
            sub_texts = current_paragraph.get('sub', [])
            self.current_position += 1
        
        elif self.broadcast_strategy == '随机播报':
     
            # 随机抽取模式
          #  print("开始随机抽取")
            current_paragraph = random.choice(paragraphs)
            main_text = current_paragraph.get('main', '')
            sub_texts = current_paragraph.get('sub', [])

        # 确保 main_text 和 sub_texts 至少有一个非空
        if not main_text and not sub_texts:
            return "没有可用的文案"

        # 随机选择一条文案（主话术或副话术）
        choices = [text for text in [main_text] + sub_texts if text]
        if not choices:
            return "没有可用的文案"

        selected_text = random.choice(choices)
        return selected_text
    
    def format_check_and_convert(self, text):
        # 这里是文本格式检查和转换的具体实现
        # 示例：去除多余空格，规范标点符号等
        text = text.replace(" ", "")  # 去除空格
        # 可以添加更多的格式化规则
        return text


    #ai文案重写
    def rewrite_text(self, content):
        # 配置项，这里需要根据实际情况配置
        api_key = Config.MINIMAX_API_KEY
        group_id = Config.MINIMAX_GROUP_ID

        def parse_chunk_delta(chunk_str):
            parsed_data = json.loads(chunk_str[6:])
            if "usage" in parsed_data:
                return
            try:
                delta_content = parsed_data.get("choices", [{}])[0].get("messages", [{}])
                text_content = delta_content[0].get("text", "不好意思，我没有听清楚")
                return text_content
            except (TypeError, IndexError, KeyError):
                return "不好意思，我没有听清楚"

        if self.ai_rewrite:
            url = f"https://api.minimax.chat/v1/text/chatcompletion_pro?GroupId={group_id}"
            payload = {
                "bot_setting": [
                    {
                        "bot_name": "晓吴",
                        "content": "晓吴是一名带货主播。",
                    }
                ],
                "messages": [{"sender_type": "USER", "sender_name": "小明", "text": "你是一名抖音带货文案创作者，请用抖音带货文案的风格方式重写一遍这段文案："+content}],
                "reply_constraints": {"sender_type": "BOT", "sender_name": "晓吴"},
                "model": "abab5.5-chat",
                "stream": True,
                "tokens_to_generate": 1034,
                "temperature": 1,
                "top_p": 0.95,
            }
            headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
            try:
                response = requests.post(url, headers=headers, json=payload, stream=True, timeout=30)
            except requests.Timeout:
                print("请求超时，请检查网络连接或者服务器状态。")
                return ""
            except requests.RequestException as e:
                print(f"请求失败：{e}")
                return ""

            all_text_segments = []
            current_text = ""
            for chunk in response.iter_lines():
                if chunk:
                    chunk_str = chunk.decode("utf-8")
                    text_content = parse_chunk_delta(chunk_str)
                    if text_content:
                        current_text += text_content

                        while True:
                            end_idx = -1
                            for punc in ['。', '！', '？']:
                                idx = current_text.find(punc)
                                if idx != -1:
                                    end_idx = idx if end_idx == -1 else min(end_idx, idx)

                            if end_idx != -1:
                                all_text_segments.append(current_text[:end_idx + 1])
                                current_text = current_text[end_idx + 1:]
                            else:
                                break
        else:
            all_text_segments = []
            current_text = content
            end_idx = -1
            comma_count = 0
            max_commas = 3

            for i, char in enumerate(current_text):
                if char in ['，', '。', '！', '？']:
                    if char == '，':
                        comma_count += 1
                        if comma_count >= max_commas:
                            all_text_segments.append(current_text[:i + 1])
                            current_text = current_text[i + 1:]
                            comma_count = 0
                            continue
                    else:
                        comma_count = 0

                    end_idx = i
                    all_text_segments.append(current_text[:end_idx + 1])
                    current_text = current_text[end_idx + 1:]

            if current_text:
                all_text_segments.append(current_text)

        # 将所有文本片段合并
        final_text = "".join(all_text_segments)

        # 对文本格式进行检查和转换
        final_text = self.format_check_and_convert(final_text)

        return final_text


    
    #音频合成
    def synthesize_audio(self, text):
        #print("开始合成普通音频")
        server_url=Config.AUDIO_SYNTHESIS_SERVER_URL
        timeout_seconds = 50
        predict_data = {
            "text_content": text,
            "model_name": self.voice,  # 使用传入的音色参数
            #"speaking_length": self.speech_speed  # 使用传入的速度参数
            "speaking_length": 1.0  # 使用传入的速度参数
        }

        output_folder = 'audio'  # 更改为你希望保存音频文件的目录
        timestamp = int(time.time())
        unique_id = uuid.uuid4()
        output_file_path = os.path.join(output_folder, f'output_{timestamp}_{unique_id}.wav')

        os.makedirs(output_folder, exist_ok=True)

        try:
            response = requests.post(server_url, json=predict_data, timeout=timeout_seconds)
            if response.status_code == 200:
                with open(output_file_path, "wb") as f:
                    f.write(response.content)
                #print(f"音频文件已保存：{output_file_path}")
                return output_file_path  # 返回音频文件路径
            else:
                print(f"音频推理失败，错误信息：{response.text}")
                return None

        except requests.exceptions.Timeout:
            print("音频推理请求超时，请检查服务器是否可达或增加超时时间。")
            return None
        except requests.exceptions.RequestException as e:
            print(f"音频推理发生请求异常：{str(e)}")
            return None
    
    #开始直播
    def start_live(self):
        thread = threading.Thread(target=self._audio_synthesis_loop)
        thread.start()

    def _audio_synthesis_loop(self):
        while self.running:
            try:
                self.audio_synthesis_paused.wait()  # 检查是否暂停
                text = self.extract_text()  # 抽取文案
                for rewritten_text in self.rewrite_text(text):  # 对文案进行重写
                    try:
                        audio_path = self.synthesize_audio(rewritten_text)  # 合成音频
                        if audio_path:
                            self.audio_queue.put(audio_path)  # 将音频路径放入队列
                            #print("合成成功")
                        else:
                            print("Audio synthesis failed.")
                    except Exception as e:
                        print(f"Error during audio synthesis: {e}")
                time.sleep(1)  # 设置间隔避免过快生成
            except Exception as e:
                print(f"Error in audio synthesis loop: {e}")

    #获取音频
    def get_next_audio(self):
        if not self.audio_queue.empty():
            return self.audio_queue.get()  # 从队列获取音频路径
        return None
    
    def get_all_audio(self):
        audio_list = []
        while not self.audio_queue.empty():
            audio_path = self.audio_queue.get()
            audio_list.append({"audio_path": audio_path, "type": "audio"})
        return audio_list 
      
    def control_audio_synthesis(self, audio_count):
        if audio_count >= 10:
            #print("暂停合成")
            self.audio_synthesis_paused.clear()  # 暂停合成
        else:
            #print("恢复合成")
            self.audio_synthesis_paused.set()  # 恢复合成
              
    #停止直播
    def stop_live(self):
        self.running = False
        self.audio_synthesis_paused.set()  # 确保线程能退出循环
        
        
    #供给websocket使用，调用一次合成一个音频
    # def generate_normal_audio(self):
    #     try:
    #         text = self.extract_text()  # 抽取文案
    
    #         for rewritten_text in self.rewrite_text(text):  # 对文案进行重写
    #             try:
    #                 audio_path = self.synthesize_audio(rewritten_text)  # 合成音频
    
    #                 if audio_path:
    #                     yield audio_path
    #                 else:
    #                     print("Audio synthesis failed.")
    #                     # 如果失败，也返回None以便处理
    #                     yield None
    #             except Exception as e:
    #                 print(f"Error during audio synthesis: {e}")
    #                 yield None
    #     except Exception as e:
    #         print(f"Error in generate_normal_audio: {e}")
    #         yield None
        
        
    # def generate_normal_audio(self):
    #     try:
    #         text = self.extract_text()  # 抽取文案

    #         # 修改：使用新的 rewrite_text 函数，它现在返回一段完整的文本
    #         rewritten_text = self.rewrite_text(text)

    #         # 检查 rewritten_text 是否有效
    #         if rewritten_text:
    #             try:
                    
    #                 audio_path = self.synthesize_audio(rewritten_text)  # 合成音频
    
    #                 if audio_path:
    #                     yield audio_path
    #                 else:
    #                     print("Audio synthesis failed.")
    #                     # 如果失败，也返回 None 以便处理
    #                     yield None
    #             except Exception as e:
    #                 print(f"Error during audio synthesis: {e}")
    #                 yield None
    #         else:
    #             print("Text rewriting failed.")
    #             yield None
    #     except Exception as e:
    #         print(f"Error in generate_normal_audio: {e}")
    #         yield None
        

    def generate_normal_audio(self):
        try:
            text = self.extract_text()  # Extract text

            # Modify: Use new rewrite_text function, now returning a complete text
            rewritten_text = self.rewrite_text(text)

            # Check if rewritten_text is valid
            if rewritten_text:
                try:
                    audio_path = self.synthesize_audio(rewritten_text)  # Synthesize audio

                    if audio_path:
                        return audio_path
                    else:
                        print("Audio synthesis failed.")
                        return None
                except Exception as e:
                    print(f"Error during audio synthesis: {e}")
                    return None
            else:
                print("Text rewriting failed.")
                return None
        except Exception as e:
            print(f"Error in generate_normal_audio: {e}")
            return None
# if __name__ == "__main__":
#     # 测试文案重写函数
#     test_content = "请进行文案重写：测试文案"
#     for rewritten_text in rewrite_text(test_content):
#         print(rewritten_text)
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
import time
import threading
import httpx
import aiofiles
class LiveService:
    def __init__(self, user_id, voice, speech_speed, broadcast_strategy, ai_rewrite, speech_library):
        self.user_id = user_id
        self.voice = voice
        self.speech_speed = speech_speed
        self.broadcast_strategy = broadcast_strategy
        self.ai_rewrite = ai_rewrite
        self.speech_library = speech_library  # 直接赋值
        self.current_position = 0  # 初始化抽取位置为0

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

    # 对文本进行违禁词过滤
    def filter_prohibited_words(self,content):
        prohibited_words = [
            "最", "最佳", "最具", "最赚", "最优", "最优秀", "最好", "最大", "最高", "最奢侈", "最低", "最便宜", 
            "最流行", "最受欢迎", "最时尚", "最先", "最先进", "最新", "绝无仅有", "顶级", "第一品牌", 
            "国家级", "全球级", "宇宙级", "世界级", "极品", "极佳", "极致", "顶尖", "尖端", "终极", "首个", 
            "首选", "全球首发", "全国首家", "全网首发", "独家", "国家领导人", "政协用酒", "人民大会堂", 
            "全国人大", "军队", "政府定价", "世界领先", "行业领先", "领先上市", "领袖品牌", "创领品牌", 
            "领导品牌", "缔造者", "王者", "至尊", "巅峰", "之王", "性价比之王", "王牌", "销量冠军", "绝对", 
            "永久", "无敌", "包过", "一次通过", "保值", "升值", "立马升值", "投资价值", "投资回报", "冥器", 
            "旺夫", "旺子", "带来好运气", "逢凶化吉", "避凶", "辟邪", "防小人", "化解小人", "增加事业运", 
            "招财进宝", "健康富贵", "提升运气", "助吉避凶", "转富招福", "评比", "排序", "指定", "推荐", 
            "选用", "获奖", "无效退款", "保险公司保险", "不反复", "三天即愈", "根治", "比手术安全", 
            "包治百病", "一盒见效", "彻底康复", "无副作用", "痊愈", "立马见效", "100%有效", "零风险", 
            "无毒副作用", "无依赖", "安全", "热销", "抢购", "试用", "免费治病", "免费赠送","极品","前所未有","选用",
            "免疫力", "提高身体免疫力", "抵抗力" ,"身体抵抗力", "免疫抵抗力","史无前例","秒杀","超级","给力","中药"
        ]

        for word in prohibited_words:
            content = content.replace(word, '')
        return content

    #ai文案重写
    async def rewrite_text(self, content):
        # 配置项
        api_key = Config.MINIMAX_API_KEY
        group_id = Config.MINIMAX_GROUP_ID

        def parse_chunk_delta(chunk_str):
            try:
                parsed_data = json.loads(chunk_str[6:])
                if "usage" in parsed_data:
                    return
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

            async with httpx.AsyncClient() as client:
                try:
                    response = await client.post(url, headers=headers, json=payload, timeout=30)
                except httpx.TimeoutException:
                    print("请求超时，请检查网络连接或者服务器状态。")
                    return ""
                except httpx.RequestError as e:
                    print(f"请求失败：{e}")
                    return ""

                all_text_segments = []
                current_text = ""
                async for chunk in response.aiter_lines():
                    if chunk:
                        text_content = parse_chunk_delta(chunk)
                        
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
        # final_text = self.format_check_and_convert(final_text)  # 假设存在此方法
        final_text= self.filter_prohibited_words(final_text)
        return final_text
    
    #音频合成
    async def synthesize_audio(self, text):
        server_url = Config.AUDIO_SYNTHESIS_SERVER_URL
        timeout_seconds = 50
        predict_data = {
            "text_content": text,
            "model_name": self.voice,
            "speaking_length": 1.0
        }

        output_folder = 'audio'
        timestamp = int(time.time())
        unique_id = uuid.uuid4()
        output_file_path = os.path.join(output_folder, f'output_{timestamp}_{unique_id}.wav')

        os.makedirs(output_folder, exist_ok=True)

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(server_url, json=predict_data, timeout=timeout_seconds)
                if response.status_code == 200:
                    async with aiofiles.open(output_file_path, "wb") as f:
                        await f.write(response.content)
                    return output_file_path
                else:
                    print(f"音频推理失败，错误信息：{response.text}")
                    return None

            except httpx.RequestError as e:
                print(f"音频推理发生请求异常：{str(e)}")
                return None


    async def generate_normal_audio(self):
        try:
            text = self.extract_text()  # Extract text
            rewritten_text = await self.rewrite_text(text)  #  # 使用 await 调用异步方法
            if rewritten_text:
                try:
                    audio_path = await self.synthesize_audio(rewritten_text)

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
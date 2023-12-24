import requests

def fetch_user_statuses():
    url = "http://36.103.180.62:5000/all_user_statuses"
    try:
        response = requests.get(url)
        response.raise_for_status()  # 检查请求是否成功

        # 打印每个用户的状态
        for status in response.json():
            print(f"用户ID: {status['user_id']}, "
                  f"是否直播中: {'是' if status['is_live_streaming'] else '否'}, "
                  f"弹幕回复启用: {'是' if status['is_danmaku_reply_enabled'] else '是'}, "
                  f"声音: {status['voice']}, "
                  f"语速: {status['speech_speed']}, "
                  f"播报策略: {status['broadcast_strategy']}, "
                  f"AI重写: {'是' if status['ai_rewrite'] else '否'}, "
                  f"是否开始直播: {'是' if status['is_broadcasting'] else '否'}, "
                  f"音频时间戳: {status['current_audio_timestamp']}, "
                  f"音频播放状态: {status['audio_playback_status']}")
    except requests.RequestException as e:
        print(f"请求失败: {e}")

if __name__ == "__main__":
    fetch_user_statuses()

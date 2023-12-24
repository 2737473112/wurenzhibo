import { defineStore } from 'pinia';
import request from '../utils/request'; // 假设这是您封装的请求方法
import { ElMessage } from 'element-plus';

export const useBroadcastStore = defineStore('broadcast', {
    state: () => ({
        isBroadcasting: false,
        isDanmuResponding: false,
        audioQueue: [] as string[], // 普通音频队列
        danmuAudioQueue: [] as string[], // 弹幕音频队列
        audioPollingInterval: null as number | null,
        audioPlayer: new Audio(), // 创建一个新的 Audio 实例
        voice: 'huoguo',
        speechSpeed: '1.0',
        broadcastStrategy: '随机播报',
        aiRewrite: false,
        productInfo: '1',
        anchorRole: '1'
    }),

    actions: {
        // 开始直播
        async startBroadcast(broadcastData: any) {
            // 清除音频队列
            this.audioQueue = [];
            this.danmuAudioQueue = [];
            this.isBroadcasting = true;
            try {
                const response = await request.post('/start_live', broadcastData);
                if (response.status === 200) {
                    ElMessage.success('开始直播成功');
                    this.startAudioPolling();
                } else {
                    ElMessage.error('开始直播失败：' + response.data.message);
                    this.isBroadcasting = false; // 重置直播状态
                }
            } catch (error) {
                ElMessage.error('开始直播失败：' + error.response.data.message);
                this.isBroadcasting = false; // 重置直播状态
            }
        },
        // 停止直播
        async stopBroadcast() {
            this.isBroadcasting = false;
            this.stopAudioPlayback(); // 新增停止音频播放方法
            try {
                const response = await request.post('/stop_live');
                if (response.status === 200) {
                    ElMessage.success('停止直播成功');
                } else {
                    ElMessage.error('停止直播失败：' + response.data.message);
                }
            } catch (error) {
                ElMessage.error('停止直播失败：' + error.response.data.message);
            }
        },
        // 开始弹幕回复
        async startDanmuResponse() {
            this.isDanmuResponding = true;

            // 创建一个包含用户选择的参数的对象
            const danmuResponseData = {
                voice: this.voice,
                speechSpeed: this.speechSpeed,
                broadcastStrategy: this.broadcastStrategy,
                aiRewrite: this.aiRewrite,
                productInfo: this.productInfo,
                anchorRole: this.anchorRole
            };

            try {
                const response = await request.post('/start_danmu_response', danmuResponseData);
                if (response.status === 200) {
                    ElMessage.success('开始弹幕回复成功');
                } else {
                    ElMessage.error('开始弹幕回复失败：' + response.data.message);
                    this.isDanmuResponding = false;
                }
            } catch (error) {
                ElMessage.error('开始弹幕回复失败：' + error.response.data.message);
                this.isDanmuResponding = false;
            }
        },

        // 停止弹幕回复
        async stopDanmuResponse() {
            try {
                const response = await request.post('/stop_danmu_response');
                if (response.status === 200) {
                    ElMessage.success('停止弹幕回复成功');
                } else {
                    ElMessage.error('停止弹幕回复失败：' + response.data.message);
                }
            } catch (error) {
                ElMessage.error('停止弹幕回复失败：' + error.response.data.message);
            }
            this.isDanmuResponding = false;
        },

        // 新增停止音频播放的方法
        stopAudioPlayback() {
            if (this.audioPlayer) {
                this.audioPlayer.pause(); // 暂停播放
                this.audioPlayer.src = ''; // 清空音频源
            }
            this.audioQueue.splice(0, this.audioQueue.length); // 清空音频队列
            if (this.audioPollingInterval) {
                clearInterval(this.audioPollingInterval); // 停止轮询
                this.audioPollingInterval = null;
            }
        },
        // 开始轮询音频
        // 在 useBroadcastStore 的 actions 中
        startAudioPolling() {
            if (this.audioPollingInterval) clearInterval(this.audioPollingInterval);
            this.audioPollingInterval = setInterval(async () => {
                try {
                    console.log("开始轮询音频");
                    // 传递当前普通音频队列的长度
                    const audioCount = this.audioQueue.length;
                    const response = await request.get('/get_audio', {
                        params: { audio_count: audioCount }
                    });
                    console.log("收到响应：", response);

                    if (response.status === 200 && Array.isArray(response.data)) {
                        const serverUrl = 'http://132.232.101.2:5000/'; // 服务器地址和端口
                        response.data.forEach(audioData => {
                            const audioPath = serverUrl + audioData.audio_path;
                            if (audioData.type === 'danmu_audio') {
                                console.log(audioPath);
                                this.danmuAudioQueue.push(audioPath); // 存储弹幕音频到队列
                            } else {
                                console.log(audioPath);
                                this.audioQueue.push(audioPath); // 存储普通音频到队列
                            }
                        });
                    } else {
                        console.log("响应格式不正确或音频路径缺失");
                    }
                } catch (error) {
                    console.error('获取音频失败：', error);
                }
            }, 1000); // 每秒轮询一次
        },


        // 停止轮询音频
        stopAudioPolling() {
            if (this.audioPollingInterval) {
                clearInterval(this.audioPollingInterval);
                this.audioPollingInterval = null;
            }
        },

        // 在 Pinia store 中
        playNextAudio() {
            // 选择当前要播放的音频队列
            const queue = this.danmuAudioQueue.length > 0 ? this.danmuAudioQueue : this.audioQueue;

            // 检查队列是否有音频，并且播放器当前没有播放
            if (queue.length > 0 && this.audioPlayer.paused) {
                const nextAudioPath = queue.shift();
                if (nextAudioPath) {
                    this.audioPlayer.src = nextAudioPath;
                    this.audioPlayer.play().then(() => {
                        console.log("音频播放开始");
                    }).catch(error => {
                        console.error('播放音频失败:', error);
                    });

                    // 在音频结束时播放下一个音频
                    this.audioPlayer.onended = () => {
                        this.playNextAudio(); // 直接调用自身以播放下一个音频
                    };
                }
            } else {
                console.log("等待新的音频");
                setTimeout(() => this.playNextAudio(), 1000); // 如果队列为空，每秒检查一次
            }
        },


        // 新增更新设置的方法
        updateSettings(settings) {
            this.voice = settings.voice;
            this.speechSpeed = settings.speechSpeed;
            this.broadcastStrategy = settings.broadcastStrategy;
            this.aiRewrite = settings.aiRewrite;
            this.productInfo = settings.productInfo;
            this.anchorRole = settings.anchorRole;
        },






    }
});

<template>
  <div>
    <!-- <audio ref="audioPlayer" controls></audio>  -->
    <!-- 显示普通音频队列长度的区域 -->


    <el-row>
      <el-col :span="24">
        <div class="audio-queue-length">
          当前普通音频队列长度: {{ normalAudioQueueLength }}
        </div>
        <div class="audio-queue-length">
          当前弹幕音频队列长度: {{ danmuAudioQueueLength }}
        </div>
      </el-col>
    </el-row>
    <el-slider v-model="audioProgress" disabled></el-slider>

    <el-row>
      <el-col :span="6">
        <el-form-item label="音色选择">
          <el-select v-model="selectedTone" placeholder="请选择音色">
            <el-option label="手机" value="shouji"></el-option>
            <el-option label="火锅" value="huoguo"></el-option>
            <el-option label="潮汕" value="chaoshan"></el-option>
          </el-select>
        </el-form-item>
      </el-col>

      <el-col :span="6">
        <el-form-item label="说话速度">
          <el-select v-model="selectedSpeed" placeholder="请选择速度">
            <el-option label="0.9" value="0.9"></el-option>
            <el-option label="1.0" value="1.0"></el-option>
            <el-option label="1.1" value="1.1"></el-option>
          </el-select>
        </el-form-item>
      </el-col>

      <el-col :span="6">
        <el-form-item label="播报策略">
          <el-select v-model="selectedStrategy" placeholder="请选择播报策略">
            <el-option label="随机播报" value="随机播报"></el-option>
            <el-option label="顺序播报" value="顺序播报"></el-option>
          </el-select>
        </el-form-item>
      </el-col>

      <el-col :span="6">
        <el-form-item label="AI重写">
          <el-select v-model="selectedAI" placeholder="请选择">
            <el-option label="是" value="是"></el-option>
            <el-option label="否" value="否"></el-option>
          </el-select>
        </el-form-item>
      </el-col>
    </el-row>

    <el-form-item>
      <el-button v-if="!isLive" type="primary" @click="startLive">开始直播</el-button>
      <el-button v-else type="danger" @click="stopLive">停止直播</el-button>
      <el-button v-if="!isDanmuCapture" type="primary" @click="startDanmuCapture">开启弹幕捕获</el-button>
      <el-button v-else type="danger" @click="stopDanmuCapture">停止弹幕捕获</el-button>

    </el-form-item>

    <el-col :span="24">
      <div class="danmu-display" ref="danmuDisplay">
        <el-scrollbar wrap-class="scroll-wrap">
          <div v-for="(message, index) in messages" :key="index" class="danmu-message">
            {{ message }}
          </div>
        </el-scrollbar>
      </div>
    </el-col>
  </div>
</template>
  
<script>
import { ref, onUnmounted, onMounted, onUpdated, computed } from 'vue';
import { ElSelect, ElOption, ElForm, ElFormItem, ElButton, ElRow, ElCol, ElSlider } from 'element-plus';
import service from '../utils/request.ts';
import { io } from 'socket.io-client';
export default {
  name: "dashboard",
  components: {
    ElSelect, ElOption, ElForm, ElFormItem, ElButton, ElRow, ElCol
  },
  setup() {
    const selectedTone = ref('shouji');
    const selectedSpeed = ref('1.0');
    const selectedStrategy = ref('随机播报');
    const selectedAI = ref('否');
    const isLive = ref(false);
    const isDanmuCapture = ref(false);
    const danmuAudioQueue = ref([]);
    const normalAudioQueue = ref([]);
    const normalAudioQueueLength = computed(() => normalAudioQueue.value.length);
    const danmuAudioQueueLength = computed(() => danmuAudioQueue.value.length);
    const messages = ref([]); // 用于存储弹幕消息
    const danmuDisplay = ref(null);
    const isAudioPlaying = ref(false);
    const audioPlayer = ref(null);
    let socket = null;
    let intervalId = ref(null);
    let isAudioErrored = false;
    const audioProgress = ref(0);



    window.onerror = function (message, source, lineno, colno, error) {
      console.error('捕获到未处理的错误:', message);
      // 在这里处理错误（比如记录日志）
    };

    // 接收并处理从 Python 发送的弹幕
    window.receiveDanmu = async (danmu) => {
      const maxMessagesSize = 100; // 例如，最多保持100条消息
      // 如果达到最大容量，移除最早的消息
      if (messages.value.length >= maxMessagesSize) {
        messages.value.shift(); // 移除数组中的第一个元素
      }
      // 添加新的弹幕消息
      messages.value.push(danmu);

      // 检查弹幕是否以“弹幕”开头
      if (danmu.startsWith("弹幕")) {
        try {
          // 发送弹幕数据到后端
          const response = await service.post('/send_danmu', {
            danmu_text: danmu
          });

          if (response.data && response.data.audio_url) {
            // 使用接收到的音频文件 URL
            console.log("接收到弹幕音频URL", response.data.audio_url);
            // 可以添加代码来播放音频或进行其他操作
            danmuAudioQueue.value.push(response.data.audio_url);
          }
        } catch (error) {
          console.error('发送弹幕请求失败:', error);
        }
      }
    };

    const startLive = async () => {
      const data = {
        voice: selectedTone.value,
        speechSpeed: selectedSpeed.value,
        broadcastStrategy: selectedStrategy.value,
        aiRewrite: selectedAI.value,
        productInfo: '测试',
        anchorRole: '测试'
      };
      // 如果开启了AI重写，则弹出消息
      if (selectedAI.value === '是') {
        ElMessage({
          message: '如果开启了AI重写，请稍等30秒，后台正在重写中。',
          type: 'info',
          duration: 5000 // 消息显示时间（毫秒），0表示不自动关闭
        });
      }
      const response = await service.post('/start_live', data);
      console.log(response.data);
      isLive.value = true;
      // 清空音频队列并重新初始化
      danmuAudioQueue.value = [];
      normalAudioQueue.value = [];
      // 启动定时检查音频队列的任务
      startAudioCheckTask();
      playAudio(); // 启动播放音频的方法
    };


    let isWaitingForAudio = false;

    // 定时检查音频队列的函数
    const startAudioCheckTask = () => {
      console.log("开始进行请求");
      intervalId.value = setInterval(async () => {
        // 当直播已停止时，不再检查或添加音频
        if (!isLive.value || isAudioPlaying.value) {
          console.log("直播已停止，不再检查音频");
          return;
        }

        if (normalAudioQueue.value.length < 4 && !isWaitingForAudio) {
          try {
            isWaitingForAudio = true;
            const response = await service.post('/check_audio_stream', {
              current_stream_length: normalAudioQueue.value.length
            });
            if (response.data && response.data.audio_url) {
              // 使用接收到的音频URL
              normalAudioQueue.value.push(response.data.audio_url);
              console.log("往内部添加一个！！！！！现在有了", normalAudioQueue.value.length);
            }
          } catch (error) {
            console.error('获取音频失败:', error);
          } finally {
            isWaitingForAudio = false;
          }
        }
      }, 1000);
    };


    // 播放音频的方法
    // 播放音频的方法
 // 播放音频的方法
const playAudio = () => {
  // 如果当前有音频正在播放，则不继续播放新的音频
  if (isAudioPlaying.value) {
    return;
  }

  let audioSrc = null;

  // 获取音频源
  if (danmuAudioQueue.value.length > 0) {
    audioSrc = danmuAudioQueue.value.shift();
  } else if (normalAudioQueue.value.length > 0) {
    audioSrc = normalAudioQueue.value.shift();
  }

  // 如果有音频可以播放
  if (audioSrc) {
    const audio = new Audio(audioSrc);
    audioPlayer.value = audio;

    audio.play().then(() => {
      isAudioPlaying.value = true;

      // 音频播放结束时的处理
      audio.onended = () => {
        isAudioPlaying.value = false;
        audioProgress.value = 0; // 重置进度条
        playAudio(); // 继续播放下一个音频
      };

      // 更新音频进度
      audio.ontimeupdate = () => {
        audioProgress.value = (audio.currentTime / audio.duration) * 100;
      };

    }).catch(e => {
      console.error('播放音频失败:', e);
      isAudioPlaying.value = false; // 如果播放失败，确保允许播放下一个音频
      setTimeout(playAudio, 1000);
    });
  } else {
    // 没有音频可播放时，稍后再试
    setTimeout(playAudio, 1000);
  }
};


    // 停止直播
// 停止直播
const stopLive = async () => {
  try {
    const response = await service.post('/stop_live');
    console.log(response.data);
    isLive.value = false;

    // 清空音频队列
    danmuAudioQueue.value = [];
    normalAudioQueue.value = [];

    // 停止当前正在播放的音频
    if (audioPlayer.value) {
      audioPlayer.value.pause();
      audioPlayer.value = null; // 清除音频播放器的引用
    }

    // 清除定时器
    if (intervalId.value) {
      clearInterval(intervalId.value);
      console.log('音频检查任务已停止');
    }

    // 重置播放状态
    isAudioPlaying.value = false;

    // 重置错误标志
    isAudioErrored = false;

  } catch (error) {
    console.error('Error stopping live:', error);
  }
};



    // 开启弹幕捕获
    const startDanmuCapture = () => {
      if (window.pywebview && window.pywebview.api) {
        window.pywebview.api.startDanmuCapture();
        isDanmuCapture.value = true;
      } else {
        console.error('Python环境未检测到');
      }
    };

    // 停止弹幕捕获
    const stopDanmuCapture = () => {
      if (window.pywebview && window.pywebview.api) {
        window.pywebview.api.stopDanmuCapture();
        isDanmuCapture.value = false;
      } else {
        console.error('Python环境未检测到');
      }
    };




    // 清理函数，在组件卸载时清除定时器
    onUnmounted(() => {
      if (intervalId) {
        clearInterval(intervalId);
      }
    });
    onMounted(async () => {

    });

    onUpdated(() => {
      const danmuDisplayElement = danmuDisplay.value;
      if (danmuDisplayElement) {
        danmuDisplayElement.scrollTop = danmuDisplayElement.scrollHeight;
      }
    });

    return {
      selectedTone, selectedSpeed, selectedStrategy, selectedAI, isLive, isDanmuCapture,
      startLive, stopLive, startDanmuCapture, stopDanmuCapture,
      danmuAudioQueue, normalAudioQueue, messages, normalAudioQueueLength, danmuAudioQueueLength, audioProgress, audioPlayer
    };
  }

};
</script>
  
<style scoped>
.danmu-display {
  border: 1px solid #dcdfe6;
  height: 300px;
  /* 设置弹幕显示区域的高度 */
  overflow: hidden;
}

.audio-queue-length {
  padding: 10px;
  background-color: #f2f2f2;
  text-align: left;
  /* 将文本对齐方式改为左对齐 */
  font-size: 16px;
}

.scroll-wrap {
  height: 100%;
}

.danmu-message {
  white-space: nowrap;
  padding: 5px 10px;
  border-bottom: 1px solid #f2f2f2;
}
</style>

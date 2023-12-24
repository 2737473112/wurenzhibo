<template>
  <div>
    <h1>用户状态管理</h1>
    <el-table :data="userStatuses" style="width: 100%">
      <el-table-column prop="username" label="用户名"></el-table-column>
      <el-table-column prop="user_id" label="用户ID"></el-table-column>
      <el-table-column prop="is_broadcasting" label="是否正在直播"></el-table-column>
      <el-table-column prop="voice" label="声音"></el-table-column>
      <el-table-column prop="speech_speed" label="语速"></el-table-column>
      <el-table-column prop="broadcast_strategy" label="播报策略"></el-table-column>
      <el-table-column prop="ai_rewrite" label="AI重写"></el-table-column>
      <el-table-column prop="current_audio_timestamp" label="音频时间戳"></el-table-column>
      <el-table-column prop="audio_playback_status" label="音频播放状态"></el-table-column>
    </el-table>
  </div>
</template>

<script lang="ts">
import { defineComponent, ref, onMounted } from 'vue';
import request from '../utils/request';

export default defineComponent({
  name: 'UserStatusManagement',
  setup() {
    const userStatuses = ref([]);

    const fetchUserStatuses = async () => {
      try {
        const response = await request.get('/all_user_statuses');
        userStatuses.value = response.data;
      } catch (error) {
        console.error('Error fetching user statuses:', error);
      }
    };

    onMounted(() => {
      fetchUserStatuses();
      setInterval(fetchUserStatuses, 1000); // 每秒刷新一次数据
    });

    return {
      userStatuses
    };
  },
});
</script>

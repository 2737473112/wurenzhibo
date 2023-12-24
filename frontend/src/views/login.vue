<template>
  <div class="login-wrap">
    <div class="ms-login">
      <div class="ms-title">无人直播管理系统</div>
      <el-form
        :model="param"
        :rules="rules"
        ref="login"
        label-width="0px"
        class="ms-content"
      >
        <el-form-item prop="username">
          <el-input v-model="param.username" placeholder="username">
            <template #prepend>
              <el-button :icon="User"></el-button>
            </template>
          </el-input>
        </el-form-item>
        <el-form-item prop="password">
          <el-input
            type="password"
            placeholder="password"
            v-model="param.password"
            @keyup.enter="submitForm(login)"
          >
            <template #prepend>
              <el-button :icon="Lock"></el-button>
            </template>
          </el-input>
        </el-form-item>
        <div class="login-btn">
          <el-button type="primary" @click="submitForm(login)">登录</el-button>
        </div>
        
      </el-form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from "vue";
import { useTagsStore } from "../store/tags";
import { usePermissStore } from "../store/permiss";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import type { FormInstance, FormRules } from "element-plus";
import { Lock, User } from "@element-plus/icons-vue";
import axios from "axios";
import service from '../utils/request';  // 引入封装好的 Axios 实例
interface LoginInfo {
  username: string;
  password: string;
}

const router = useRouter();
const param = reactive<LoginInfo>({
  username: "",
  password: "",
});

const rules: FormRules = {
  username: [
    {
      required: true,
      message: "请输入用户名",
      trigger: "blur",
    },
  ],
  password: [{ required: true, message: "请输入密码", trigger: "blur" }],
};
const permiss = usePermissStore();

const login = ref<FormInstance>();

const submitForm = (formEl: FormInstance | undefined) => {
    if (!formEl) return;
    formEl.validate(async (valid: boolean) => {
        if (valid) {
            try {
                // 使用封装好的 Axios 实例 service 发送请求
                const response = await service.post('/login', {
                    username: param.username,
                    password: param.password,
                });
                if (response.status === 200) {
                    ElMessage.success('登录成功');

                    // 保存 JWT 令牌到本地存储
                    localStorage.setItem('ms_username', param.username);
                    localStorage.setItem('ms_access_token', response.data.access_token);
                    
                    const keys = permiss.defaultList[param.username == 'admin' ? 'admin' : 'user'];
                    permiss.handleSet(keys);
                    localStorage.setItem('ms_keys', JSON.stringify(keys));
                    router.push('/');
                } else {
                    ElMessage.error('登录失败：' + response.data.message);
                }
            } catch (error: any) {
                ElMessage.error('登录失败：' + error.response.data.message);
            }
        } else {
            ElMessage.error('表单验证失败');
            return false;
        }
    });
};

// const submitForm = (formEl: FormInstance | undefined) => {
//     if (!formEl) return;
//     formEl.validate(async (valid: boolean) => {
//         if (valid) {
//             try {
//                 const response = await request.post('/login', {
//                     username: param.username,
//                     password: param.password,
//                 });
//                 if (response.status === 200) {
//                     ElMessage.success('登录成功');
//                     localStorage.setItem('ms_username', param.username);
//                     const keys = permiss.defaultList[param.username == 'admin' ? 'admin' : 'user'];
//                     permiss.handleSet(keys);
//                     localStorage.setItem('ms_keys', JSON.stringify(keys));
//                     router.push('/');
//                 } else {
//                     ElMessage.error('登录失败：' + response.data.message);
//                 }
//             } catch (error: any) {
//                 ElMessage.error('登录失败：' + error.response.data.message);
//             }
//         } else {
//             ElMessage.error('表单验证失败');
//             return false;
//         }
//     });
// };

const tags = useTagsStore();
tags.clearTags();
</script>

<style scoped>
.login-wrap {
  position: relative;
  width: 100%;
  height: 100%;
  background-image: url(../assets/img/login-bg.jpg);
  background-size: 100%;
}
.ms-title {
  width: 100%;
  line-height: 50px;
  text-align: center;
  font-size: 20px;
  color: #fff;
  border-bottom: 1px solid #ddd;
}
.ms-login {
  position: absolute;
  left: 50%;
  top: 50%;
  width: 350px;
  margin: -190px 0 0 -175px;
  border-radius: 5px;
  background: rgba(255, 255, 255, 0.3);
  overflow: hidden;
}
.ms-content {
  padding: 30px 30px;
}
.login-btn {
  text-align: center;
}
.login-btn button {
  width: 100%;
  height: 36px;
  margin-bottom: 10px;
}
.login-tips {
  font-size: 12px;
  line-height: 30px;
  color: #fff;
}
</style>

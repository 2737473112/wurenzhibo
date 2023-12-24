import axios, { AxiosInstance, AxiosError, AxiosResponse, AxiosRequestConfig } from 'axios';

const service: AxiosInstance = axios.create({
    baseURL: 'http://36.103.180.62:5003', // 设置你的后端的基本 URL
    timeout: 60000,
});

service.interceptors.request.use(
    (config: AxiosRequestConfig) => {
        // 获取 JWT 令牌并添加到请求头中
        const access_token = localStorage.getItem('ms_access_token');
        if (access_token) {
            // 使用条件检查确保 config.headers 存在
            if (!config.headers) {
                config.headers = {};
            }
            config.headers['Authorization'] = `Bearer ${access_token}`;
        }
        return config;
    },
    (error: AxiosError) => {
        console.log(error);
        return Promise.reject();
    }
);

service.interceptors.response.use(
    (response: AxiosResponse) => {
        if (response.status === 200) {
            return response;
        } else {
            Promise.reject();
        }
    },
    (error: AxiosError) => {
        console.log(error);
        // 处理令牌过期的情况
        if (error.response?.status === 401) {
            // 令牌过期，重定向到登录页
            // 你可以使用你的路由导航库来实现重定向，例如 Vue Router 的 router.push('/login')
            // 或者直接跳转到登录页的 URL
            window.location.href = '/login'; // 这里示例直接跳转到登录页的 URL
        }
        return Promise.reject();
    }
);

export default service;

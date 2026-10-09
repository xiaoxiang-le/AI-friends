const platform = import.meta.env.DEV ? 'vue' : 'django'   // 本地开发与 Django 静态部署

const CONFIG_API = {
    HTTP_URL: '',
    VAD_URL: '',
}

if (platform === 'vue') {
    CONFIG_API.HTTP_URL = 'http://127.0.0.1:8000'
    CONFIG_API.VAD_URL = `${window.location.origin}/vad/`
} else if (platform === 'django') {
    CONFIG_API.HTTP_URL = window.location.origin
    CONFIG_API.VAD_URL = `${window.location.origin}/static/frontend/vad/`
} else if (platform === 'cloud') {
    CONFIG_API.HTTP_URL = 'https://app7804.acapp.acwing.com.cn'
    CONFIG_API.VAD_URL = 'https://app7804.acapp.acwing.com.cn/static/frontend/vad/'
}

export default CONFIG_API

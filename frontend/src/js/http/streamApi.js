import { fetchEventSource } from '@microsoft/fetch-event-source'
import { useUserStore } from '@/stores/user.js'
import api from './api.js'
import CONFIG_API from '@/js/config/config.js'

export default async function streamApi(url, options = {}) {
  const user = useUserStore()
  let refreshed = false
  let done = false
  while (true) {
    try {
      await fetchEventSource(CONFIG_API.HTTP_URL + url, {
        method: options.method || 'POST',
        signal: options.signal,
        credentials: 'include',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${user.accessToken}`, ...options.headers },
        body: JSON.stringify(options.body || {}),
        openWhenHidden: true,
        async onopen(response) {
          if (response.status === 401 && !refreshed) throw new Error('TOKEN_EXPIRED')
          if (!response.ok || !response.headers.get('content-type')?.includes('text/event-stream')) {
            const data = await response.json().catch(() => ({}))
            throw new Error(data.result || data.detail || `请求失败：${response.status}`)
          }
        },
        onmessage(msg) {
          if (msg.data === '[DONE]') {
            done = true
            options.onmessage?.('', true)
            return
          }
          if (!msg.data) return
          const data = JSON.parse(msg.data)
          if (data.error) throw new Error(data.error)
          options.onmessage?.(data, false)
        },
        onerror(error) { throw error },
        onclose() {
          if (!done) throw new Error('对话连接中断，请重试')
          options.onclose?.()
        },
      })
      return
    } catch (error) {
      if (options.signal?.aborted) return
      if (error.message === 'TOKEN_EXPIRED' && !refreshed) {
        refreshed = true
        const { data } = await api.post('/api/user/account/refresh_token/', {})
        user.setAccessToken(data.access)
        continue
      }
      options.onerror?.(error)
      throw error
    }
  }
}

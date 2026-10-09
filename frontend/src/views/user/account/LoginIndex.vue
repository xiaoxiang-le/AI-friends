<script setup>
import { ref } from 'vue'
import { useUserStore } from '@/stores/user.js'
import { useRoute, useRouter } from 'vue-router'
import api from '@/js/http/api.js'
import AuthLayout from '@/components/AuthLayout.vue'
const username = ref('')
const password = ref('')
const showPassword = ref(false)
const errorMessage = ref('')
const submitting = ref(false)
const user = useUserStore()
const router = useRouter()
const route = useRoute()
async function handleLogin() {
  if (submitting.value) return
  errorMessage.value = ''
  if (!username.value.trim() || !password.value.trim()) { errorMessage.value = '请输入用户名和密码'; return }
  submitting.value = true
  try {
    const { data } = await api.post('/api/user/account/login/', { username: username.value.trim(), password: password.value })
    if (data.result === 'success') {
      user.setAccessToken(data.access)
      user.setUserInfo(data)
      const target = route.query.redirect
      await router.push(typeof target === 'string' && target.startsWith('/') && !target.startsWith('//') && !/^\/(login|register)(\/|\?|$)/.test(target) ? target : { name: 'homepage-index' })
    } else { errorMessage.value = data.result || '登录失败，请稍后重试' }
  } catch { errorMessage.value = '暂时无法连接，请检查网络后重试' }
  finally { submitting.value = false }
}
</script>
<template>
  <AuthLayout><form @submit.prevent="handleLogin" class="auth-form" :aria-busy="submitting">
    <div class="form-field"><label for="login-username">用户名</label><input id="login-username" v-model="username" autocomplete="username" placeholder="输入你的用户名" required :disabled="submitting" /></div>
    <div class="form-field"><label for="login-password">密码</label><div class="password-field"><input id="login-password" v-model="password" :type="showPassword ? 'text' : 'password'" autocomplete="current-password" placeholder="输入你的密码" required :disabled="submitting" /><button type="button" @click="showPassword = !showPassword" :aria-pressed="showPassword" :aria-label="showPassword ? '隐藏密码' : '显示密码'">{{ showPassword ? '隐藏' : '显示' }}</button></div></div>
    <p v-if="errorMessage" class="form-error" role="alert">{{ errorMessage }}</p>
    <button type="submit" class="primary-button auth-submit" :disabled="submitting">{{ submitting ? '正在登录…' : '登录' }}<span v-if="!submitting">→</span></button>
    <div class="auth-divider"><span>第一次来到这里？</span></div>
    <RouterLink :to="{ name: 'user-account-register-index', query: route.query.redirect ? { redirect: route.query.redirect } : {} }" class="soft-button auth-secondary">创建新账号</RouterLink>
  </form></AuthLayout>
</template>

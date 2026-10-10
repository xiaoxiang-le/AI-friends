<script setup>
import { ref } from 'vue'
import { useUserStore } from '@/stores/user.js'
import { useRoute, useRouter } from 'vue-router'
import api from '@/js/http/api.js'
import AuthLayout from '@/components/AuthLayout.vue'
const username = ref('')
const password = ref('')
const passwordConfirm = ref('')
const showPassword = ref(false)
const errorMessage = ref('')
const submitting = ref(false)
const user = useUserStore()
const router = useRouter()
const route = useRoute()
async function handleRegister() {
  if (submitting.value) return
  errorMessage.value = ''
  if (!username.value.trim()) { errorMessage.value = '请填写用户名'; return }
  if (password.value.length < 6) { errorMessage.value = '密码长度不能少于 6 位'; return }
  if (password.value !== passwordConfirm.value) { errorMessage.value = '两次输入的密码不一致'; return }
  submitting.value = true
  try {
    const { data } = await api.post('/api/user/account/register/', { username: username.value.trim(), password: password.value, password_confirm: passwordConfirm.value })
    if (data.result === 'success') {
      user.setAccessToken(data.access)
      user.setUserInfo(data)
      const target = route.query.redirect
      await router.push(typeof target === 'string' && target.startsWith('/') && !target.startsWith('//') && !/^\/(login|register)(\/|\?|$)/.test(target) ? target : { name: 'homepage-index' })
    } else { errorMessage.value = data.result || '注册失败，请稍后重试' }
  } catch (error) {
    if (error.response) {
      errorMessage.value = error.response.data?.result ||
        (error.response.status === 401 ? '身份验证失败，请重新输入账号和密码' : '服务暂时异常，请稍后重试')
    } else {errorMessage.value = '暂时无法连接，请确认后台服务已启动后重试'}
  }
  finally { submitting.value = false }
}
</script>
<template>
  <AuthLayout register><form @submit.prevent="handleRegister" class="auth-form" :aria-busy="submitting">
    <div class="form-field"><label for="register-username">用户名</label><input id="register-username" v-model="username" autocomplete="username" placeholder="给自己取个名字" required :disabled="submitting" /></div>
    <div class="form-field"><label for="register-password">设置密码</label><div class="password-field"><input id="register-password" v-model="password" :type="showPassword ? 'text' : 'password'" autocomplete="new-password" minlength="6" aria-describedby="password-hint" placeholder="至少 6 位字符" required :disabled="submitting" /><button type="button" @click="showPassword = !showPassword" :aria-pressed="showPassword" :aria-label="showPassword ? '隐藏密码' : '显示密码'">{{ showPassword ? '隐藏' : '显示' }}</button></div><span id="password-hint" class="field-hint">建议组合使用字母、数字和符号。</span></div>
    <div class="form-field"><label for="register-confirm">确认密码</label><input id="register-confirm" v-model="passwordConfirm" :type="showPassword ? 'text' : 'password'" autocomplete="new-password" placeholder="再次输入密码" required :disabled="submitting" /></div>
    <p v-if="errorMessage" class="form-error" role="alert">{{ errorMessage }}</p>
    <button type="submit" class="primary-button auth-submit" :disabled="submitting">{{ submitting ? '正在创建…' : '创建账号' }}<span v-if="!submitting">→</span></button>
    <p class="auth-switch">已经有账号？ <RouterLink :to="{ name: 'user-account-login-index', query: route.query.redirect ? { redirect: route.query.redirect } : {} }">去登录</RouterLink></p>
  </form></AuthLayout>
</template>

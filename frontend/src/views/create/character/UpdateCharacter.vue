<script setup>
import Photo from "@/views/create/character/components/Photo.vue";
import Name from "@/views/create/character/components/Name.vue";
import Profile from "@/views/create/character/components/Profile.vue";
import BackgroundImage from "@/views/create/character/components/BackgroundImage.vue";
import {onMounted, ref, useTemplateRef} from "vue";
import {base64ToFile} from "@/js/utils/base64_to_file.js";
import api from "@/js/http/api.js";
import {useRoute, useRouter} from "vue-router";
import {useUserStore} from "@/stores/user.js";
import Voice from "@/views/create/character/components/Voice.vue";

import PublishSettings from '@/views/create/character/components/PublishSettings.vue'
const publishRef = useTemplateRef('publish-ref')
const user = useUserStore()
const router = useRouter()
const route = useRoute()
const characterId = route.params.character_id
const character = ref(null)

const voices = ref([])
const curVoiceId = ref(null)

onMounted(async () => {
  try {
    const res = await api.get('/api/create/character/get_single/', {
      params: {
        character_id: characterId,
      }
    })
    const data = res.data
    if (data.result === 'success') {
      character.value = data.character
      voices.value = data.voices
      curVoiceId.value = data.character.voice_id
    } else {
      errorMessage.value = data.result || '角色加载失败'
    }
  } catch (err) {
    errorMessage.value = '角色加载失败，请刷新重试'
  }
})

const photoRef = useTemplateRef('photo-ref')
const nameRef = useTemplateRef('name-ref')
const voiceRef = useTemplateRef('voice-ref')
const profileRef = useTemplateRef('profile-ref')
const backgroundImageRef = useTemplateRef('background-image-ref')
const errorMessage = ref('')
const submitting = ref(false)
const successMessage = ref('')
let saved = false

import {useEditorGuard} from '@/js/utils/editor_guard.js'
function hasUnsavedChanges() {
  if(saved || !character.value || !nameRef.value) return false
  const c=character.value
  return nameRef.value.myName!==c.name || profileRef.value.myProfile!==(c.persona_prompt || c.profile) ||
    photoRef.value.myPhoto!==c.photo || backgroundImageRef.value.myBackgroundImage!==c.background_image ||
    voiceRef.value.myVoice!==c.voice_id || publishRef.value.description!==c.public_description ||
    publishRef.value.visibility!==c.visibility || publishRef.value.status!==(c.status==='published' ? 'published' : 'draft')
}
useEditorGuard(hasUnsavedChanges)

async function handleUpdate() {
  if (submitting.value) return
  successMessage.value = ''
  const photo = photoRef.value.myPhoto
  const name = nameRef.value.myName?.trim()
  const voice = voiceRef.value.myVoice
  const profile = profileRef.value.myProfile?.trim()
  const backgroundImage = backgroundImageRef.value.myBackgroundImage

  errorMessage.value = ''
  if (!photo) {
    errorMessage.value = '头像不能为空'
  } else if (!name) {
    errorMessage.value = '名字不能为空'
  } else if (publishRef.value.status === 'published' && publishRef.value.visibility === 'public' && !publishRef.value.description.trim()) {
    errorMessage.value = '公开发布需要填写公开简介'
  } else if (!profile) {
    errorMessage.value = '角色介绍不能为空'
  } else if (!backgroundImage) {
    errorMessage.value = '聊天背景不能为空'
  } else {
    submitting.value = true
    const formData = new FormData()
    formData.append('character_id', characterId)
    formData.append('version', character.value.version)
    formData.append('name', name)
    formData.append('voice_id', voice ?? 'none')
    formData.append('public_description', publishRef.value.description.trim())
    formData.append('persona_prompt', profile)
    formData.append('visibility', publishRef.value.visibility)
    formData.append('status', publishRef.value.status)
    formData.append('profile', profile)
    if (photo !== character.value.photo) {
      formData.append('photo', base64ToFile(photo, 'photo.png'))
    }

    if (backgroundImage !== character.value.background_image) {
      formData.append('background_image', base64ToFile(backgroundImage, 'background_image.png'))
    }

    try {
      const res = await api.post('/api/create/character/update/', formData)
      const data = res.data
      if (data.result === 'success') {
        saved=true
        await router.push({
          name: 'user-space-index',
          params: {
            user_id: user.id,
          }
        })
      } else {
        errorMessage.value = data.result
      }
    } catch (err) {
      errorMessage.value = err.response?.data?.result || '暂时无法连接，请稍后重试'
    } finally {
      submitting.value = false
    }
  }
}
</script>

<template>
  <p v-if="!character && errorMessage" class="form-error" role="alert">{{ errorMessage }}</p>
  <p v-else-if="!character" role="status">正在加载角色…</p>
  <div v-if="character" class="flex justify-center">
    <div class="card editor-card">
      <div class="card-body">
        <h3 class="text-lg font-bold my-4">更新角色</h3>
        <p v-if="character.moderation_reason" class="form-error">审核反馈：{{character.moderation_reason}}</p>
        <Photo ref="photo-ref" :photo="character.photo" />
        <Name ref="name-ref" :name="character.name" />
        <Voice ref="voice-ref" :voices="voices" :curVoiceId="curVoiceId" />
        <Profile ref="profile-ref" :profile="character.persona_prompt || character.profile" />
        <BackgroundImage ref="background-image-ref" :backgroundImage="character.background_image" />

        <PublishSettings ref="publish-ref" :character="character" />

        <p v-if="errorMessage" class="form-error" role="alert">{{ errorMessage }}</p>

        <div class="flex justify-center">
          <button @click="handleUpdate" class="btn btn-neutral editor-submit" :disabled="submitting">更新</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
</style>

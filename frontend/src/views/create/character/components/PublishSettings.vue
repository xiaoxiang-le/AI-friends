<script setup>
import {ref, watch} from 'vue'
const props = defineProps(['character'])
const description = ref(props.character?.public_description || '')
const visibility = ref(props.character?.visibility || 'private')
const status = ref(props.character?.status === 'published' ? 'published' : 'draft')
watch(() => props.character, c => {
  if (c) {description.value = c.public_description || ''; visibility.value = c.visibility; status.value = c.status === 'published' ? 'published' : 'draft'}
})
defineExpose({description, visibility, status})
</script>
<template>
  <fieldset class="fieldset w-full">
    <legend class="label text-base">发布设置</legend>
    <label for="public-description">公开简介（最多200字，不包含内部角色设定）</label>
    <textarea id="public-description" v-model="description" class="textarea w-full" maxlength="200" rows="3" />
    <label for="character-status">保存方式</label>
    <select id="character-status" v-model="status" class="select w-full"><option value="draft">保存草稿</option><option value="published">发布角色</option></select>
    <label for="character-visibility">谁可以看到</label>
    <select id="character-visibility" v-model="visibility" class="select w-full"><option value="private">仅自己</option><option value="unlisted">不在发现页展示（已有访问入口可聊天）</option><option value="public">公开展示</option></select>
    <p class="text-sm text-gray-500">草稿仅自己可见；公开发布后才进入发现页。归档可恢复，聊天历史保留。</p>
  </fieldset>
</template>

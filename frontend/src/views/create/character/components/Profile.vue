<script setup>
import {ref, watch} from "vue";

const props = defineProps(['profile'])
const myProfile = ref(props.profile)

watch(() => props.profile, newVal => {
  myProfile.value = newVal
})

defineExpose({
  myProfile,
})
</script>

<template>
  <fieldset class="fieldset">
    <label for="character-profile" class="label text-base">角色设定（仅用于 AI 对话）</label>
    <textarea id="character-profile" v-model="myProfile" rows="6" class="textarea w-full"></textarea>
  </fieldset>
</template>

<style scoped>

</style>
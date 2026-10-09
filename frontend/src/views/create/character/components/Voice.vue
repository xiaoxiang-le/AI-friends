<script setup>
import {ref, watch} from "vue";

const props = defineProps(['voices', 'curVoiceId'])
const myVoice = ref(props.curVoiceId)

watch(() => props.curVoiceId, newVal => {
  myVoice.value = newVal
})

defineExpose({
  myVoice,
})
</script>

<template>
  <fieldset class="fieldset">
    <label for="character-voice" class="label text-base">音色</label>
    <select id="character-voice" v-model="myVoice" class="select w-full" :disabled="!voices?.length">
      <option v-if="!voices?.length" :value="null">暂无可用音色</option>
      <option
          v-for="voice in voices"
          :key="voice.id"
          :value="voice.id"
      >{{ voice.name }}</option>
    </select>
  </fieldset>
</template>

<style scoped>

</style>

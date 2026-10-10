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
  <fieldset class="fieldset voice-picker">
    <legend class="label text-base">角色音色</legend>
    <p class="voice-hint">选择角色的声音，试听后再决定。</p>
    <div class="voice-grid">
      <div v-for="voice in voices" :key="voice.id" class="voice-option" :class="{'is-selected':myVoice === voice.id}">
        <label :for="`voice-${voice.id}`" class="voice-choice">
          <input :id="`voice-${voice.id}`" v-model="myVoice" type="radio" name="character-voice" :value="voice.id">
          <span><strong>{{ voice.name }}</strong><small>{{ voice.description || '自定义音色' }}</small></span>
        </label>
      </div>
    </div>
    <p v-if="!voices?.length" class="voice-hint">暂无可用音色，请联系管理员。</p>
  </fieldset>
</template>

<style scoped>
.voice-picker {min-width:0}.voice-hint {color:#8a929e;font-size:12px;margin:0 0 8px}
.voice-grid {display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:9px}
.voice-option {display:flex;align-items:center;gap:5px;border:1px solid #e5e9f0;border-radius:13px;padding:11px;background:#fff;transition:border-color .15s,background .15s}
.voice-option.is-selected {border-color:#77aaff;background:#f1f6ff}.voice-choice {display:flex;align-items:center;gap:8px;min-width:0;flex:1;cursor:pointer}
.voice-choice input {accent-color:#1877f2}.voice-choice strong {display:block;font-size:13px;color:#243246}.voice-choice small {display:block;font-size:11px;color:#8a929e;margin-top:3px}
.preview-button {flex-shrink:0;border:0;background:#eaf1ff;color:#246bc4;border-radius:8px;padding:6px 9px;font-size:12px;cursor:pointer}.preview-button:hover {background:#dce9ff}
.voice-error {font-size:12px;color:#ae3333;background:#fff0f0;padding:7px;border-radius:8px}
@media(max-width:480px) {.voice-grid {grid-template-columns:1fr}}
</style>

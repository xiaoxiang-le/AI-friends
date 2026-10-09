<script setup>
import {ref, watch} from "vue";

const props = defineProps(['name'])
const myName = ref(props.name)

watch(() => props.name, newVal => {
  myName.value = newVal
})

defineExpose({
  myName,
})
</script>

<template>
  <fieldset class="fieldset">
    <label for="character-name" class="label text-base">名字</label>
    <input id="character-name" maxlength="50" v-model="myName" type="text" class="input w-full">
  </fieldset>
</template>

<style scoped>

</style>
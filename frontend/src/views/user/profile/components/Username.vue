<script setup>
import { ref, watch } from "vue";

const props = defineProps(["username"]);
const emit = defineEmits(["update:username"]);
const myUsername = ref(props.username);

watch(
  () => props.username,
  (newValue) => {
    myUsername.value = newValue;
  }
);
watch(myUsername, (newValue) => {
  emit("update:username", newValue);
});

defineExpose(
    {myUsername}
)
</script>

<template>
  <fieldset class="fieldset">
    <label for="profile-username" class="label text-base">用户名</label>
    <input id="profile-username" maxlength="150" v-model="myUsername" type="text" class="input w-full"/>
  </fieldset>
</template>

<style scoped>

</style>
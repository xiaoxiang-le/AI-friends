<script setup>
import { ref, watch } from "vue";

const props = defineProps(["profile"]);
const emit = defineEmits(["update:profile"]);
const myProfile = ref(props.profile);

watch(
  () => props.profile,
  (newValue) => {
    myProfile.value = newValue;
  }
);
watch(myProfile, (newValue) => {
  emit("update:profile", newValue);
});

defineExpose({
  myProfile
})
</script>

<template>
  <fieldset class="fieldset">
    <label for="profile-description" class="label text-base">简介</label>
    <textarea id="profile-description" maxlength="500" v-model="myProfile" rows="6" class="textarea w-full"></textarea>
  </fieldset>
</template>

<style scoped>

</style>
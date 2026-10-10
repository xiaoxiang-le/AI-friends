<script setup>
import { ref, watch, computed, nextTick, onBeforeUnmount } from "vue";
import { BASE_URL } from "@/js/http/api.js";
import CameraIcon from "@/views/user/profile/components/icon/CameraIcon.vue";
import Croppie from "croppie";
import "croppie/croppie.css";

const props = defineProps(["photo"]);
const myPhoto = ref(props.photo);

const fileInputRef = ref(null);
const modalRef = ref(null);
const croppieRef = ref(null);
let croppie = null
const uploadError = ref('');

async function openModal(photo) {
  if (!modalRef.value) return;
  modalRef.value.showModal();
  await nextTick();
  await new Promise((r) => setTimeout(r, 50));

  const container = croppieRef.value;
  if (!container) return;

  if (croppie) {
    croppie.destroy();
    croppie = null;
  }
  container.innerHTML = "";
  // 每次用新创建的 div 传给 Croppie，避免 "Can't initialize croppie more than once"
  const wrapper = document.createElement("div");
  wrapper.className = "croppie-wrapper";
  wrapper.style.width = "300px";
  wrapper.style.height = "300px";
  container.appendChild(wrapper);
  croppie = new Croppie(wrapper, {
    viewport: { width: 200, height: 200, type: "square" },
    boundary: { width: 300, height: 300 },
    enableOrientation: true,
    enforceBoundary: true,
  });
  croppie.bind({ url: photo });
}

async function crop() {
  if (!croppie) return;

  // 与 yxc demo 一致：输出 base64，ProfileIndex 用 base64ToFile(photo) 上传
  myPhoto.value = await croppie.result({ type: "base64", size: "viewport" });
  modalRef.value.close();
}

function onFileChange(e) {
  const file = e.target.files?.[0];
  e.target.value = "";
  if (!file || !file.type.startsWith("image/")) return;

  const reader = new FileReader();
  reader.onerror = () => {
    console.error("读取图片失败");
  };
  reader.onload = () => {
    const dataUrl = reader.result;
    if (dataUrl) openModal(dataUrl);
  };
  reader.onerror=() => {uploadError.value='图片读取失败，请重试'}
  reader.readAsDataURL(file);
}

watch(
  () => props.photo,
  (newValue) => {
    myPhoto.value = newValue;
  }
);

// 开发环境下后端返回 /media/... 相对路径，需拼上后端地址；data: 为裁剪后的 base64
const photoUrl = computed(() => {
  const p = myPhoto.value;
  if (!p) return "";
  if (typeof p === "string" && (p.startsWith("http") || p.startsWith("blob:") || p.startsWith("data:"))) return p;
  return BASE_URL ? BASE_URL + p : p;
});

onBeforeUnmount(() => {
  croppie?.destroy();
  croppie = null;
});

defineExpose({
  myPhoto,
})
</script>

<template>
  <p v-if="uploadError" class="form-error" role="alert">{{uploadError}}</p>
  <div class="flex justify-center w-full">
    <div class="avatar relative">
      <div class="w-28 rounded-full">
        <img :src="photoUrl" alt="" />
      </div>
      <button type="button" aria-label="上传个人头像" @click="fileInputRef?.click()" class="absolute left-0 top-0 w-28 h-28 flex justify-center items-center bg-black/20 rounded-full cursor-pointer">
        <CameraIcon />
      </button>
    </div>
  </div>

  <input ref="fileInputRef" type="file" accept="image/*" class="hidden" @change="onFileChange" />

  <dialog ref="modalRef" class="modal">
    <div class="modal-box transition-none">
      <button type="button" @click="modalRef?.close()" class="btn btn-circle btn-sm btn-ghost absolute right-2 top-2">✕</button>

      <div ref="croppieRef" class="croppie-container my-4"></div>

      <div class="modal-action">
        <button type="button" @click="modalRef?.close()" class="btn">取消</button>
        <button type="button" @click="crop" class="btn btn-neutral">确定</button>
      </div>
    </div>
  </dialog>
</template>

<style scoped>
.croppie-container {
  width: 300px;
  height: 300px;
  margin: 0 auto;
}
</style>
<script setup>
import {nextTick, onBeforeUnmount, ref, useTemplateRef, watch} from "vue";
import { resolveMediaUrl } from "@/js/http/api.js";
import CameraIcon from "@/views/user/profile/components/icon/CameraIcon.vue";
import Croppie from "croppie";

const props = defineProps(['backgroundImage'])
const myBackgroundImage = ref(props.backgroundImage)

watch(() => props.backgroundImage, newVal => {
  myBackgroundImage.value = newVal
})

const fileInputRef = useTemplateRef('file-input-ref')
const modalRef = useTemplateRef('modal-ref')
const croppieRef = useTemplateRef('croppie-ref')
let croppie = null
const uploadError = ref('')

async function openModal(photo) {
  modalRef.value.showModal()
  await nextTick()

  if (!croppie) {
    croppie = new Croppie(croppieRef.value, {
      viewport: {width: Math.min(260, window.innerWidth - 116), height: Math.min(430, (window.innerWidth - 116) * 5 / 3)},
      boundary: {width: Math.min(600, window.innerWidth - 96), height: 540},
      enableOrientation: true,
      enforceBoundary: true,
    })
  }

  await croppie.bind({
    url: photo,
  })
}

async function crop() {
  if (!croppie) return

  myBackgroundImage.value = await croppie.result({
    type: 'base64',
    size: 'viewport',
  })

  modalRef.value.close()
}

function onFileChange(e) {
  const file = e.target.files[0]
  e.target.value = ''
  uploadError.value=''
  if(!file) return
  if(!['image/jpeg','image/png','image/webp'].includes(file.type) || file.size>5*1024*1024) {uploadError.value='请选择5MB以内的 JPEG、PNG 或 WebP 图片';return}

  const reader = new FileReader()
  reader.onload = () => {
    openModal(reader.result).catch(() => {uploadError.value='图片无法读取，请更换文件';modalRef.value?.close()})
  }
  reader.onerror=() => {uploadError.value='图片读取失败，请重试'}
  reader.readAsDataURL(file)
}

onBeforeUnmount(() => {
  croppie?.destroy()
})

defineExpose({
  myBackgroundImage,
})
</script>

<template>
  <p v-if="uploadError" class="form-error" role="alert">{{uploadError}}</p>
  <fieldset class="fieldset">
    <label class="label text-base">聊天背景</label>
    <div class="avatar relative">
      <div v-if="myBackgroundImage" class="w-15 h-25 rounded-box">
        <img :src="myBackgroundImage?.startsWith('data:') ? myBackgroundImage : resolveMediaUrl(myBackgroundImage)" alt="">
      </div>
      <div v-else class="w-15 h-25 rounded-box bg-base-200"></div>
      <button type="button" aria-label="上传聊天背景" @click="fileInputRef.click()" class="w-15 h-25 rounded-box absolute left-0 top-0 bg-black/20 flex justify-center items-center cursor-pointer">
        <CameraIcon />
      </button>
    </div>
  </fieldset>

  <input aria-label="上传聊天背景" ref="file-input-ref" type="file" class="hidden" accept="image/*" @change="onFileChange">

  <dialog ref="modal-ref" class="modal">
    <div class="modal-box transition-none max-w-2xl">
      <button type="button" @click="modalRef.close()" class="btn btn-sm btn-circle btn-ghost absolute right-2 top-2">✕</button>

      <div ref="croppie-ref" class="flex flex-col my-4"></div>

      <div class="modal-action">
        <button type="button" @click="modalRef.close()" class="btn">取消</button>
        <button type="button" @click="crop" class="btn btn-neutral">确定</button>
      </div>
    </div>
  </dialog>
</template>

<style scoped>
</style>

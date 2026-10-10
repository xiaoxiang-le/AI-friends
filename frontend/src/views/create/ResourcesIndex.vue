<script setup>
import {onMounted, ref, onBeforeUnmount, watch} from 'vue'
import api from '@/js/http/api.js'
import {useUserStore} from '@/stores/user.js'
const characters=ref([]), characterId=ref(''), documents=ref([]), voices=ref([]), jobs=ref([]), reports=ref([])
const message=ref(''), busy=ref(false), voiceName=ref(''), authorized=ref(false), sample=ref(null)
const user=useUserStore()
let timer=null, disposed=false, initialized=false
const labels={queued:'排队中', running:'处理中', completed:'已完成', failed:'失败', cancelled:'已取消', uploaded:'已上传', processing:'处理中', ready:'可用', preparing:'准备中', deleting:'删除中', pending:'待处理', resolved:'已处理', rejected:'不成立'}
async function refresh() {
  try {
    const [v,j,r] = await Promise.all([api.get('/api/voices/custom/'),api.get('/api/jobs/'),api.get('/api/reports/')])
    if(disposed) return
    voices.value=v.data.voices; jobs.value=j.data.jobs; reports.value=r.data.reports
    await loadDocuments()
  } catch(e) {message.value=e.response?.data?.result || '资源加载失败，请刷新重试'}
}
async function loadDocuments() {
  if(!characterId.value) {documents.value=[]; return}
  const id=characterId.value
  const {data}=await api.get('/api/knowledge/documents/', {params:{character_id:id}})
  if(!disposed && characterId.value===id) documents.value=data.documents
}
async function action(task, success) {
  if(busy.value) return
  busy.value=true; message.value=''
  try {await task(); message.value=success; await refresh()}
  catch(e) {message.value=e.response?.data?.result || '操作失败，请稍后重试'}
  finally {busy.value=false}
}
async function uploadKnowledge(event) {
  const file=event.target.files[0]; if(!file) return
  const data=new FormData(); data.append('file',file); data.append('character_id',characterId.value)
  await action(() => api.post('/api/knowledge/documents/', data), '文件已提交，处理状态会自动更新。')
  event.target.value=''
}
async function cloneVoice() {
  if(!sample.value || !authorized.value) {message.value='请选择样本并确认使用授权';return}
  const data=new FormData(); data.append('sample',sample.value); data.append('name',voiceName.value); data.append('authorized','true')
  await action(() => api.post('/api/voices/custom/',data), '复刻任务已提交，完成后可在角色编辑页面试听和选择。')
}
async function initialize() {
  if(!user.isLogin() || initialized || disposed) return
  initialized=true
  try {
    let offset=0
    while(true) {
      const {data}=await api.get('/api/create/character/get_list/', {params:{user_id:user.id,items_count:offset}})
      if(disposed) return
      characters.value.push(...data.characters)
      if(data.characters.length<20) break
      offset+=20
    }
    characterId.value=characters.value[0]?.id || ''
    await refresh()
    timer=setInterval(() => {if(!busy.value) refresh()},5000)
  } catch(e) {initialized=false;message.value=e.response?.data?.result || '资源加载失败'}
}
onMounted(initialize)
watch(() => user.id, id => {if(id) initialize()})
onBeforeUnmount(() => {disposed=true;clearInterval(timer)})
</script>
<template>
  <div class="resource-page">
    <RouterLink :to="{name:'create-index'}" class="soft-button">返回创作中心</RouterLink>
    <h1 class="text-2xl font-bold">创作资源</h1>
    <p v-if="message" role="status" class="resource-notice">{{message}}</p>
    <section class="panel p-5">
      <h2 class="text-lg font-bold">角色知识文件</h2>
      <p>TXT / Markdown，UTF-8 编码，单份最多1MB和20万字。仅用于关联角色的检索，最多20份。</p>
      <p>角色会在回答中引用这些资料；公开角色的资料请选择可以向聊天用户披露的内容。</p>
      <label for="knowledge-character">关联角色</label>
      <select id="knowledge-character" v-model="characterId" class="select w-full" @change="loadDocuments"><option v-for="c in characters" :key="c.id" :value="c.id">{{c.name}}</option></select>
      <label for="knowledge-file">上传知识文件</label>
      <input id="knowledge-file" type="file" accept=".txt,.md" :disabled="!characterId || busy" @change="uploadKnowledge">
      <p v-if="!characters.length">请先创建一个角色。</p>
      <div v-for="doc in documents" :key="doc.id" class="resource-row"><span>{{doc.name}} · {{labels[doc.status] || doc.status}} · {{doc.index_mode==='hybrid' ? '语义与关键词检索' : '关键词检索'}}<small v-if="doc.error">{{doc.error}}</small></span><button class="soft-button" :disabled="busy" @click="action(() => api.delete('/api/knowledge/documents/',{data:{document_id:doc.id}}),'知识文件已删除')">删除</button></div>
      <p v-if="characterId && !documents.length">暂无知识文件。</p>
    </section>
    <section class="panel p-5">
      <h2 class="text-lg font-bold">个人音色复刻</h2>
      <p>上传你有权使用的10至20秒 WAV 样本：单声道、16位 PCM、至少16kHz，最多10MB。供应商收到样本用于复刻，样本通过限时地址传递。</p>
      <label for="custom-voice-name">音色名字</label><input id="custom-voice-name" v-model="voiceName" maxlength="50" class="input w-full">
      <label for="voice-sample-file">声音样本</label><input id="voice-sample-file" type="file" accept=".wav,audio/wav" @change="sample=$event.target.files[0]">
      <label class="flex gap-2"><input v-model="authorized" type="checkbox">我确认拥有此声音样本的使用授权</label>
      <button class="soft-button" :disabled="busy || !voiceName.trim() || !authorized || !sample" @click="cloneVoice">提交复刻</button>
      <div v-for="voice in voices" :key="voice.id" class="resource-row"><span>{{voice.name}} · {{labels[voice.status] || voice.status}}<small>{{voice.error}}</small></span><button class="soft-button" :disabled="busy || ['preparing','deleting'].includes(voice.status)" @click="action(() => api.delete('/api/voices/custom/',{data:{voice_id:voice.id}}),'音色删除任务已提交')">删除</button></div>
    </section>
    <section class="panel p-5">
      <h2 class="text-lg font-bold">后台任务</h2><p>状态每5秒刷新。失败任务最多尝试3次；提交结果不确定的音色复刻由管理员核对，避免重复创建。</p>
      <div v-for="job in jobs" :key="job.id" class="resource-row"><span>#{{job.id}} {{ {knowledge:'知识处理',voice:'音色复刻',voice_delete:'音色删除',memory:'记忆摘要'}[job.kind] }} · {{labels[job.status] || job.status}}<small>{{job.error}}</small></span><button v-if="job.retryable" class="soft-button" :disabled="busy" @click="action(() => api.post('/api/jobs/',{job_id:job.id}),'任务已重新排队')">重试</button></div>
      <p v-if="!jobs.length">暂无任务。</p>
    </section>
    <section class="panel p-5"><h2 class="text-lg font-bold">我的举报反馈</h2><div v-for="report in reports" :key="report.id" class="resource-row"><span>{{report.character_name}} · {{labels[report.status]}}<small>{{report.resolution || '等待管理员处理'}}</small></span></div><p v-if="!reports.length">暂无举报记录。</p></section>
  </div>
</template>
<style scoped>
.resource-page {display:flex;flex-direction:column;gap:20px;max-width:800px;margin:auto}.resource-page section {display:flex;flex-direction:column;gap:12px}.resource-page p {font-size:14px;color:#64748b}.resource-row {display:flex;align-items:center;justify-content:space-between;gap:12px;border-top:1px solid #edf0f3;padding:12px 0;overflow-wrap:anywhere}.resource-row span {min-width:0}.resource-row small {display:block;color:#64748b}.resource-notice {padding:12px;background:#fff;border-radius:10px}.resource-page input[type=file] {max-width:100%}
</style>

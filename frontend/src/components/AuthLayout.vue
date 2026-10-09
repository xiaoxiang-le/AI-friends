<script setup>
defineProps({ register: Boolean })
</script>
<template>
  <div class="auth-page">
    <header class="auth-header"><RouterLink :to="{ name: 'homepage-index' }" class="brand"><span class="brand-symbol">af<span></span></span>AIFriends</RouterLink><RouterLink :to="{ name: 'homepage-index' }" class="text-button">先逛逛社区 <span>↗</span></RouterLink></header>
    <main class="auth-main">
      <section class="auth-intro">
        <div class="eyebrow"><span class="blue-dot"></span> 每段故事，从一句你好开始</div>
        <h1>遇见有趣的灵魂，<br /><span>打开新的世界。</span></h1>
        <p>在 AIFriends，发现与你同频的 AI 角色。<br />分享想象，畅聊日常，让灵感有个回应。</p>
        <div class="connection-art" aria-hidden="true"><div class="art-orbit"></div><span class="art-avatar art-one">☀</span><span class="art-avatar art-two">✦</span><span class="art-avatar art-three">☺</span><span class="art-avatar art-four">☾</span><div class="art-bubble">你好，很高兴认识你 <span>✧</span></div><div class="art-bubble secondary">今天，想聊些什么？</div></div>
        <div class="auth-features"><span>✦ 自定义角色</span><span>◉ 语音交流</span><span>♡ 持续陪伴</span></div>
      </section>
      <section class="auth-form-column"><div class="auth-card"><div class="auth-card-heading"><span class="eyebrow">{{ register ? '开启新的连接' : '继续你的故事' }}</span><h2>{{ register ? '创建你的账号' : '欢迎回来' }}</h2><p>{{ register ? '几步之后，就能遇见你的 AI 好友。' : '登录 AIFriends，和你的好友说声你好。' }}</p></div><slot /></div><p class="auth-card-caption">为每一种想象，留一个相遇的地方。</p></section>
    </main>
    <footer class="auth-footer"><span>AIFriends · AI 角色社区</span><span>发现 · 连接 · 创造</span></footer>
  </div>
</template>

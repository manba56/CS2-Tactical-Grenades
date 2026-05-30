<script setup lang="ts">
import { onMounted } from 'vue';
import { useHead } from '../composables/useHead';

onMounted(() => {
  useHead('404 页面不存在', '你访问的页面不存在，请检查链接或返回首页');
});
</script>

<template>
  <div class="empty-card" style="text-align:center;padding:80px 20px">
    <h1 style="font-size:4rem;margin:0;color:#ff7a18">404</h1>
    <p class="section-intro">你访问的页面不存在</p>
    <router-link class="primary-button" to="/">返回首页</router-link>
  </div>
</template>

<script setup lang="ts">
import TopNav from './components/TopNav.vue';
import BottomNav from './components/BottomNav.vue';
import BackToTop from './components/BackToTop.vue';
</script>

<template>
  <a href="#main-content" class="skip-link">跳到主要内容</a>
  <div class="app-shell">
    <TopNav />
    <main id="main-content" class="page-shell" tabindex="-1">
      <router-view />
    </main>
    <BottomNav />
    <BackToTop />
  </div>
</template>

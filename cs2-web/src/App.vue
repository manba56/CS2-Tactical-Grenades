<script setup lang="ts">
import TopNav from './components/TopNav.vue';
import BottomNav from './components/BottomNav.vue';
import BackToTop from './components/BackToTop.vue';
</script>

<template>
  <div class="app-shell">
    <TopNav />
    <main class="page-shell">
      <router-view />
    </main>
    <BottomNav />
    <BackToTop />
  </div>
</template>

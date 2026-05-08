<script setup lang="ts">
import TopNav from './components/TopNav.vue';
</script>

<template>
  <div class="app-shell">
    <TopNav />
    <main class="page-shell">
      <router-view />
    </main>
  </div>
</template>

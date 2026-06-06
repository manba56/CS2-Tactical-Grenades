<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue';

const visible = ref(false);

function onScroll() {
  visible.value = window.scrollY > 400;
}

let ticking = false;
function throttledScroll() {
  if (!ticking) {
    requestAnimationFrame(() => {
      onScroll();
      ticking = false;
    });
    ticking = true;
  }
}

function scrollTop() {
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

onMounted(() => window.addEventListener('scroll', throttledScroll, { passive: true }));
onUnmounted(() => window.removeEventListener('scroll', throttledScroll));
</script>

<template>
  <button
    v-show="visible"
    class="back-to-top"
    @click="scrollTop"
    aria-label="回到顶部"
  >
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polyline points="18 15 12 9 6 15"/></svg>
  </button>
</template>

<style scoped>
.back-to-top {
  position: fixed;
  bottom: 80px;
  right: 20px;
  z-index: 40;
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: rgba(255, 122, 24, 0.85);
  border: none;
  color: #fff;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 16px rgba(255, 122, 24, 0.3);
  transition: opacity 0.3s, transform 0.3s;
  opacity: 0.9;
}
.back-to-top:hover {
  opacity: 1;
  transform: scale(1.1);
}
@media (max-width: 640px) {
  .back-to-top {
    bottom: 90px;
    right: 12px;
  }
}
</style>

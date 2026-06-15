<script setup lang="ts">
import TopNav from './components/TopNav.vue';
import BottomNav from './components/BottomNav.vue';
import BackToTop from './components/BackToTop.vue';
import { useI18n } from './composables/useI18n';

const { t } = useI18n();
</script>

<template>
  <a href="#main-content" class="skip-link">{{ t('skipToMain') }}</a>
  <div class="app-shell">
    <TopNav />
    <main id="main-content" class="page-shell" tabindex="-1">
      <router-view />
    </main>
    <BottomNav />
    <BackToTop />
  </div>
</template>

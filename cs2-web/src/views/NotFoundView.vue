<script setup lang="ts">
import { onMounted } from 'vue';
import { useHead } from '../composables/useHead';
import { useI18n } from '../composables/useI18n';

const { t } = useI18n();

onMounted(() => {
  useHead(`404 ${t('notFoundTitle')}`, t('notFoundDescription'));
});
</script>

<template>
  <div class="empty-card" style="text-align:center;padding:80px 20px">
    <h1 style="font-size:4rem;margin:0;color:#ff7a18">404</h1>
    <p class="section-intro">{{ t('notFoundDescription') }}</p>
    <router-link class="primary-button" to="/">{{ t('backHome') }}</router-link>
  </div>
</template>

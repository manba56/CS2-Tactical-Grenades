<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { useRoute } from 'vue-router';

import { api } from '../api';
import TacticCard from '../components/TacticCard.vue';
import type { CollectionDetail } from '../types';

const route = useRoute();
const collection = ref<CollectionDetail | null>(null);
const error = ref('');

onMounted(async () => {
  try {
    collection.value = await api.getCollection(route.params.slug as string);
  } catch (err) {
    error.value = err instanceof Error ? err.message : '加载失败';
  }
});
</script>

<template>
  <section v-if="error" class="empty-card danger">{{ error }}</section>
  <template v-else-if="collection">
    <div class="section-heading">
      <div>
        <div class="kicker">Tactic Collection</div>
        <h1>{{ collection.title }}</h1>
      </div>
      <p class="section-intro">{{ collection.description }}</p>
    </div>

    <section class="section-block">
      <div class="section-heading">
        <h2>包含战术</h2>
        <span class="muted">{{ collection.tactics.length }} 条</span>
      </div>
      <div class="card-grid">
        <TacticCard v-for="t in collection.tactics" :key="t.id" :tactic="t" />
      </div>
    </section>
  </template>
</template>

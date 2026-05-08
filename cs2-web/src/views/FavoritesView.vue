<script setup lang="ts">
import { onMounted, ref } from 'vue';

import { api } from '../api';
import TacticCard from '../components/TacticCard.vue';
import { useSessionStore } from '../stores/session';
import type { FavoriteBundle } from '../types';

const session = useSessionStore();
const bundle = ref<FavoriteBundle | null>(null);
const error = ref('');

onMounted(async () => {
  try {
    bundle.value = await api.getFavorites(session.token);
  } catch (err) {
    error.value = err instanceof Error ? err.message : '加载失败';
  }
});
</script>

<template>
  <section class="section-heading">
    <div>
      <div class="kicker">Personal Shelf</div>
      <h1>收藏与最近浏览</h1>
    </div>
    <p class="section-intro">首版只做最关键的两个能力：快速回看和战术沉淀。</p>
  </section>

  <section v-if="error" class="empty-card danger">{{ error }}</section>

  <template v-else-if="bundle">
    <section class="section-block favorite-bundle">
      <div class="section-heading">
        <h2>我的收藏</h2>
        <span class="muted">{{ bundle.favorites.length }} 条</span>
      </div>
      <div v-if="bundle.favorites.length" class="favorites-grid">
        <TacticCard v-for="item in bundle.favorites" :key="item.id" :tactic="item" />
      </div>
      <div v-else class="empty-card">你还没有收藏战术，可以先去地图页挑一套顺手的执行。</div>
    </section>

    <section class="section-block favorite-bundle">
      <div class="section-heading">
        <h2>最近浏览</h2>
        <span class="muted">{{ bundle.recent.length }} 条</span>
      </div>
      <div v-if="bundle.recent.length" class="favorites-grid">
        <TacticCard v-for="item in bundle.recent" :key="item.id" :tactic="item" />
      </div>
      <div v-else class="empty-card">最近还没有浏览记录。</div>
    </section>
  </template>
</template>

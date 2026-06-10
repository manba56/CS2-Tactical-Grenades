<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';

import { api } from '../api';
import { useHead } from '../composables/useHead';
import TacticCard from '../components/TacticCard.vue';
import { useSessionStore } from '../stores/session';
import type { FavoriteBundle } from '../types';

const session = useSessionStore();
const bundle = ref<FavoriteBundle | null>(null);
const error = ref('');
const filterMap = ref('');
const filterSide = ref('');
const filterUtility = ref('');

const allPersonalTactics = computed(() => {
  if (!bundle.value) return [];
  const seen = new Set<number>();
  return [...bundle.value.favorites, ...bundle.value.recent].filter((item) => {
    if (seen.has(item.id)) return false;
    seen.add(item.id);
    return true;
  });
});

const mapOptions = computed(() => Array.from(new Map(allPersonalTactics.value.map(t => [t.map.slug, t.map])).values()));
const utilityOptions = computed(() => Array.from(new Set(allPersonalTactics.value.flatMap(t => t.utility_types))).sort());

function matchesFilters(item: FavoriteBundle['favorites'][number]) {
  if (filterMap.value && item.map.slug !== filterMap.value) return false;
  if (filterSide.value && item.side !== filterSide.value) return false;
  if (filterUtility.value && !item.utility_types.includes(filterUtility.value)) return false;
  return true;
}

const filteredFavorites = computed(() => bundle.value ? bundle.value.favorites.filter(matchesFilters) : []);
const filteredRecent = computed(() => bundle.value ? bundle.value.recent.filter(matchesFilters) : []);
const frequentBundle = computed(() => allPersonalTactics.value.filter(matchesFilters).slice(0, 6));

onMounted(async () => {
  useHead('我的收藏', '已收藏的战术和最近浏览记录');

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
    <section class="glass-panel favorite-filter-panel">
      <select v-model="filterMap" class="filter-select">
        <option value="">全部地图</option>
        <option v-for="map in mapOptions" :key="map.slug" :value="map.slug">{{ map.name }}</option>
      </select>
      <select v-model="filterSide" class="filter-select">
        <option value="">全部阵营</option>
        <option value="T">T方</option>
        <option value="CT">CT方</option>
      </select>
      <select v-model="filterUtility" class="filter-select">
        <option value="">全部道具</option>
        <option v-for="utility in utilityOptions" :key="utility" :value="utility">{{ utility }}</option>
      </select>
      <button class="ghost-button" @click="filterMap='';filterSide='';filterUtility=''">清除</button>
    </section>

    <section v-if="frequentBundle.length" class="section-block favorite-bundle">
      <div class="section-heading">
        <h2>我的常用战术包</h2>
        <span class="muted">{{ frequentBundle.length }} 条</span>
      </div>
      <div class="favorites-grid">
        <TacticCard v-for="item in frequentBundle" :key="item.id" :tactic="item" />
      </div>
    </section>

    <section class="section-block favorite-bundle">
      <div class="section-heading">
        <h2>我的收藏</h2>
        <span class="muted">{{ filteredFavorites.length }} 条</span>
      </div>
      <div v-if="filteredFavorites.length" class="favorites-grid">
        <TacticCard v-for="item in filteredFavorites" :key="item.id" :tactic="item" />
      </div>
      <div v-else class="empty-card">你还没有收藏战术，可以先去地图页挑一套顺手的执行。</div>
    </section>

    <section class="section-block favorite-bundle">
      <div class="section-heading">
        <h2>最近浏览</h2>
        <span class="muted">{{ filteredRecent.length }} 条</span>
      </div>
      <div v-if="filteredRecent.length" class="favorites-grid">
        <TacticCard v-for="item in filteredRecent" :key="item.id" :tactic="item" />
      </div>
      <div v-else class="empty-card">最近还没有浏览记录。</div>
    </section>
  </template>
</template>

<style scoped>
.favorite-filter-panel {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  align-items: center;
  padding: 12px;
  margin-bottom: 18px;
}
.favorite-filter-panel .filter-select {
  min-width: 140px;
  border: 1px solid rgba(255,255,255,0.1);
  background: rgba(8,14,23,0.76);
  color: #fff;
  border-radius: 8px;
  padding: 9px 10px;
}
</style>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';

import { api, resolveAssetUrl } from '../api';
import TacticCard from '../components/TacticCard.vue';
import type { MapSummary, TacticCard as TacticCardType } from '../types';

const loading = ref(true);
const loadError = ref('');
const maps = ref<MapSummary[]>([]);
const allTactics = ref<TacticCardType[]>([]);

// Filters for the tactic grid
const filterMapSlug = ref('');
const filterSide = ref('');

onMounted(async () => {
  try {
    const [homeData, tacticsData] = await Promise.all([
      api.getHome(),
      api.getTactics({}),
    ]);
    maps.value = homeData.featured_maps;
    allTactics.value = tacticsData.items;
  } catch {
    loadError.value = '加载失败，请刷新重试';
  } finally {
    loading.value = false;
  }
});

const filteredTactics = computed(() => {
  return allTactics.value.filter(t => {
    if (filterMapSlug.value && t.map_slug !== filterMapSlug.value) return false;
    if (filterSide.value && t.side !== filterSide.value) return false;
    return true;
  });
});
</script>

<template>
  <div class="home-root">
    <!-- ── Hero ────────────────────────────────────────────── -->
    <section class="hero-panel">
      <div class="hero-text">
        <div class="kicker">CS2 Tactics Playbook</div>
        <h1 class="hero-title">战术手册</h1>
        <p class="hero-subtitle">
          以地图为入口，按阵营、道具、执行阶段浏览。快速找到下一局要用的配合。
        </p>
        <div class="hero-actions">
          <router-link class="primary-button" to="/maps">浏览全部地图</router-link>
          <router-link class="secondary-button" to="/favorites">我的收藏</router-link>
        </div>
      </div>
      <div class="hero-stats">
        <div class="hero-stat">
          <strong>{{ maps.length }}</strong>
          <span>张地图</span>
        </div>
        <div class="hero-stat">
          <strong>{{ allTactics.length }}</strong>
          <span>条战术</span>
        </div>
      </div>
    </section>

    <!-- ── Map entry cards (horizontal scroll) ─────────────── -->
    <section class="section-block" v-if="!loading">
      <div class="section-heading">
        <h2>快速选图</h2>
      </div>
      <div class="map-scroll">
        <router-link
          v-for="map in maps"
          :key="map.slug"
          class="map-entry-card"
          :to="`/maps/${map.slug}`"
        >
          <img :src="resolveAssetUrl(map.cover_url)" :alt="map.name" class="map-entry-icon" />
          <div class="map-entry-body">
            <strong>{{ map.name }}</strong>
            <span class="chip">{{ map.tactic_count }} 条战术</span>
          </div>
        </router-link>
      </div>
    </section>

    <!-- ── All tactics ─────────────────────────────────────── -->
    <section class="section-block" v-if="!loading">
      <div class="section-heading">
        <h2>全部战术</h2>
        <span class="muted" v-if="!loadError">{{ filteredTactics.length }} 条</span>
      </div>

      <!-- Filter chips -->
      <div class="home-filter-bar">
        <div class="filter-row">
          <button
            class="filter-chip"
            :class="{ active: !filterMapSlug }"
            @click="filterMapSlug = ''"
          >全部地图</button>
          <button
            v-for="map in maps"
            :key="map.slug"
            class="filter-chip"
            :class="{ active: filterMapSlug === map.slug }"
            @click="filterMapSlug = map.slug"
          >{{ map.name }}</button>
        </div>
        <div class="filter-row">
          <button
            class="filter-chip"
            :class="{ active: !filterSide }"
            @click="filterSide = ''"
          >全部阵营</button>
          <button
            class="filter-chip"
            :class="{ active: filterSide === 'T' }"
            @click="filterSide = 'T'"
          >T 进攻</button>
          <button
            class="filter-chip"
            :class="{ active: filterSide === 'CT' }"
            @click="filterSide = 'CT'"
          >CT 防守</button>
        </div>
      </div>

      <div class="card-grid">
        <TacticCard v-for="tactic in filteredTactics" :key="tactic.id" :tactic="tactic" />
      </div>

      <div v-if="filteredTactics.length === 0" class="empty-card">
        <p class="muted">没有匹配的战术</p>
      </div>
    </section>

    <div v-if="loadError" class="empty-card">
      <p class="muted">{{ loadError }}</p>
    </div>
  </div>
</template>

<style scoped>
.home-root {
  display: flex;
  flex-direction: column;
  gap: 32px;
}

/* ── Hero ─────────────────────────────── */
.hero-panel {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 24px;
  padding: 40px 0 8px;
}
.hero-text {
  max-width: 600px;
}
.hero-title {
  margin: 4px 0 12px;
  font-size: clamp(2rem, 5vw, 3rem);
  font-weight: 800;
}
.hero-subtitle {
  color: #aeb9cb;
  font-size: 1.05rem;
  line-height: 1.6;
  margin-bottom: 18px;
}
.hero-actions {
  display: flex;
  gap: 10px;
}
.hero-stats {
  display: flex;
  gap: 28px;
  flex-shrink: 0;
}
.hero-stat {
  text-align: center;
}
.hero-stat strong {
  display: block;
  font-size: 2rem;
  color: #ff7a18;
}
.hero-stat span {
  font-size: 0.82rem;
  color: #888;
}

/* ── Map scroll ────────────────────────── */
.map-scroll {
  display: flex;
  gap: 14px;
  overflow-x: auto;
  padding-bottom: 8px;
  scroll-snap-type: x mandatory;
  -webkit-overflow-scrolling: touch;
}
.map-scroll::-webkit-scrollbar {
  height: 6px;
}
.map-scroll::-webkit-scrollbar-thumb {
  background: #333;
  border-radius: 3px;
}
.map-entry-card {
  flex: 0 0 220px;
  scroll-snap-align: start;
  display: flex;
  flex-direction: column;
  border-radius: 20px;
  overflow: hidden;
  background: rgba(13, 20, 31, 0.9);
  border: 1px solid rgba(255, 255, 255, 0.08);
  transition: border-color 0.2s, transform 0.15s;
  text-decoration: none;
  color: inherit;
}
.map-entry-card:hover {
  border-color: #ff7a18;
  transform: translateY(-2px);
}
.map-entry-icon {
  width: 100%;
  aspect-ratio: 2 / 1;
  object-fit: cover;
}
.map-entry-body {
  padding: 12px 14px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.map-entry-body strong {
  font-size: 14px;
}

/* ── Filter chips ──────────────────────── */
.home-filter-bar {
  margin-bottom: 18px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.filter-row {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
.filter-chip {
  padding: 5px 14px;
  border-radius: 999px;
  border: 1px solid #444;
  background: #1a1a2e;
  color: #ddd;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s;
}
.filter-chip:hover {
  border-color: #ff7a18;
  color: #fff;
}
.filter-chip.active {
  background: #ff7a18;
  border-color: #ff7a18;
  color: #fff;
  font-weight: 700;
}
</style>

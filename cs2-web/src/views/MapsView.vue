<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';

import { api, resolveAssetUrl } from '../api';
import { useHead } from '../composables/useHead';
import TacticCard from '../components/TacticCard.vue';
import type { MapSummary, TacticCard as TacticCardType } from '../types';

const maps = ref<MapSummary[]>([]);
const tactics = ref<TacticCardType[]>([]);
const activeMapSlug = ref('');
const searchWord = ref('');
const activePoolOnly = ref(false);
const withTacticsOnly = ref(false);
const loadError = ref('');
const tacticLoadError = ref('');
const radarFallbacks = ref<Record<string, boolean>>({});

async function load() {
  loadError.value = '';
  tacticLoadError.value = '';
  try {
    const [mapItems, tacticItems] = await Promise.allSettled([
      api.getMaps(),
      api.getTactics({ page_size: 50 }),
    ]);
    if (mapItems.status === 'rejected') {
      throw mapItems.reason;
    }
    maps.value = mapItems.value;
    if (!activeMapSlug.value && mapItems.value[0]) {
      activeMapSlug.value = mapItems.value[0].slug;
    }
    if (tacticItems.status === 'fulfilled') {
      tactics.value = tacticItems.value.items;
    } else {
      tactics.value = [];
      tacticLoadError.value = '地图已加载，战术列表暂时加载失败';
    }
  } catch {
    loadError.value = '加载失败，请刷新重试';
  }
}

function selectMap(slug: string) {
  activeMapSlug.value = slug;
}

function clearFilters() {
  activeMapSlug.value = maps.value[0]?.slug || '';
  searchWord.value = '';
  activePoolOnly.value = false;
  withTacticsOnly.value = false;
}

function mapSearchText(map: MapSummary) {
  return [map.name, map.slug, map.overview].join(' ').toLowerCase();
}

const filteredMaps = computed(() => {
  const query = searchWord.value.trim().toLowerCase();
  return maps.value.filter((map) => {
    if (query && !mapSearchText(map).includes(query)) return false;
    if (activePoolOnly.value && !map.active_pool) return false;
    if (withTacticsOnly.value && (map.tactic_count || 0) <= 0) return false;
    return true;
  });
});

const activeMap = computed(() =>
  filteredMaps.value.find((map) => map.slug === activeMapSlug.value) || filteredMaps.value[0] || null,
);
const displayedTactics = computed(() => {
  if (!activeMap.value) return [];
  return tactics.value.filter((tactic) => tactic.map.slug === activeMap.value?.slug);
});

function mapRadarUrl(map: MapSummary) {
  if (radarFallbacks.value[map.slug]) {
    return resolveAssetUrl(map.layout_url || map.cover_url);
  }
  return resolveAssetUrl(`/static/assets/maps/radars/${map.slug}-radar.png`);
}

function useRadarFallback(map: MapSummary) {
  radarFallbacks.value = { ...radarFallbacks.value, [map.slug]: true };
}

onMounted(() => {
  useHead('地图库', '浏览全部 CS2 地图雷达图，按地图查找战术');
  load();
});
</script>

<template>
  <div class="maps-page">
    <section class="maps-heading">
      <div>
        <div class="kicker">Map-first Tactic Browser</div>
        <h1>地图库</h1>
      </div>
      <p class="section-intro">左侧选择地图，右侧查看对应雷达图和该地图战术。</p>
    </section>

    <div v-if="loadError" class="empty-card">
      <p class="muted">{{ loadError }}</p>
    </div>

    <div v-else class="maps-layout">
      <aside class="maps-sidebar">
        <div class="map-filter-section">
          <div class="side-label">搜索</div>
          <input
            v-model="searchWord"
            class="map-search"
            placeholder="搜索地图名称 / slug"
          />
        </div>

        <div class="map-filter-section">
          <div class="side-label">范围</div>
          <label class="filter-toggle">
            <input v-model="withTacticsOnly" type="checkbox" />
            <span>只看有战术的地图</span>
          </label>
          <label class="filter-toggle">
            <input v-model="activePoolOnly" type="checkbox" />
            <span>只看现役地图池</span>
          </label>
        </div>

        <div class="map-filter-section">
          <div class="side-label">地图</div>
          <button
            v-for="map in filteredMaps"
            :key="map.slug"
            class="map-list-item"
            :class="{ active: activeMap?.slug === map.slug }"
            @click="selectMap(map.slug)"
          >
            <span>{{ map.name }}</span>
            <strong>{{ map.tactic_count || 0 }}</strong>
          </button>
          <p v-if="filteredMaps.length === 0" class="muted small-empty">没有匹配的地图</p>
        </div>

        <button class="map-reset" @click="clearFilters">清除筛选</button>
      </aside>

      <main class="maps-main">
        <section v-if="activeMap" class="selected-map-panel">
          <div class="selected-map-media">
            <img
              :src="mapRadarUrl(activeMap)"
              :alt="activeMap.name"
              loading="lazy"
              @error="useRadarFallback(activeMap)"
            />
          </div>
          <div class="selected-map-info">
            <div class="section-heading compact-heading">
              <h2>{{ activeMap.name }}</h2>
              <span class="chip strong">{{ activeMap.tactic_count || 0 }} 条战术</span>
            </div>
            <p class="section-intro">{{ activeMap.overview }}</p>
            <div class="map-actions">
              <router-link class="primary-button small" :to="`/maps/${activeMap.slug}`">进入地图详情</router-link>
            </div>
          </div>
        </section>
        <div v-else class="empty-card">
          <p class="muted">没有匹配的地图</p>
        </div>

        <section v-if="activeMap" class="section-block map-tactics-section">
          <div class="section-heading compact-heading">
            <h2>{{ activeMap.name }} 战术</h2>
            <span class="muted">{{ displayedTactics.length }} 条结果</span>
          </div>
          <div v-if="tacticLoadError" class="empty-card">
            <p class="muted">{{ tacticLoadError }}</p>
          </div>
          <div v-if="displayedTactics.length" class="card-grid map-tactic-grid">
            <TacticCard v-for="tactic in displayedTactics" :key="tactic.id" :tactic="tactic" />
          </div>
          <div v-else-if="!tacticLoadError" class="empty-card">
            <p class="muted">这张地图暂时没有已发布战术</p>
          </div>
        </section>
      </main>
    </div>
  </div>
</template>

<style scoped>
.maps-page {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.maps-heading {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 18px;
  padding: 10px 0 2px;
}

.maps-heading h1 {
  margin: 4px 0 0;
  font-size: 1.55rem;
}

.maps-heading .section-intro {
  max-width: 420px;
  margin: 0;
  text-align: right;
}

.maps-layout {
  display: grid;
  grid-template-columns: 236px minmax(0, 1fr);
  gap: 20px;
  align-items: flex-start;
}

.maps-sidebar {
  position: sticky;
  top: 72px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  max-height: calc(100vh - 90px);
  padding: 14px 10px;
  overflow-y: auto;
  border-right: 1px solid rgba(255,255,255,0.06);
}

.side-label {
  margin-bottom: 7px;
  color: #7a8ba0;
  font-size: 0.68rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.map-search {
  width: 100%;
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 8px;
  background: rgba(8,14,23,0.76);
  color: #fff;
  padding: 8px 10px;
  font-size: 13px;
  line-height: 1.35;
}

.map-search:focus {
  outline: none;
  border-color: rgba(255,122,24,0.55);
}

.filter-toggle {
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 28px;
  color: #bcc8d6;
  font-size: 0.8rem;
}

.filter-toggle input {
  width: 14px;
  height: 14px;
  accent-color: #ff7a18;
}

.map-list-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  min-height: 30px;
  border: 0;
  border-radius: 7px;
  background: transparent;
  color: #bcc8d6;
  padding: 5px 9px;
  font-size: 0.8rem;
  text-align: left;
}

.map-list-item:hover {
  background: rgba(255,255,255,0.04);
}

.map-list-item.active {
  background: rgba(255,122,24,0.12);
  color: #ffb88c;
}

.map-list-item strong {
  color: #5a6478;
  font-size: 0.7rem;
}

.map-reset {
  min-height: 30px;
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 6px;
  background: none;
  color: #6b7d95;
  padding: 6px 10px;
  font-size: 0.74rem;
}

.map-reset:hover {
  color: #ff7a18;
  border-color: rgba(255,122,24,0.3);
}

.small-empty {
  margin: 6px 0 0;
  font-size: 0.78rem;
}

.maps-main {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.selected-map-panel {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(260px, 0.8fr);
  gap: 18px;
  align-items: stretch;
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 12px;
  background: rgba(13,20,31,0.72);
  padding: 14px;
}

.selected-map-media,
.radar-card-media {
  overflow: hidden;
  border-radius: 10px;
  background: rgba(255,255,255,0.025);
}

.selected-map-media img,
.radar-card-media img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.selected-map-media {
  aspect-ratio: 1 / 1;
}

.selected-map-info {
  display: flex;
  flex-direction: column;
  justify-content: center;
  min-width: 0;
}

.compact-heading {
  margin-bottom: 12px;
  padding-bottom: 10px;
}

.compact-heading h2 {
  font-size: 1.2rem;
}

.map-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 10px;
}

.radar-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 14px;
}

.radar-card {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 12px;
  background: rgba(13,20,31,0.72);
  color: inherit;
  text-decoration: none;
  transition: transform 0.18s ease, border-color 0.18s ease;
}

.radar-card:hover {
  transform: translateY(-2px);
  border-color: rgba(255,122,24,0.35);
}

.radar-card-media {
  aspect-ratio: 1 / 1;
  border-radius: 0;
}

.radar-card-info {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 10px 12px;
}

.radar-card-info strong {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 0.9rem;
}

.radar-card-info span {
  flex: 0 0 auto;
  color: #7a8ba0;
  font-size: 0.75rem;
}

.map-tactics-section {
  margin-top: 0;
}

.map-tactic-grid {
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 14px;
}

@media (max-width: 920px) {
  .selected-map-panel {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .maps-heading {
    align-items: flex-start;
    flex-direction: column;
    gap: 8px;
  }

  .maps-heading .section-intro {
    max-width: none;
    text-align: left;
  }

  .maps-layout {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .maps-sidebar {
    position: static;
    width: 100%;
    max-height: none;
    padding: 12px 0 4px;
    border-right: none;
  }

  .radar-grid,
  .map-tactic-grid {
    grid-template-columns: 1fr;
  }
}
</style>

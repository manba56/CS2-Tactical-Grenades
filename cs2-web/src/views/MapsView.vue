<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';

import { api, resolveAssetUrl } from '../api';
import { useHead } from '../composables/useHead';
import type { MapDetail, MapPoint, MapSummary, UtilityLineupDetail } from '../types';
import { label, DIFFICULTY_LABELS, SIDE_LABELS, UTILITY_LABELS } from '../utils/labels';

const maps = ref<MapSummary[]>([]);
const activeMapSlug = ref('');
const activeMapDetail = ref<MapDetail | null>(null);
const searchWord = ref('');
const activePoolOnly = ref(false);
const loadError = ref('');
const detailError = ref('');
const loadingDetail = ref(false);
const radarFallbacks = ref<Record<string, boolean>>({});
const activeLandingPointId = ref<number | null>(null);
const activeLineupId = ref<number | null>(null);
const lightboxUrl = ref('');

type LandingGroup = {
  point: MapPoint;
  lineups: UtilityLineupDetail[];
};

type LineupMediaCard = {
  title: string;
  description: string;
  url: string;
};

function mapSearchText(map: MapSummary) {
  return [map.name, map.slug, map.overview].join(' ').toLowerCase();
}

const filteredMaps = computed(() => {
  const query = searchWord.value.trim().toLowerCase();
  return maps.value.filter((map) => {
    if (query && !mapSearchText(map).includes(query)) return false;
    if (activePoolOnly.value && !map.active_pool) return false;
    return true;
  });
});

const activeMap = computed(() =>
  maps.value.find((map) => map.slug === activeMapSlug.value) || null,
);

const landingGroups = computed<LandingGroup[]>(() => {
  if (!activeMapDetail.value) return [];
  const byPoint = new Map<number, UtilityLineupDetail[]>();
  for (const lineup of activeMapDetail.value.lineups) {
    const items = byPoint.get(lineup.land_point_id) || [];
    items.push(lineup);
    byPoint.set(lineup.land_point_id, items);
  }
  return Array.from(byPoint.entries())
    .map(([pointId, lineups]) => {
      const point = activeMapDetail.value?.points.find((item) => item.id === pointId);
      return point ? { point, lineups } : null;
    })
    .filter((item): item is LandingGroup => Boolean(item))
    .sort((a, b) => a.point.name.localeCompare(b.point.name));
});

const activeLandingGroup = computed(() =>
  landingGroups.value.find((group) => group.point.id === activeLandingPointId.value) || null,
);

const activeLineup = computed(() => {
  const group = activeLandingGroup.value;
  if (!group) return null;
  return group.lineups.find((lineup) => lineup.id === activeLineupId.value) || group.lineups[0] || null;
});

const selectedLineupPoints = computed(() => {
  const lineup = activeLineup.value;
  if (!lineup) return [];
  return [
    { role: '站位', point: lineup.start_point, color: '#65d6ce' },
    { role: '瞄点', point: lineup.aim_point, color: '#ff7a18' },
    { role: '落点', point: lineup.land_point, color: '#f5d76e' },
  ].filter((item) => item.point);
});

const activeLineupMediaCards = computed<LineupMediaCard[]>(() => {
  const lineup = activeLineup.value;
  if (!lineup) return [];
  const cards: LineupMediaCard[] = [];

  if (lineup.start_point?.aim_image_url) {
    cards.push({
      title: '站位瞄点',
      description: lineup.start_point.aim_image_description || lineup.start_point.description || '站到这里后再对准道具瞄点。',
      url: lineup.start_point.aim_image_url,
    });
  }
  if (lineup.aim_point?.aim_image_url) {
    cards.push({
      title: '道具瞄点',
      description: lineup.aim_point.aim_image_description || lineup.aim_point.description || '准星对准该位置后按步骤投掷。',
      url: lineup.aim_point.aim_image_url,
    });
  }
  if (lineup.land_point?.effect_image_url) {
    cards.push({
      title: '落点效果图',
      description: lineup.land_point.effect_image_description || lineup.land_point.description || '道具落点和实际遮挡效果。',
      url: lineup.land_point.effect_image_url,
    });
  }
  for (const [index, url] of (lineup.media || []).entries()) {
    cards.push({
      title: `补充截图 ${index + 1}`,
      description: '',
      url,
    });
  }

  return cards;
});

const activeVideoUrl = computed(() => {
  const lineup = activeLineup.value;
  if (!lineup) return '';
  return lineup.video_url || lineup.aim_point?.video_url || lineup.start_point?.video_url || lineup.land_point?.video_url || '';
});

const lineupPath = computed(() =>
  selectedLineupPoints.value
    .map((item, index) => `${index === 0 ? 'M' : 'L'}${item.point.x} ${item.point.y}`)
    .join(' '),
);

const radarUrl = computed(() => {
  const map = activeMapDetail.value || activeMap.value;
  if (!map) return '';
  if (radarFallbacks.value[map.slug]) return resolveAssetUrl(map.layout_url || map.cover_url);
  return resolveAssetUrl(`/static/assets/maps/radars/${map.slug}-radar.png`);
});

async function loadMaps() {
  loadError.value = '';
  try {
    maps.value = await api.getMaps();
    if (!activeMapSlug.value && maps.value[0]) {
      activeMapSlug.value = maps.value[0].slug;
    }
  } catch {
    loadError.value = '加载失败，请刷新重试';
  }
}

let detailRequestId = 0;
async function loadMapDetail(slug: string) {
  if (!slug) {
    activeMapDetail.value = null;
    return;
  }
  const requestId = ++detailRequestId;
  loadingDetail.value = true;
  detailError.value = '';
  activeLandingPointId.value = null;
  activeLineupId.value = null;
  lightboxUrl.value = '';
  try {
    const detail = await api.getMapDetail(slug);
    if (requestId !== detailRequestId) return;
    activeMapDetail.value = detail;
  } catch {
    if (requestId !== detailRequestId) return;
    activeMapDetail.value = null;
    detailError.value = '地图道具加载失败，请稍后重试';
  } finally {
    if (requestId === detailRequestId) loadingDetail.value = false;
  }
}

function selectMap(slug: string) {
  activeMapSlug.value = slug;
}

function clearFilters() {
  searchWord.value = '';
  activePoolOnly.value = false;
  activeMapSlug.value = maps.value[0]?.slug || '';
}

function selectLanding(group: LandingGroup) {
  if (activeLandingPointId.value === group.point.id) {
    activeLandingPointId.value = null;
    activeLineupId.value = null;
    return;
  }
  activeLandingPointId.value = group.point.id;
  activeLineupId.value = group.lineups[0]?.id || null;
}

function selectLineup(lineup: UtilityLineupDetail) {
  activeLineupId.value = lineup.id;
}

function utilityTypesForGroup(group: LandingGroup) {
  return Array.from(new Set(group.lineups.map((lineup) => lineup.utility_type)));
}

function pointFill(point: MapPoint) {
  if (point.side === 'CT') return '#65d6ce';
  if (point.side === 'T') return '#ff7a18';
  return '#f5d76e';
}

function useRadarFallback(slug: string) {
  radarFallbacks.value = { ...radarFallbacks.value, [slug]: true };
}

function openLightbox(url: string) {
  lightboxUrl.value = resolveAssetUrl(url);
}

watch(activeMapSlug, (slug) => {
  loadMapDetail(slug);
});

watch(filteredMaps, (items) => {
  if (items.length === 0) {
    activeMapSlug.value = '';
    return;
  }
  if (!items.some((map) => map.slug === activeMapSlug.value)) {
    activeMapSlug.value = items[0].slug;
  }
});

onMounted(() => {
  useHead('地图库', '在地图库直接查看 CS2 地图雷达落点和投掷物道具线路');
  loadMaps();
});
</script>

<template>
  <div class="maps-page">
    <section class="maps-heading">
      <div>
        <div class="kicker">Utility Radar Browser</div>
        <h1>地图库</h1>
      </div>
      <p class="section-intro">左侧切换地图，右侧直接点击雷达落点查看对应道具。</p>
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
            :class="{ active: activeMapSlug === map.slug }"
            @click="selectMap(map.slug)"
          >
            <span>{{ map.name }}</span>
          </button>
          <p v-if="filteredMaps.length === 0" class="muted small-empty">没有匹配的地图</p>
        </div>

        <button class="map-reset" @click="clearFilters">清除筛选</button>
      </aside>

      <main class="maps-main">
        <section v-if="activeMap" class="map-utility-layout">
          <div class="glass-panel radar-panel">
            <div class="radar-toolbar">
              <div>
                <strong>{{ activeMap.name }}</strong>
                <span class="muted">
                  {{ loadingDetail ? '加载道具中...' : `${landingGroups.length} 个落点` }}
                </span>
              </div>
              <button v-if="activeLandingGroup" class="secondary-button" @click="activeLandingPointId = null; activeLineupId = null">
                清除落点
              </button>
            </div>

            <div class="map-stage radar-stage">
              <img
                :src="radarUrl"
                :alt="activeMap.name"
                loading="lazy"
                @error="useRadarFallback(activeMap.slug)"
              />
              <svg v-if="activeLineup" class="lineup-overlay" viewBox="0 0 100 100" preserveAspectRatio="none">
                <path
                  v-if="lineupPath"
                  :d="lineupPath"
                  stroke="#ff7a18"
                  stroke-width="0.85"
                  fill="none"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                />
              </svg>

              <button
                v-for="group in landingGroups"
                :key="group.point.id"
                class="landing-marker"
                :class="{ active: activeLandingPointId === group.point.id }"
                :style="{ left: `${group.point.x}%`, top: `${group.point.y}%`, background: pointFill(group.point) }"
                :title="group.point.name"
                @click="selectLanding(group)"
              >
                {{ group.lineups.length }}
              </button>
              <button
                v-for="group in landingGroups"
                :key="`label-${group.point.id}`"
                class="landing-label"
                :class="{ active: activeLandingPointId === group.point.id }"
                :style="{ left: `${group.point.x}%`, top: `${group.point.y}%` }"
                @click="selectLanding(group)"
              >
                {{ group.point.name }}
              </button>

              <span
                v-for="item in selectedLineupPoints"
                :key="item.role"
                class="lineup-point"
                :style="{ left: `${item.point.x}%`, top: `${item.point.y}%`, background: item.color }"
              >
                {{ item.role }}
              </span>
            </div>
          </div>

          <aside class="glass-panel landing-panel">
            <div v-if="detailError" class="empty-landing-panel">
              <div class="kicker">Error</div>
              <h2>道具加载失败</h2>
              <p class="muted">{{ detailError }}</p>
            </div>

            <template v-else-if="activeLandingGroup">
              <div class="landing-panel-heading">
                <div>
                  <div class="kicker">Landing Point</div>
                  <h2>{{ activeLandingGroup.point.name }}</h2>
                </div>
                <span class="chip strong">{{ activeLandingGroup.lineups.length }} 个道具</span>
              </div>
              <p v-if="activeLandingGroup.point.description" class="section-intro">
                {{ activeLandingGroup.point.description }}
              </p>
              <div class="chip-row">
                <span
                  v-for="utility in utilityTypesForGroup(activeLandingGroup)"
                  :key="utility"
                  class="chip util-badge"
                  :class="'util-' + utility"
                >
                  {{ label(utility, UTILITY_LABELS) }}
                </span>
              </div>

              <div class="lineup-list">
                <button
                  v-for="lineup in activeLandingGroup.lineups"
                  :key="lineup.id"
                  class="lineup-item"
                  :class="{ active: activeLineup?.id === lineup.id }"
                  @click="selectLineup(lineup)"
                >
                  <strong>{{ lineup.title }}</strong>
                  <span>{{ label(lineup.utility_type, UTILITY_LABELS) }} · {{ label(lineup.side, SIDE_LABELS) }}</span>
                </button>
              </div>

              <div v-if="activeLineup" class="lineup-detail">
                <div class="lineup-detail-meta">
                  <span class="chip">{{ label(activeLineup.utility_type, UTILITY_LABELS) }}</span>
                  <span class="chip">{{ label(activeLineup.side, SIDE_LABELS) }}</span>
                  <span class="chip">{{ label(activeLineup.difficulty, DIFFICULTY_LABELS) }}</span>
                </div>
                <p class="section-intro">{{ activeLineup.summary || activeLineup.purpose }}</p>
                <div class="point-triplet">
                  <span><strong>站位瞄点</strong>{{ activeLineup.start_point?.name }}</span>
                  <span><strong>道具瞄点</strong>{{ activeLineup.aim_point?.name }}</span>
                  <span><strong>落点</strong>{{ activeLineup.land_point?.name }}</span>
                </div>
                <ol v-if="activeLineup.steps?.length" class="lineup-steps">
                  <li v-for="step in activeLineup.steps" :key="step">{{ step }}</li>
                </ol>
                <div v-if="activeLineupMediaCards.length" class="lineup-media-grid">
                  <button
                    v-for="card in activeLineupMediaCards"
                    :key="`${card.title}-${card.url}`"
                    type="button"
                    class="lineup-media-card"
                    @click="openLightbox(card.url)"
                  >
                    <img :src="resolveAssetUrl(card.url)" :alt="card.title" loading="lazy" />
                    <span>
                      <strong>{{ card.title }}</strong>
                      <small v-if="card.description">{{ card.description }}</small>
                    </span>
                  </button>
                </div>
                <a v-if="activeVideoUrl" class="video-link-card" :href="activeVideoUrl" target="_blank" rel="noreferrer">
                  <strong>视频演示</strong>
                  <span>{{ activeVideoUrl }}</span>
                </a>
              </div>
            </template>

            <div v-else class="empty-landing-panel">
              <div class="kicker">Landing Point</div>
              <h2>{{ loadingDetail ? '正在加载道具' : '点击雷达上的落点' }}</h2>
              <p class="muted">这里会显示该落点下所有烟、闪、火、雷线路。一个落点可以关联多个道具。</p>
            </div>
          </aside>
        </section>

        <div v-else class="empty-card">
          <p class="muted">没有匹配的地图</p>
        </div>
      </main>
    </div>

    <div v-if="lightboxUrl" class="point-lightbox" @click="lightboxUrl = ''">
      <img :src="lightboxUrl" alt="utility media" />
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
}

.map-utility-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.35fr) minmax(300px, 0.65fr);
  gap: 18px;
  align-items: start;
}

.radar-panel,
.landing-panel {
  border-radius: 12px;
}

.radar-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.radar-toolbar strong {
  display: block;
}

.radar-toolbar .muted {
  font-size: 0.78rem;
}

.radar-stage {
  position: relative;
  overflow: hidden;
  border-radius: 10px;
  background: rgba(255,255,255,0.025);
}

.radar-stage img {
  display: block;
  width: 100%;
}

.lineup-overlay {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.landing-marker {
  position: absolute;
  width: 24px;
  height: 24px;
  border: 2px solid #fff;
  border-radius: 999px;
  color: #07111f;
  font-size: 0.72rem;
  font-weight: 900;
  line-height: 1;
  transform: translate(-50%, -50%);
  box-shadow: 0 0 0 7px rgba(255,122,24,0.16);
  cursor: pointer;
  z-index: 3;
}

.landing-marker:hover,
.landing-marker.active {
  box-shadow: 0 0 0 5px rgba(255,122,24,0.34), 0 0 18px rgba(255,122,24,0.55);
  transform: translate(-50%, -50%) scale(1.12);
}

.landing-label {
  position: absolute;
  max-width: 130px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  border: 1px solid rgba(255,255,255,0.14);
  border-radius: 999px;
  background: rgba(8,14,23,0.86);
  color: #fff;
  padding: 4px 8px;
  font-size: 0.72rem;
  transform: translate(-50%, 14px);
  cursor: pointer;
  z-index: 2;
}

.landing-label.active {
  color: #ffb88c;
  border-color: rgba(255,122,24,0.55);
  background: rgba(255,122,24,0.18);
}

.lineup-point {
  position: absolute;
  z-index: 4;
  border: 2px solid #fff;
  border-radius: 999px;
  color: #07111f;
  padding: 2px 7px;
  font-size: 0.68rem;
  font-weight: 900;
  transform: translate(-50%, -50%);
  white-space: nowrap;
  pointer-events: none;
}

.landing-panel {
  min-height: 420px;
}

.landing-panel-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.landing-panel-heading h2,
.empty-landing-panel h2 {
  margin: 4px 0 0;
  font-size: 1.2rem;
}

.lineup-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin: 14px 0;
}

.lineup-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 8px;
  background: rgba(255,255,255,0.03);
  color: #dfe9f6;
  padding: 10px;
  text-align: left;
}

.lineup-item:hover,
.lineup-item.active {
  border-color: rgba(255,122,24,0.42);
  background: rgba(255,122,24,0.12);
}

.lineup-item span {
  color: #91a3ba;
  font-size: 0.75rem;
}

.lineup-detail {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding-top: 12px;
  border-top: 1px solid rgba(255,255,255,0.08);
}

.lineup-detail-meta,
.point-triplet {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.point-triplet span {
  flex: 1 1 90px;
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 8px;
  background: rgba(255,255,255,0.03);
  padding: 8px;
  color: #dfe9f6;
  font-size: 0.78rem;
}

.point-triplet strong {
  display: block;
  color: #7a8ba0;
  font-size: 0.68rem;
}

.lineup-steps {
  margin: 0;
  padding-left: 18px;
  color: #d6e2f0;
}

.lineup-steps li + li {
  margin-top: 6px;
}

.lineup-media-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.lineup-media-card {
  overflow: hidden;
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 8px;
  background: rgba(255,255,255,0.03);
  padding: 0;
  color: #dfe9f6;
  text-align: left;
}

.lineup-media-card img {
  display: block;
  width: 100%;
  aspect-ratio: 16 / 10;
  object-fit: cover;
}

.lineup-media-card span {
  display: grid;
  gap: 3px;
  padding: 9px;
}

.lineup-media-card strong {
  font-size: 0.8rem;
}

.lineup-media-card small {
  color: #91a3ba;
  font-size: 0.72rem;
  line-height: 1.35;
}

.video-link-card {
  display: grid;
  gap: 4px;
  border: 1px solid rgba(255,122,24,0.28);
  border-radius: 8px;
  background: rgba(255,122,24,0.1);
  color: #ffd1b3;
  padding: 10px;
  text-decoration: none;
}

.video-link-card span {
  overflow: hidden;
  color: #91a3ba;
  font-size: 0.74rem;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.empty-landing-panel {
  display: flex;
  flex-direction: column;
  justify-content: center;
  min-height: 320px;
}

.point-lightbox {
  position: fixed;
  inset: 0;
  z-index: 100;
  display: grid;
  place-items: center;
  padding: 24px;
  background: rgba(0,0,0,0.82);
  cursor: zoom-out;
}

.point-lightbox img {
  max-width: min(1100px, 96vw);
  max-height: 90vh;
  border-radius: 10px;
  object-fit: contain;
}

@media (max-width: 920px) {
  .map-utility-layout {
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

  .landing-panel {
    min-height: 0;
  }
}
</style>

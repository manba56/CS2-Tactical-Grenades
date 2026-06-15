<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import { api, resolveAssetUrl } from '../api';
import { useHead } from '../composables/useHead';
import { useI18n } from '../composables/useI18n';
import type { MapDetail, MapPoint, MapSummary, UtilityLineupDetail } from '../types';
import {
  DIFFICULTY_LABELS,
  DIFFICULTY_LABELS_EN,
  SIDE_LABELS,
  SIDE_LABELS_EN,
  UTILITY_LABELS,
  UTILITY_LABELS_EN,
  labelByLanguage,
} from '../utils/labels';
import {
  buildLineupMediaCards,
  groupLineupsByLandingPoint,
  type LandingGroup,
  type LineupMediaCard,
} from '../utils/mapUtilities.js';

const maps = ref<MapSummary[]>([]);
const route = useRoute();
const router = useRouter();
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
const pendingLandingPointId = ref<number | null>(null);
const pendingLineupId = ref<number | null>(null);
const selectedUtility = ref('all');
const selectedSide = ref('all');
const selectedDifficulty = ref('all');
const radarZoom = ref(1);
const shareMessage = ref('');
const favoriteLineupIds = ref<number[]>([]);
const FAVORITE_UTILITY_KEY = 'cs2-favorite-lineups';
const { language, t } = useI18n();

type UtilitySection = {
  utility: string;
  lineups: UtilityLineupDetail[];
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
  return groupLineupsByLandingPoint(activeMapDetail.value.points, filteredLineups.value);
});

const activeLandingGroup = computed(() =>
  landingGroups.value.find((group) => group.point.id === activeLandingPointId.value) || null,
);

const activeLineup = computed(() => {
  const group = activeLandingGroup.value;
  if (!group) return null;
  return group.lineups.find((lineup) => lineup.id === activeLineupId.value) || group.lineups[0] || null;
});

const filteredLineups = computed(() => {
  const lineups = activeMapDetail.value?.lineups || [];
  return lineups.filter((lineup) => {
    if (selectedUtility.value !== 'all' && lineup.utility_type !== selectedUtility.value) return false;
    if (selectedSide.value !== 'all' && lineup.side !== selectedSide.value) return false;
    if (selectedDifficulty.value !== 'all' && lineup.difficulty !== selectedDifficulty.value) return false;
    return true;
  });
});

const utilityOptions = computed(() => Array.from(new Set((activeMapDetail.value?.lineups || []).map((lineup) => lineup.utility_type))));
const sideOptions = computed(() => Array.from(new Set((activeMapDetail.value?.lineups || []).map((lineup) => lineup.side))));
const difficultyOptions = computed(() => Array.from(new Set((activeMapDetail.value?.lineups || []).map((lineup) => lineup.difficulty))));

const activeLandingSections = computed<UtilitySection[]>(() => {
  const group = activeLandingGroup.value;
  if (!group) return [];
  const byUtility = new Map<string, UtilityLineupDetail[]>();
  for (const lineup of group.lineups) {
    const items = byUtility.get(lineup.utility_type) || [];
    items.push(lineup);
    byUtility.set(lineup.utility_type, items);
  }
  return Array.from(byUtility.entries()).map(([utility, lineups]) => ({ utility, lineups }));
});

const activeLineupShareUrl = computed(() => {
  if (!activeMapSlug.value) return '';
  const params = new URLSearchParams();
  params.set('map', activeMapSlug.value);
  if (selectedUtility.value !== 'all') params.set('utility', selectedUtility.value);
  if (selectedSide.value !== 'all') params.set('side', selectedSide.value);
  if (selectedDifficulty.value !== 'all') params.set('difficulty', selectedDifficulty.value);
  if (activeLandingPointId.value) params.set('land', String(activeLandingPointId.value));
  if (activeLineupId.value) params.set('lineup', String(activeLineupId.value));
  return `${window.location.origin}/maps?${params.toString()}`;
});

const isActiveLineupFavorite = computed(() =>
  activeLineup.value ? favoriteLineupIds.value.includes(activeLineup.value.id) : false,
);

const selectedLineupPoints = computed(() => {
  const lineup = activeLineup.value;
  if (!lineup) return [];
  return [
    { role: t('standAimPoint'), point: lineup.start_point, color: '#65d6ce' },
    { role: t('utilityAimPoint'), point: lineup.aim_point, color: '#ff7a18' },
    { role: t('landingPoint'), point: lineup.land_point, color: '#f5d76e' },
  ].filter((item) => item.point);
});

const activeLineupMediaCards = computed<LineupMediaCard[]>(() => {
  return buildLineupMediaCards(activeLineup.value, language.value);
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
    const queryMap = typeof route.query.map === 'string' ? route.query.map : '';
    if (!activeMapSlug.value && maps.value[0]) {
      activeMapSlug.value = maps.value.some((map) => map.slug === queryMap) ? queryMap : maps.value[0].slug;
    }
  } catch {
    loadError.value = t('loadingFailedRefresh');
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
  radarZoom.value = 1;
  lightboxUrl.value = '';
  try {
    const detail = await api.getMapDetail(slug);
    if (requestId !== detailRequestId) return;
    activeMapDetail.value = detail;
    applyPendingSelection();
  } catch {
    if (requestId !== detailRequestId) return;
    activeMapDetail.value = null;
    detailError.value = t('mapUtilityLoadFailed');
  } finally {
    if (requestId === detailRequestId) loadingDetail.value = false;
  }
}

function selectMap(slug: string) {
  activeMapSlug.value = slug;
  syncSelectionToUrl();
}

function clearFilters() {
  searchWord.value = '';
  activePoolOnly.value = false;
  selectedUtility.value = 'all';
  selectedSide.value = 'all';
  selectedDifficulty.value = 'all';
  clearLandingSelection(false);
  activeMapSlug.value = maps.value[0]?.slug || '';
  syncSelectionToUrl();
}

function selectLanding(group: LandingGroup) {
  if (activeLandingPointId.value === group.point.id) {
    activeLandingPointId.value = null;
    activeLineupId.value = null;
    syncSelectionToUrl();
    return;
  }
  activeLandingPointId.value = group.point.id;
  activeLineupId.value = group.lineups[0]?.id || null;
  syncSelectionToUrl();
}

function clearLandingSelection(sync = true) {
  activeLandingPointId.value = null;
  activeLineupId.value = null;
  if (sync) syncSelectionToUrl();
}

function selectLineup(lineup: UtilityLineupDetail) {
  activeLineupId.value = lineup.id;
  syncSelectionToUrl();
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

function syncSelectionToUrl() {
  const query: Record<string, string> = {};
  if (activeMapSlug.value) query.map = activeMapSlug.value;
  if (selectedUtility.value !== 'all') query.utility = selectedUtility.value;
  if (selectedSide.value !== 'all') query.side = selectedSide.value;
  if (selectedDifficulty.value !== 'all') query.difficulty = selectedDifficulty.value;
  if (activeLandingPointId.value) query.land = String(activeLandingPointId.value);
  if (activeLineupId.value) query.lineup = String(activeLineupId.value);
  router.replace({ path: '/maps', query });
}

function applyPendingSelection() {
  const detail = activeMapDetail.value;
  if (!detail) return;
  const landingId = pendingLandingPointId.value;
  const lineupId = pendingLineupId.value;
  if (!landingId) return;
  const group = landingGroups.value.find((item) => item.point.id === landingId);
  if (!group) return;
  activeLandingPointId.value = group.point.id;
  activeLineupId.value = group.lineups.some((lineup) => lineup.id === lineupId)
    ? lineupId
    : group.lineups[0]?.id || null;
  pendingLandingPointId.value = null;
  pendingLineupId.value = null;
}

function loadFavoriteLineups() {
  try {
    favoriteLineupIds.value = JSON.parse(localStorage.getItem(FAVORITE_UTILITY_KEY) || '[]');
  } catch {
    favoriteLineupIds.value = [];
  }
}

function saveFavoriteLineups() {
  localStorage.setItem(FAVORITE_UTILITY_KEY, JSON.stringify(favoriteLineupIds.value));
}

function toggleActiveLineupFavorite() {
  const lineup = activeLineup.value;
  if (!lineup) return;
  const exists = favoriteLineupIds.value.includes(lineup.id);
  favoriteLineupIds.value = exists
    ? favoriteLineupIds.value.filter((id) => id !== lineup.id)
    : [...favoriteLineupIds.value, lineup.id];
  saveFavoriteLineups();
}

async function copyShareLink() {
  if (!activeLineupShareUrl.value) return;
  try {
    await navigator.clipboard.writeText(activeLineupShareUrl.value);
    shareMessage.value = t('linkCopied');
  } catch {
    shareMessage.value = activeLineupShareUrl.value;
  }
  window.setTimeout(() => {
    shareMessage.value = '';
  }, 2200);
}

function changeRadarZoom(delta: number) {
  radarZoom.value = Math.min(2.2, Math.max(1, Number((radarZoom.value + delta).toFixed(2))));
}

function resetRadarZoom() {
  radarZoom.value = 1;
}

watch(activeMapSlug, (slug) => {
  loadMapDetail(slug);
});

watch([selectedUtility, selectedSide, selectedDifficulty], () => {
  const group = activeLandingPointId.value
    ? landingGroups.value.find((item) => item.point.id === activeLandingPointId.value)
    : null;
  if (!group) {
    activeLandingPointId.value = null;
    activeLineupId.value = null;
  } else if (!group.lineups.some((lineup) => lineup.id === activeLineupId.value)) {
    activeLineupId.value = group.lineups[0]?.id || null;
  }
  syncSelectionToUrl();
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
  useHead(t('maps'), t('mapPageIntro'));
  const queryMap = typeof route.query.map === 'string' ? route.query.map : '';
  const queryLand = Number(route.query.land || 0);
  const queryLineup = Number(route.query.lineup || 0);
  const queryUtility = typeof route.query.utility === 'string' ? route.query.utility : '';
  const querySide = typeof route.query.side === 'string' ? route.query.side : '';
  const queryDifficulty = typeof route.query.difficulty === 'string' ? route.query.difficulty : '';
  if (queryMap) activeMapSlug.value = queryMap;
  if (queryLand) pendingLandingPointId.value = queryLand;
  if (queryLineup) pendingLineupId.value = queryLineup;
  if (queryUtility) selectedUtility.value = queryUtility;
  if (querySide) selectedSide.value = querySide;
  if (queryDifficulty) selectedDifficulty.value = queryDifficulty;
  loadFavoriteLineups();
  loadMaps();
});
</script>

<template>
  <div class="maps-page">
    <section class="maps-heading">
      <div>
        <div class="kicker">{{ t('utilityRadarBrowser') }}</div>
        <h1>{{ t('maps') }}</h1>
      </div>
      <p class="section-intro">{{ t('mapPageIntro') }}</p>
    </section>

    <div v-if="loadError" class="empty-card">
      <p class="muted">{{ loadError }}</p>
    </div>

    <div v-else class="maps-layout">
      <aside class="maps-sidebar">
        <div class="map-filter-section">
          <div class="side-label">{{ t('search') }}</div>
          <input
            v-model="searchWord"
            class="map-search"
            :placeholder="t('mapSearchPlaceholder')"
          />
        </div>

        <div class="map-filter-section">
          <div class="side-label">{{ t('scope') }}</div>
          <label class="filter-toggle">
            <input v-model="activePoolOnly" type="checkbox" />
            <span>{{ t('activePoolOnly') }}</span>
          </label>
        </div>

        <div class="map-filter-section">
          <div class="side-label">{{ t('utilityFilter') }}</div>
          <select v-model="selectedUtility" class="map-filter-select">
            <option value="all">{{ t('allUtilities') }}</option>
            <option v-for="utility in utilityOptions" :key="utility" :value="utility">
              {{ labelByLanguage(utility, UTILITY_LABELS, UTILITY_LABELS_EN, language) }}
            </option>
          </select>
          <select v-model="selectedSide" class="map-filter-select">
            <option value="all">{{ t('allSides') }}</option>
            <option v-for="side in sideOptions" :key="side" :value="side">
              {{ labelByLanguage(side, SIDE_LABELS, SIDE_LABELS_EN, language) }}
            </option>
          </select>
          <select v-model="selectedDifficulty" class="map-filter-select">
            <option value="all">{{ t('allDifficulties') }}</option>
            <option v-for="difficulty in difficultyOptions" :key="difficulty" :value="difficulty">
              {{ labelByLanguage(difficulty, DIFFICULTY_LABELS, DIFFICULTY_LABELS_EN, language) }}
            </option>
          </select>
        </div>

        <div class="map-filter-section">
          <div class="side-label">{{ t('maps') }}</div>
          <button
            v-for="map in filteredMaps"
            :key="map.slug"
            class="map-list-item"
            :class="{ active: activeMapSlug === map.slug }"
            @click="selectMap(map.slug)"
          >
            <span>{{ map.name }}</span>
          </button>
          <p v-if="filteredMaps.length === 0" class="muted small-empty">{{ t('noMatchedMaps') }}</p>
        </div>

        <button class="map-reset" @click="clearFilters">{{ t('clearFilters') }}</button>
      </aside>

      <main class="maps-main">
        <section v-if="activeMap" class="map-utility-layout">
          <div class="glass-panel radar-panel">
            <div class="radar-toolbar">
              <div>
                <strong>{{ activeMap.name }}</strong>
                <span class="muted">
                  {{ loadingDetail ? t('loadingUtilities') : `${landingGroups.length} ${t('landingPointCount')}` }}
                  <template v-if="activeMapDetail"> / {{ filteredLineups.length }} {{ t('utilityCount') }}</template>
                </span>
              </div>
              <div class="radar-actions">
                <button class="secondary-button compact" type="button" @click="changeRadarZoom(0.2)">{{ t('zoomIn') }}</button>
                <button class="secondary-button compact" type="button" @click="changeRadarZoom(-0.2)">{{ t('zoomOut') }}</button>
                <button v-if="radarZoom > 1" class="secondary-button compact" type="button" @click="resetRadarZoom">{{ t('reset') }}</button>
                <button v-if="activeLandingGroup" class="secondary-button compact" type="button" @click="clearLandingSelection">
                  {{ t('clearLanding') }}
                </button>
              </div>
            </div>

            <div class="radar-scroll">
              <div class="map-stage radar-stage" :style="{ width: `${radarZoom * 100}%` }">
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
          </div>

          <aside class="glass-panel landing-panel">
            <div v-if="detailError" class="empty-landing-panel">
              <div class="kicker">Error</div>
              <h2>{{ t('utilityLoadFailed') }}</h2>
              <p class="muted">{{ detailError }}</p>
            </div>

            <template v-else-if="activeLandingGroup">
              <div class="landing-panel-heading">
                <div>
                  <div class="kicker">{{ t('landingPointKicker') }}</div>
                  <h2>{{ activeLandingGroup.point.name }}</h2>
                </div>
                <span class="chip strong">{{ activeLandingGroup.lineups.length }} {{ t('utilityCount') }}</span>
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
                  {{ labelByLanguage(utility, UTILITY_LABELS, UTILITY_LABELS_EN, language) }}
                </span>
              </div>

              <div class="lineup-list">
                <section v-for="section in activeLandingSections" :key="section.utility" class="lineup-section">
                  <div class="lineup-section-title">{{ labelByLanguage(section.utility, UTILITY_LABELS, UTILITY_LABELS_EN, language) }}</div>
                  <button
                    v-for="lineup in section.lineups"
                    :key="lineup.id"
                    class="lineup-item"
                    :class="{ active: activeLineup?.id === lineup.id, favorite: favoriteLineupIds.includes(lineup.id) }"
                    @click="selectLineup(lineup)"
                  >
                    <strong>{{ lineup.title }}</strong>
                    <span>
                      {{ labelByLanguage(lineup.utility_type, UTILITY_LABELS, UTILITY_LABELS_EN, language) }}
                      · {{ labelByLanguage(lineup.side, SIDE_LABELS, SIDE_LABELS_EN, language) }}
                      · {{ labelByLanguage(lineup.difficulty, DIFFICULTY_LABELS, DIFFICULTY_LABELS_EN, language) }}
                    </span>
                  </button>
                </section>
              </div>

              <div v-if="activeLineup" class="lineup-detail">
                <div class="lineup-action-row">
                  <button class="secondary-button compact" type="button" @click="toggleActiveLineupFavorite">
                    {{ isActiveLineupFavorite ? t('favoriteAdded') : t('favoriteUtility') }}
                  </button>
                  <button class="secondary-button compact" type="button" @click="copyShareLink">{{ t('copyLink') }}</button>
                  <span v-if="shareMessage" class="share-message">{{ shareMessage }}</span>
                </div>
                <div class="lineup-detail-meta">
                  <span class="chip">{{ labelByLanguage(activeLineup.utility_type, UTILITY_LABELS, UTILITY_LABELS_EN, language) }}</span>
                  <span class="chip">{{ labelByLanguage(activeLineup.side, SIDE_LABELS, SIDE_LABELS_EN, language) }}</span>
                  <span class="chip">{{ labelByLanguage(activeLineup.difficulty, DIFFICULTY_LABELS, DIFFICULTY_LABELS_EN, language) }}</span>
                </div>
                <p class="section-intro">{{ activeLineup.summary || activeLineup.purpose }}</p>
                <div class="point-triplet">
                  <span><strong>{{ t('standAimPoint') }}</strong>{{ activeLineup.start_point?.name }}</span>
                  <span><strong>{{ t('utilityAimPoint') }}</strong>{{ activeLineup.aim_point?.name }}</span>
                  <span><strong>{{ t('landingPoint') }}</strong>{{ activeLineup.land_point?.name }}</span>
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
                  <strong>{{ t('videoDemo') }}</strong>
                  <span>{{ activeVideoUrl }}</span>
                </a>
              </div>
            </template>

            <div v-else class="empty-landing-panel">
              <div class="kicker">{{ t('landingPointKicker') }}</div>
              <h2>{{ loadingDetail ? t('loadingUtilityDetail') : t('clickLandingPoint') }}</h2>
              <p class="muted">{{ t('landingPanelHint') }}</p>
            </div>
          </aside>
        </section>

        <div v-else class="empty-card">
          <p class="muted">{{ t('noMatchedMaps') }}</p>
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

.map-filter-select {
  width: 100%;
  margin-bottom: 8px;
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 8px;
  background-color: rgba(8,14,23,0.76);
  color: #fff;
  padding: 8px 28px 8px 10px;
  font-size: 13px;
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

.radar-actions,
.lineup-action-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.secondary-button.compact {
  padding: 7px 10px;
  font-size: 0.72rem;
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
  min-width: 100%;
  transition: width 0.18s ease;
}

.radar-scroll {
  overflow: auto;
  border-radius: 10px;
  overscroll-behavior: contain;
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
  gap: 12px;
  margin: 14px 0;
}

.lineup-section {
  display: grid;
  gap: 8px;
}

.lineup-section-title {
  color: #7a8ba0;
  font-size: 0.68rem;
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
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

.lineup-item.favorite {
  border-color: rgba(101,214,206,0.25);
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

.share-message {
  min-width: 0;
  color: #8de8be;
  font-size: 0.74rem;
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

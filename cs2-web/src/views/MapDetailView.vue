<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRoute } from 'vue-router';

import { api, resolveAssetUrl } from '../api';
import { useHead } from '../composables/useHead';
import TacticCard from '../components/TacticCard.vue';
import type { MapDetail, MapPoint, UtilityLineupDetail } from '../types';
import { label, DIFFICULTY_LABELS, SIDE_LABELS, UTILITY_LABELS } from '../utils/labels';

const route = useRoute();
const mapDetail = ref<MapDetail | null>(null);
const activeLandingPointId = ref<number | null>(null);
const activeLineupId = ref<number | null>(null);
const lightboxUrl = ref('');
const loadError = ref('');
const radarFallback = ref(false);

type LandingGroup = {
  point: MapPoint;
  lineups: UtilityLineupDetail[];
};

const radarUrl = computed(() => {
  if (!mapDetail.value) return '';
  if (radarFallback.value) return resolveAssetUrl(mapDetail.value.layout_url || mapDetail.value.cover_url);
  return resolveAssetUrl(`/static/assets/maps/radars/${mapDetail.value.slug}-radar.png`);
});

const landingGroups = computed<LandingGroup[]>(() => {
  if (!mapDetail.value) return [];
  const byPoint = new Map<number, UtilityLineupDetail[]>();
  for (const lineup of mapDetail.value.lineups) {
    const items = byPoint.get(lineup.land_point_id) || [];
    items.push(lineup);
    byPoint.set(lineup.land_point_id, items);
  }
  return Array.from(byPoint.entries())
    .map(([pointId, lineups]) => {
      const point = mapDetail.value?.points.find((item) => item.id === pointId);
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
    { role: '起点', point: lineup.start_point, color: '#65d6ce' },
    { role: '瞄点', point: lineup.aim_point, color: '#ff7a18' },
    { role: '落点', point: lineup.land_point, color: '#f5d76e' },
  ].filter((item) => item.point);
});

const lineupPath = computed(() =>
  selectedLineupPoints.value
    .map((item, index) => `${index === 0 ? 'M' : 'L'}${item.point.x} ${item.point.y}`)
    .join(' '),
);

const relatedTactics = computed(() => {
  if (!mapDetail.value || !activeLandingGroup.value) return [];
  const lineupIds = new Set(activeLandingGroup.value.lineups.map((lineup) => lineup.id));
  return mapDetail.value.tactics.filter((tactic) =>
    (tactic.lineup_ids || []).some((id) => lineupIds.has(id)),
  );
});

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

function openLightbox(url: string) {
  lightboxUrl.value = resolveAssetUrl(url);
}

onMounted(async () => {
  try {
    mapDetail.value = await api.getMapDetail(route.params.mapSlug as string);
    useHead(
      mapDetail.value?.name || '地图详情',
      `${mapDetail.value?.name || '地图'}的投掷物落点和道具线路`,
    );
  } catch {
    loadError.value = '加载失败，请刷新重试';
  }
});
</script>

<template>
  <div v-if="mapDetail" class="map-detail-root">
    <section class="map-detail-heading">
      <div>
        <div class="kicker">Utility Landing Map</div>
        <h1 class="map-title">{{ mapDetail.name }}</h1>
      </div>
      <p class="section-intro">{{ mapDetail.overview }}</p>
    </section>

    <section class="map-utility-layout">
      <div class="glass-panel radar-panel">
        <div class="radar-toolbar">
          <div>
            <strong>投掷落点</strong>
            <span class="muted">{{ landingGroups.length }} 个落点</span>
          </div>
          <button v-if="activeLandingGroup" class="secondary-button" @click="activeLandingPointId = null; activeLineupId = null">
            清除落点
          </button>
        </div>

        <div class="map-stage radar-stage">
          <img :src="radarUrl" :alt="mapDetail.name" @error="radarFallback = true" />
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
        <template v-if="activeLandingGroup">
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
              <span><strong>起点</strong>{{ activeLineup.start_point?.name }}</span>
              <span><strong>瞄点</strong>{{ activeLineup.aim_point?.name }}</span>
              <span><strong>落点</strong>{{ activeLineup.land_point?.name }}</span>
            </div>
            <ol v-if="activeLineup.steps?.length" class="lineup-steps">
              <li v-for="step in activeLineup.steps" :key="step">{{ step }}</li>
            </ol>
            <div v-if="activeLineup.media?.length" class="lineup-media-grid">
              <button
                v-for="url in activeLineup.media"
                :key="url"
                type="button"
                class="lineup-media-card"
                @click="openLightbox(url)"
              >
                <img :src="resolveAssetUrl(url)" alt="道具截图" loading="lazy" />
              </button>
            </div>
          </div>
        </template>

        <template v-else>
          <div class="empty-landing-panel">
            <div class="kicker">Landing Point</div>
            <h2>点击雷达上的落点</h2>
            <p class="muted">这里会显示该落点下所有烟、闪、火、雷线路。一个落点可以关联多个道具。</p>
          </div>
        </template>
      </aside>
    </section>

    <section v-if="activeLandingGroup" class="section-block">
      <div class="section-heading">
        <h2>关联战术</h2>
        <span class="muted">{{ relatedTactics.length }} 条</span>
      </div>
      <div v-if="relatedTactics.length" class="card-grid">
        <TacticCard v-for="tactic in relatedTactics" :key="tactic.id" :tactic="tactic" />
      </div>
      <div v-else class="empty-card">
        <p class="muted">这个落点暂时还没有关联战术</p>
      </div>
    </section>

    <div v-if="lightboxUrl" class="point-lightbox" @click="lightboxUrl = ''">
      <img :src="lightboxUrl" alt="utility media" />
    </div>
  </div>

  <div v-else-if="loadError" class="glass-panel load-state">
    <p class="muted">{{ loadError }}</p>
  </div>
  <div v-else class="glass-panel load-state">
    <p class="muted">加载中...</p>
  </div>
</template>

<style scoped>
.map-detail-root {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.map-detail-heading {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 18px;
  padding: 10px 0 0;
}

.map-detail-heading h1 {
  margin: 4px 0 0;
  font-size: 1.55rem;
}

.map-detail-heading .section-intro {
  max-width: 520px;
  margin: 0;
  text-align: right;
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
}

.lineup-media-card img {
  display: block;
  width: 100%;
  aspect-ratio: 16 / 10;
  object-fit: cover;
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

.load-state {
  padding: 40px;
  text-align: center;
}

@media (max-width: 920px) {
  .map-utility-layout {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .map-detail-heading {
    align-items: flex-start;
    flex-direction: column;
    gap: 8px;
  }

  .map-detail-heading .section-intro {
    max-width: none;
    text-align: left;
  }

  .landing-panel {
    min-height: 0;
  }
}
</style>

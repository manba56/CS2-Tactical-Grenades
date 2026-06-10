<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRoute } from 'vue-router';

import { api, resolveAssetUrl } from '../api';
import { useHead } from '../composables/useHead';
import TacticCard from '../components/TacticCard.vue';
import type { MapDetail } from '../types';
import { label, UTILITY_LABELS, SIDE_LABELS, DIFFICULTY_LABELS } from '../utils/labels';

const route = useRoute();
const mapDetail = ref<MapDetail | null>(null);
const activePointId = ref<number | null>(null);
const lightboxUrl = ref('');

type FilterKey = 'side' | 'utility_type' | 'goal' | 'phase' | 'difficulty' | 'tag';
const filterKeys: FilterKey[] = ['side', 'utility_type', 'goal', 'phase', 'difficulty', 'tag'];
const filterLabels: Record<FilterKey, string> = {
  side: '阵营', utility_type: '道具', goal: '目标', phase: '阶段', difficulty: '难度', tag: '标签',
};

const activeFilters = ref<Record<FilterKey, string>>({
  side: '', utility_type: '', goal: '', phase: '', difficulty: '', tag: '',
});

const filteredTactics = computed(() => {
  if (!mapDetail.value) return [];
  return mapDetail.value.tactics.filter((tactic) => {
    const f = activeFilters.value;
    if (f.side && tactic.side !== f.side) return false;
    if (f.goal && tactic.goal !== f.goal) return false;
    if (f.phase && tactic.phase !== f.phase) return false;
    if (f.difficulty && tactic.difficulty !== f.difficulty) return false;
    if (f.tag && !tactic.tags.includes(f.tag)) return false;
    if (f.utility_type && !tactic.utility_types.includes(f.utility_type)) return false;
    if (activePointId.value) {
      const pointLineupIds = lineupsForPoint(activePointId.value);
      const tacticLineupIds = tactic.lineup_ids || [];
      if (!tacticLineupIds.some((id) => pointLineupIds.has(id))) return false;
    }
    return true;
  });
});

const activePoint = computed(() => {
  if (!mapDetail.value || !activePointId.value) return null;
  return mapDetail.value.points.find((point) => point.id === activePointId.value) || null;
});

const relatedLineupsForActivePoint = computed(() => {
  if (!mapDetail.value || !activePointId.value) return [];
  return mapDetail.value.lineups.filter((lineup) =>
    lineup.start_point_id === activePointId.value ||
    lineup.aim_point_id === activePointId.value ||
    lineup.land_point_id === activePointId.value,
  );
});

const pointVideoEmbedUrl = computed(() => {
  const url = activePoint.value?.video_url || '';
  if (!url) return '';
  const bvMatch = url.match(/BV\w+/);
  return bvMatch ? `//player.bilibili.com/player.html?bvid=${bvMatch[0]}&page=1` : '';
});

const filterOptions = computed(() => {
  if (!mapDetail.value) return {} as Record<FilterKey, string[]>;
  const f = mapDetail.value.filters;
  return {
    side: f.sides,
    utility_type: f.utility_types,
    goal: f.goals,
    phase: f.phases,
    difficulty: f.difficulties,
    tag: f.tags,
  };
});

function filterLabel(key: string, val: string) {
  if (key === 'side') return label(val, SIDE_LABELS);
  if (key === 'utility_type') return label(val, UTILITY_LABELS);
  if (key === 'difficulty') return label(val, DIFFICULTY_LABELS);
  return val;
}

function lineupsForPoint(pointId: number) {
  const result = new Set<number>();
  if (!mapDetail.value) return result;
  for (const lineup of mapDetail.value.lineups) {
    if (
      lineup.start_point_id === pointId ||
      lineup.aim_point_id === pointId ||
      lineup.land_point_id === pointId
    ) {
      result.add(lineup.id);
    }
  }
  return result;
}

function togglePoint(pointId: number) {
  activePointId.value = activePointId.value === pointId ? null : pointId;
}

const loadError = ref('');

onMounted(async () => {
  try {
    mapDetail.value = await api.getMapDetail(route.params.mapSlug as string);
    useHead(mapDetail.value?.name || '地图详情', `${mapDetail.value?.name || '地图'}的全部战术——包含烟雾弹、闪光弹、燃烧弹线路`);
  } catch {
    loadError.value = '加载失败，请刷新重试';
  }
});
</script>

<template>
  <div v-if="mapDetail" class="map-detail-root">
    <!-- ── Filter bar (top) ──────────────────────────────────── -->
    <div class="filter-bar">
      <span class="filter-bar-title">筛选器</span>
      <label v-for="key in filterKeys" :key="key" class="filter-label">
        <span class="filter-label-text">{{ filterLabels[key] }}</span>
        <select v-model="activeFilters[key]" class="filter-select">
          <option value="">全部</option>
          <option v-for="val in filterOptions[key]" :key="val" :value="val">{{ filterLabel(key, val) }}</option>
        </select>
      </label>
      <button v-if="activePoint" class="point-filter-chip" @click="activePointId = null">
        点位：{{ activePoint.name }} ×
      </button>
      <span class="filter-count">{{ filteredTactics.length }} 条</span>
    </div>

    <!-- ── Map image ─────────────────────────────────────────── -->
    <div class="glass-panel map-panel">
      <div class="kicker">Map Layer</div>
      <h1 class="map-title">{{ mapDetail.name }}</h1>
      <p class="section-intro">{{ mapDetail.overview }}</p>
      <div class="map-point-layout section-block">
        <div class="map-stage radar-column">
          <img :src="resolveAssetUrl(`/static/assets/maps/radars/${mapDetail.slug}-radar.png`)" :alt="mapDetail.name" />
          <span
            v-for="point in mapDetail.points" :key="point.id"
            class="map-point clickable-point"
            :class="{ active: activePointId === point.id }"
            :style="{
              left: `${point.x}%`, top: `${point.y}%`,
              background: point.side === 'CT' ? '#65d6ce' : point.side === 'T' ? '#ff7a18' : '#ffffff',
            }"
            :title="`查看 ${point.name}`"
            @click="togglePoint(point.id)"
          />
          <span
            v-for="point in mapDetail.points" :key="'lbl-'+point.id"
            class="map-point-label clickable-label"
            :class="{ active: activePointId === point.id }"
            :style="{ left: `${point.x}%`, top: `${point.y}%` }"
            @click="togglePoint(point.id)"
          >{{ point.name }}</span>
        </div>

        <aside class="point-detail-panel">
          <template v-if="activePoint">
            <div class="inline-point-heading">
              <div>
                <div class="kicker">Point Detail</div>
                <h2>{{ activePoint.name }}</h2>
              </div>
              <span class="chip">{{ activePoint.side }}</span>
            </div>
            <p v-if="activePoint.description" class="section-intro">{{ activePoint.description }}</p>
            <p v-else class="muted">这个点位还没有说明，可以在后台点位管理里补充。</p>
            <div v-if="activePoint.tags?.length" class="chip-row">
              <span v-for="tag in activePoint.tags" :key="tag" class="chip">{{ tag }}</span>
            </div>

            <div class="point-media-grid">
              <button
                v-if="activePoint.aim_image_url"
                type="button"
                class="point-media-card"
                @click="lightboxUrl = resolveAssetUrl(activePoint.aim_image_url || '')"
              >
                <img :src="resolveAssetUrl(activePoint.aim_image_url)" alt="瞄点图" loading="lazy" />
                <span>瞄点图</span>
              </button>
              <button
                v-if="activePoint.effect_image_url"
                type="button"
                class="point-media-card"
                @click="lightboxUrl = resolveAssetUrl(activePoint.effect_image_url || '')"
              >
                <img :src="resolveAssetUrl(activePoint.effect_image_url)" alt="效果图" loading="lazy" />
                <span>效果图</span>
              </button>
            </div>

            <div v-if="pointVideoEmbedUrl" class="point-video">
              <iframe
                :src="pointVideoEmbedUrl"
                scrolling="no"
                border="0"
                frameborder="no"
                framespacing="0"
                allowfullscreen="true"
              />
            </div>
            <a v-else-if="activePoint.video_url" class="secondary-button" :href="activePoint.video_url" target="_blank" rel="noreferrer">
              打开视频
            </a>

            <div v-if="relatedLineupsForActivePoint.length" class="section-block">
              <div class="muted">关联道具线路</div>
              <div class="point-lineup-list">
                <div v-for="lineup in relatedLineupsForActivePoint" :key="lineup.id" class="point-lineup-item">
                  <strong>{{ lineup.title }}</strong>
                  <span class="chip">{{ filterLabel('utility_type', lineup.utility_type) }}</span>
                </div>
              </div>
            </div>
          </template>
          <template v-else>
            <div class="empty-point-detail">
              <div class="kicker">Point Detail</div>
              <h2>点击雷达点位查看资料</h2>
              <p class="muted">点位资料可在后台维护瞄点图、效果图和视频。</p>
            </div>
          </template>
        </aside>
      </div>
    </div>

    <!-- ── Side Tabs ─────────────────────────────────────────── -->
    <div class="side-tabs">
      <button :class="{ active: !activeFilters.side }" @click="activeFilters.side=''">全部</button>
      <button :class="{ active: activeFilters.side === 'T' }" @click="activeFilters.side='T'">
        <span class="side-dot t"></span>进攻方
      </button>
      <button :class="{ active: activeFilters.side === 'CT' }" @click="activeFilters.side='CT'">
        <span class="side-dot ct"></span>防守方
      </button>
    </div>

    <!-- ── Tactic list ───────────────────────────────────────── -->
    <section class="section-block">
      <div class="section-heading">
        <h2>战术列表</h2>
        <span class="muted">{{ filteredTactics.length }} 条匹配结果</span>
      </div>
      <div class="card-grid">
        <TacticCard v-for="tactic in filteredTactics" :key="tactic.id" :tactic="tactic" />
      </div>
    </section>
    <div v-if="lightboxUrl" class="point-lightbox" @click="lightboxUrl = ''">
      <img :src="lightboxUrl" alt="point media" />
    </div>
  </div>
  <div v-else-if="loadError" class="glass-panel" style="text-align:center;padding:40px;">
    <p class="muted">{{ loadError }}</p>
  </div>
  <div v-else class="glass-panel" style="text-align:center;padding:40px;">
    <p class="muted">加载中...</p>
  </div>
</template>

<style scoped>
.map-detail-root {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

/* ── Filter bar ────────────────────────────── */
.filter-bar {
  display: flex;
  align-items: flex-end;
  gap: 16px;
  flex-wrap: wrap;
  padding: 14px 18px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.1);
}
.filter-bar-title {
  font-weight: 700;
  font-size: 13px;
  color: #ff7a18;
  white-space: nowrap;
  padding-bottom: 6px;
  margin-right: 4px;
}
.filter-label {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.filter-label-text {
  font-size: 11px;
  color: #aaa;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.filter-select {
  padding: 7px 32px 7px 12px;
  border-radius: 8px;
  border: 1px solid #555;
  background: #1a1a2e;
  color: #fff;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%23888' d='M6 8L1 3h10z'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 10px center;
  min-width: 100px;
}
.filter-select:focus {
  outline: none;
  border-color: #ff7a18;
}
.filter-select option {
  background: #1a1a2e;
  color: #fff;
}
.filter-count {
  font-size: 12px;
  color: #888;
  white-space: nowrap;
  padding-bottom: 8px;
  margin-left: auto;
}

/* ── Side tabs ────────────────────────── */
.side-tabs { display: flex; gap: 8px; margin-bottom: 16px; }
.side-tabs button {
  padding: 8px 16px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.08);
  background: rgba(255,255,255,0.02); color: #8896ad; font-size: 0.85rem;
  cursor: pointer; transition: all 0.15s; display: flex; align-items: center; gap: 6px;
}
.side-tabs button:hover { border-color: rgba(255,122,24,0.3); color: #fff; }
.side-tabs button.active { background: rgba(255,122,24,0.15); border-color: rgba(255,122,24,0.3); color: #ffb88c; }
.side-dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; }
.side-dot.t { background: #e6a23c; }
.side-dot.ct { background: #409eff; }

/* ── Map panel ─────────────────────────────── */
.map-panel {
  /* full width */
}
.map-point-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.35fr) minmax(280px, 0.65fr);
  gap: 18px;
  align-items: start;
}
.radar-column {
  border-radius: 16px;
}
.point-detail-panel {
  min-height: 320px;
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 12px;
  padding: 16px;
  background: rgba(255,255,255,0.03);
}
.inline-point-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}
.inline-point-heading h2 {
  margin: 4px 0 0;
  font-size: 1.2rem;
}
.point-media-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin-top: 14px;
}
.point-media-card {
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 8px;
  overflow: hidden;
  background: rgba(255,255,255,0.03);
  color: #fff;
  padding: 0;
  cursor: pointer;
  text-align: left;
}
.point-media-card img {
  display: block;
  width: 100%;
  aspect-ratio: 16 / 10;
  object-fit: cover;
}
.point-media-card span {
  display: block;
  padding: 8px;
  font-size: 12px;
  color: #c7d2e1;
}
.point-video {
  position: relative;
  margin-top: 14px;
  padding-top: 56.25%;
  border-radius: 8px;
  overflow: hidden;
  background: #000;
}
.point-video iframe {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  border: 0;
}
.point-lineup-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 8px;
}
.point-lineup-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 8px;
  border-radius: 8px;
  background: rgba(255,255,255,0.04);
}
.empty-point-detail {
  min-height: 240px;
  display: flex;
  flex-direction: column;
  justify-content: center;
}
.clickable-point {
  cursor: pointer;
  transition: box-shadow 0.15s, transform 0.15s;
}
.clickable-point:hover,
.clickable-point.active {
  box-shadow: 0 0 0 4px rgba(255, 122, 24, 0.28), 0 0 16px rgba(255, 122, 24, 0.45);
  transform: translate(-50%, -50%) scale(1.2);
}
.clickable-label {
  cursor: pointer;
  user-select: none;
}
.clickable-label.active {
  color: #ffb88c;
  border-color: rgba(255, 122, 24, 0.55);
  background: rgba(255, 122, 24, 0.18);
}
.point-filter-chip {
  border: 1px solid rgba(255, 122, 24, 0.35);
  border-radius: 8px;
  background: rgba(255, 122, 24, 0.14);
  color: #ffb88c;
  padding: 7px 10px;
  cursor: pointer;
  font-size: 12px;
  white-space: nowrap;
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

@media (max-width: 640px) {
  .map-point-layout {
    grid-template-columns: 1fr;
  }
  .point-detail-panel {
    min-height: 0;
  }
  .filter-bar {
    gap: 10px;
    padding: 10px 14px;
  }
  .filter-select {
    min-width: 80px;
    padding: 7px 28px 7px 10px;
    font-size: 12px;
    /* Restore native appearance for mobile touch targets */
    appearance: auto;
    -webkit-appearance: auto;
    background-image: none;
    padding: 7px 10px;
  }
  .filter-count {
    margin-left: 0;
  }
}

@media (max-width: 480px) {
  .filter-bar {
    gap: 8px;
    padding: 8px 10px;
    border-radius: 12px;
  }
  .filter-select {
    min-width: 70px;
    font-size: 11px;
    appearance: auto;
    -webkit-appearance: auto;
    background-image: none;
    padding: 6px 6px;
  }
  .filter-label-text {
    font-size: 10px;
  }
}
</style>

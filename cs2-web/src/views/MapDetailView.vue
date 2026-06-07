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
    return true;
  });
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
      <span class="filter-count">{{ filteredTactics.length }} 条</span>
    </div>

    <!-- ── Map image ─────────────────────────────────────────── -->
    <div class="glass-panel map-panel">
      <div class="kicker">Map Layer</div>
      <h1 class="map-title">{{ mapDetail.name }}</h1>
      <p class="section-intro">{{ mapDetail.overview }}</p>
      <div class="map-stage section-block">
        <img :src="resolveAssetUrl(`/static/assets/maps/radars/${mapDetail.slug}-radar.png`)" :alt="mapDetail.name" />
        <span
          v-for="point in mapDetail.points" :key="point.id"
          class="map-point"
          :style="{
            left: `${point.x}%`, top: `${point.y}%`,
            background: point.side === 'CT' ? '#65d6ce' : point.side === 'T' ? '#ff7a18' : '#ffffff',
          }"
        />
        <span
          v-for="point in mapDetail.points" :key="'lbl-'+point.id"
          class="map-point-label"
          :style="{ left: `${point.x}%`, top: `${point.y}%` }"
        >{{ point.name }}</span>
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

@media (max-width: 640px) {
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

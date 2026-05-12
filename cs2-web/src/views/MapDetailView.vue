<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRoute } from 'vue-router';

import { api, resolveAssetUrl } from '../api';
import TacticCard from '../components/TacticCard.vue';
import type { MapDetail } from '../types';

const route = useRoute();
const mapDetail = ref<MapDetail | null>(null);
const filters = ref({
  side: '',
  utility_type: '',
  goal: '',
  phase: '',
  difficulty: '',
  tag: '',
});

const filteredTactics = computed(() => {
  if (!mapDetail.value) {
    return [];
  }

  return mapDetail.value.tactics.filter((tactic) => {
    if (filters.value.side && tactic.side !== filters.value.side) return false;
    if (filters.value.goal && tactic.goal !== filters.value.goal) return false;
    if (filters.value.phase && tactic.phase !== filters.value.phase) return false;
    if (filters.value.difficulty && tactic.difficulty !== filters.value.difficulty) return false;
    if (filters.value.tag && !tactic.tags.includes(filters.value.tag)) return false;
    if (filters.value.utility_type && !tactic.utility_types.includes(filters.value.utility_type)) return false;
    return true;
  });
});

onMounted(async () => {
  mapDetail.value = await api.getMapDetail(route.params.mapSlug as string);
});
</script>

<template>
  <section v-if="mapDetail" class="detail-grid">
    <div class="glass-panel">
      <div class="kicker">Map Layer</div>
      <h1 class="map-title">{{ mapDetail.name }}</h1>
      <p class="section-intro">{{ mapDetail.overview }}</p>
      <div class="map-stage section-block">
        <img :src="resolveAssetUrl(`/static/assets/maps/radars/${mapDetail.slug}-radar.png`)" :alt="mapDetail.name" />
        <template v-for="point in mapDetail.points" :key="point.id">
          <span
            class="map-point"
            :style="{
              left: `${point.x}%`,
              top: `${point.y}%`,
              background: point.side === 'CT' ? '#65d6ce' : point.side === 'T' ? '#ff7a18' : '#ffffff',
            }"
          />
          <span class="map-point-label" :style="{ left: `${point.x}%`, top: `${point.y}%` }">
            {{ point.name }}
          </span>
        </template>
      </div>
    </div>

    <aside class="glass-panel">
      <div class="section-heading">
        <h2>筛选器</h2>
      </div>
      <div class="filter-grid">
        <label>
          阵营
          <select v-model="filters.side" class="field-select">
            <option value="">全部</option>
            <option v-for="side in mapDetail.filters.sides" :key="side" :value="side">{{ side }}</option>
          </select>
        </label>
        <label>
          道具类型
          <select v-model="filters.utility_type" class="field-select">
            <option value="">全部</option>
            <option v-for="item in mapDetail.filters.utility_types" :key="item" :value="item">{{ item }}</option>
          </select>
        </label>
        <label>
          目标
          <select v-model="filters.goal" class="field-select">
            <option value="">全部</option>
            <option v-for="item in mapDetail.filters.goals" :key="item" :value="item">{{ item }}</option>
          </select>
        </label>
        <label>
          执行阶段
          <select v-model="filters.phase" class="field-select">
            <option value="">全部</option>
            <option v-for="item in mapDetail.filters.phases" :key="item" :value="item">{{ item }}</option>
          </select>
        </label>
        <label>
          难度
          <select v-model="filters.difficulty" class="field-select">
            <option value="">全部</option>
            <option v-for="item in mapDetail.filters.difficulties" :key="item" :value="item">{{ item }}</option>
          </select>
        </label>
        <label>
          标签
          <select v-model="filters.tag" class="field-select">
            <option value="">全部</option>
            <option v-for="item in mapDetail.filters.tags" :key="item" :value="item">{{ item }}</option>
          </select>
        </label>
      </div>
    </aside>
  </section>

  <section v-if="mapDetail" class="section-block">
    <div class="section-heading">
      <h2>战术列表</h2>
      <span class="muted">{{ filteredTactics.length }} 条匹配结果</span>
    </div>
    <div class="card-grid">
      <TacticCard v-for="tactic in filteredTactics" :key="tactic.id" :tactic="tactic" />
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';

import { api, resolveAssetUrl } from '../api';
import TacticCard from '../components/TacticCard.vue';
import type { MapSummary, TacticCard as TacticCardType } from '../types';

const maps = ref<MapSummary[]>([]);
const tactics = ref<TacticCardType[]>([]);
const filters = ref({
  map_slug: '',
  side: '',
  utility_type: '',
  difficulty: '',
  search: '',
});

const loadError = ref('');

async function load() {
  try {
    const [mapItems, tacticItems] = await Promise.all([api.getMaps(), api.getTactics(filters.value)]);
    maps.value = mapItems;
    tactics.value = tacticItems.items;
  } catch {
    loadError.value = '加载失败，请刷新重试';
  }
}

onMounted(load);
</script>

<template>
  <section class="section-heading">
    <div>
      <div class="kicker">Map-first Tactic Browser</div>
      <h1>地图库</h1>
    </div>
    <p class="section-intro">先按地图定位，再按阵营、难度和道具类型收窄结果。</p>
  </section>

  <section class="maps-grid">
    <router-link
      v-for="map in maps"
      :key="map.slug"
      class="map-card"
      :style="{ backgroundImage: `url(${resolveAssetUrl(map.cover_url)})` }"
      :to="`/maps/${map.slug}`"
    >
      <span class="chip strong">{{ map.name }}</span>
      <h3 class="map-title">{{ map.name }}</h3>
      <p>{{ map.overview }}</p>
    </router-link>
  </section>

  <section class="section-block glass-panel">
    <div class="section-heading">
      <h2>全局筛选</h2>
    </div>
    <div class="filter-grid">
      <label>
        地图
        <select v-model="filters.map_slug" class="field-select" @change="load">
          <option value="">全部地图</option>
          <option v-for="map in maps" :key="map.slug" :value="map.slug">{{ map.name }}</option>
        </select>
      </label>
      <label>
        阵营
        <select v-model="filters.side" class="field-select" @change="load">
          <option value="">全部</option>
          <option value="T">T</option>
          <option value="CT">CT</option>
        </select>
      </label>
      <label>
        道具
        <select v-model="filters.utility_type" class="field-select" @change="load">
          <option value="">全部</option>
          <option value="smoke">smoke</option>
          <option value="flash">flash</option>
          <option value="molotov">molotov</option>
          <option value="he">he</option>
        </select>
      </label>
      <label>
        难度
        <select v-model="filters.difficulty" class="field-select" @change="load">
          <option value="">全部</option>
          <option value="easy">easy</option>
          <option value="medium">medium</option>
          <option value="hard">hard</option>
        </select>
      </label>
      <label>
        搜索
        <input v-model="filters.search" class="field" placeholder="标题 / 标签 / 摘要" @keyup.enter="load" />
      </label>
      <button class="primary-button" @click="load">刷新列表</button>
    </div>
  </section>

  <section class="section-block">
    <div class="section-heading">
      <h2>战术结果</h2>
      <span class="muted">{{ tactics.length }} 条结果</span>
    </div>
    <div class="card-grid">
      <TacticCard v-for="tactic in tactics" :key="tactic.id" :tactic="tactic" />
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';

import { api, resolveAssetUrl } from '../api';
import TacticCard from '../components/TacticCard.vue';
import type { MapSummary, TacticCard as TacticCardType } from '../types';

const loading = ref(true);
const maps = ref<MapSummary[]>([]);
const featuredTactics = ref<TacticCardType[]>([]);
const latestTactics = ref<TacticCardType[]>([]);
const utilityQuickLinks = ref<{ type: string; count: number }[]>([]);

const loadError = ref('');

onMounted(async () => {
  try {
    const home = await api.getHome();
    maps.value = home.featured_maps;
    featuredTactics.value = home.featured_tactics;
    latestTactics.value = home.latest_tactics;
    utilityQuickLinks.value = home.utility_quick_links;
  } catch {
    loadError.value = '加载失败，请刷新重试';
  } finally {
    loading.value = false;
  }
});
</script>

<template>
  <section class="hero-grid">
    <div class="hero-card">
      <div class="kicker">Manual Playbook for CS2 Teams</div>
      <h1 class="hero-title">把战术、道具和执行顺序整理成一眼能看懂的地图资料站。</h1>
      <p class="hero-subtitle">
        以地图为入口，把点位、投掷物线路、执行步骤和战术配合拆开展示。首版聚焦现役比赛地图池，适合队内复盘和日常约战。
      </p>
      <div class="split-actions">
        <router-link class="primary-button" to="/maps">进入地图库</router-link>
        <router-link class="secondary-button" to="/favorites">查看收藏与最近浏览</router-link>
      </div>
    </div>

    <div class="glass-panel">
      <div class="section-heading">
        <h2>快速入口</h2>
      </div>
      <div class="chip-row">
        <span v-for="quick in utilityQuickLinks" :key="quick.type" class="chip strong">
          {{ quick.type }} · {{ quick.count }}
        </span>
      </div>
      <div class="section-block stats-grid">
        <div class="stat-card">
          <div class="muted">地图池</div>
          <strong>{{ maps.length }}</strong>
        </div>
        <div class="stat-card">
          <div class="muted">精选战术</div>
          <strong>{{ featuredTactics.length }}</strong>
        </div>
        <div class="stat-card">
          <div class="muted">最新上架</div>
          <strong>{{ latestTactics.length }}</strong>
        </div>
      </div>
    </div>
  </section>

  <section class="section-block">
    <div class="section-heading">
      <h2>热门地图</h2>
      <span class="section-intro">按地图进入，浏览点位与战术联动。</span>
    </div>
    <div class="maps-grid" v-if="!loading">
      <router-link
        v-for="map in maps"
        :key="map.slug"
        class="map-card"
        :style="{ backgroundImage: `url(${resolveAssetUrl(map.cover_url)})` }"
        :to="`/maps/${map.slug}`"
      >
        <div class="chip-row">
          <span class="chip strong">{{ map.name }}</span>
          <span class="chip">{{ map.tactic_count }} 个战术</span>
        </div>
        <h3 class="map-title">{{ map.name }}</h3>
        <p>{{ map.overview }}</p>
      </router-link>
    </div>
  </section>

  <section class="section-block">
    <div class="section-heading">
      <h2>精选执行</h2>
      <span class="section-intro">更适合直接抄进训练计划的成套配合。</span>
    </div>
    <div class="card-grid">
      <TacticCard v-for="tactic in featuredTactics" :key="tactic.id" :tactic="tactic" />
    </div>
  </section>

  <section class="section-block">
    <div class="section-heading">
      <h2>最新上线</h2>
      <span class="section-intro">方便队伍保持手册的新鲜度。</span>
    </div>
    <div class="card-grid">
      <TacticCard v-for="tactic in latestTactics" :key="tactic.id" :tactic="tactic" />
    </div>
  </section>
</template>

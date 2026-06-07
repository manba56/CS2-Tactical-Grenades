<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { useRoute } from 'vue-router';

import { api, resolveAssetUrl } from '../api';
import { useHead } from '../composables/useHead';
import SideNav from '../components/SideNav.vue';
import TacticCard from '../components/TacticCard.vue';
import type { CollectionSummary, MapSummary, TacticCard as TacticCardType } from '../types';

const route = useRoute();
const loading = ref(true);
const loadError = ref('');
const maps = ref<MapSummary[]>([]);
const allTactics = ref<TacticCardType[]>([]);
const collections = ref<CollectionSummary[]>([]);

const filterMapSlug = ref('');
const filterSide = ref('');
const filterDifficulty = ref('');
const searchWord = ref('');

function selectMap(slug: string) { filterMapSlug.value = filterMapSlug.value === slug ? '' : slug; }
function selectSide(side: string) { filterSide.value = side; }
function selectDifficulty(diff: string) { filterDifficulty.value = diff; }
function clearFilters() { filterMapSlug.value = ''; filterSide.value = ''; filterDifficulty.value = ''; }

onMounted(async () => {
  useHead('CS2战术百科', '以地图为入口的CS2战术手册，浏览投掷物线路、团队配合战术');
  const q = (route.query.search as string) || '';
  if (q) searchWord.value = q;
  try {
    const [homeData, tacticsData] = await Promise.all([
      api.getHome(),
      api.getTactics(q ? { search: q } : {}),
    ]);
    maps.value = (homeData.featured_maps || []).filter((m: MapSummary) => (m as any).tactic_count > 0);
    collections.value = (homeData as any).collections || [];
    allTactics.value = tacticsData.items;
  } catch {
    loadError.value = '加载失败，请刷新重试';
  } finally {
    loading.value = false;
  }
});

// Watch URL search param changes
watch(() => route.query.search, (val) => {
  searchWord.value = (val as string) || '';
});

const featuredTactics = computed(() => allTactics.value.filter(t => t.featured).slice(0, 3));
const hasFilters = computed(() => filterMapSlug.value || filterSide.value || filterDifficulty.value || searchWord.value);
const nonFeaturedTactics = computed(() => allTactics.value.filter(t => !t.featured));

const filteredTactics = computed(() => {
  let source = nonFeaturedTactics.value;
  if (filterMapSlug.value) source = source.filter(t => t.map.slug === filterMapSlug.value);
  if (filterSide.value) source = source.filter(t => t.side === filterSide.value);
  if (filterDifficulty.value) source = source.filter(t => t.difficulty === filterDifficulty.value);
  return source;
});
</script>

<template>
  <div class="home-root">
    <!-- Compact Hero -->
    <section class="hero-compact">
      <div class="hero-compact-left">
        <h1 class="hero-title">CS2 战术实验室</h1>
        <p class="hero-sub">全地图道具 & 战术手册</p>
      </div>
      <div class="hero-compact-right">
        <div class="hero-stat"><strong>{{ maps.length }}</strong><span>张地图</span></div>
        <div class="hero-stat"><strong>{{ allTactics.length }}</strong><span>条战术</span></div>
      </div>
    </section>

    <!-- Skeleton -->
    <div v-if="loading" class="loading-grid">
      <div v-for="n in 4" :key="'sk'+n" class="skeleton-card">
        <div class="skeleton-box" style="aspect-ratio:16/9"></div>
        <div class="skeleton-box skeleton-line" style="width:60%;margin-top:12px"></div>
      </div>
    </div>

    <!-- Search result banner -->
    <div v-if="searchWord && !loading" class="glass-panel" style="padding:10px 16px;margin-bottom:0;display:flex;align-items:center;justify-content:space-between">
      <span class="muted">搜索"<strong>{{ searchWord }}</strong>" — {{ allTactics.length }} 条结果</span>
      <button class="ghost-button" @click="searchWord='';filterMapSlug='';filterSide='';filterDifficulty=''">清除</button>
    </div>

    <!-- Sidebar layout -->
    <div class="home-layout" v-if="!loading">
      <SideNav
        :maps="maps"
        :all-tactics="allTactics"
        :active-map-slug="filterMapSlug"
        :active-side="filterSide"
        :active-difficulty="filterDifficulty"
        @select-map="selectMap"
        @select-side="selectSide"
        @select-difficulty="selectDifficulty"
        @clear-filters="clearFilters"
      />

      <div class="home-main">
        <!-- Featured -->
        <section v-if="!hasFilters && featuredTactics.length" class="section-block">
          <div class="section-heading"><h2>推荐战术</h2></div>
          <div class="card-grid">
            <TacticCard v-for="t in featuredTactics" :key="'feat-'+t.id" :tactic="t" />
          </div>
        </section>

        <!-- Collections -->
        <section v-if="!hasFilters && collections.length" class="section-block">
          <div class="section-heading">
            <h2>战术合集</h2>
            <router-link to="/collections" class="chip">全部</router-link>
          </div>
          <div class="collection-scroll">
            <router-link v-for="col in collections" :key="col.id" :to="`/collections/${col.slug}`" class="collection-card">
              <img v-if="col.cover_url" :src="resolveAssetUrl(col.cover_url)" alt="" />
              <div class="collection-info"><strong>{{ col.title }}</strong><span class="muted">{{ col.tactic_count }} 条</span></div>
            </router-link>
          </div>
        </section>

        <!-- Filtered tactics -->
        <section class="section-block">
          <div class="section-heading">
            <h2>{{ filterMapSlug || filterSide || filterDifficulty ? '筛选结果' : '全部战术' }}</h2>
            <span class="muted">{{ filteredTactics.length }} 条</span>
          </div>
          <div class="card-grid">
            <TacticCard v-for="t in filteredTactics" :key="t.id" :tactic="t" />
          </div>
          <div v-if="filteredTactics.length===0" class="empty-card"><p class="muted">没有匹配的战术</p></div>
        </section>
      </div>
    </div>

    <div v-if="loadError" class="empty-card"><p class="muted">{{ loadError }}</p></div>
  </div>
</template>

<style scoped>
.home-root { display: flex; flex-direction: column; gap: 20px; }

/* Compact Hero */
.hero-compact { display: flex; align-items: center; justify-content: space-between; padding: 20px 0 8px; flex-wrap: wrap; gap: 16px; }
.hero-compact-left {}
.hero-title { font-size: 1.6rem; font-weight: 900; margin: 0; color: #fff; }
.hero-sub { color: #8896ad; font-size: 0.9rem; margin: 4px 0 0; }
.hero-compact-right { display: flex; gap: 20px; }
.hero-stat { text-align: center; }
.hero-stat strong { display: block; font-size: 1.6rem; font-weight: 800; color: #ff7a18; }
.hero-stat span { font-size: 0.72rem; color: #7788a0; text-transform: uppercase; letter-spacing: 0.08em; }

/* Layout */
.home-layout { display: flex; gap: 24px; align-items: flex-start; }
.home-main { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 20px; }

/* Sidebar */
.side-nav { width: 260px; flex-shrink: 0; position: sticky; top: 72px; max-height: calc(100vh - 90px); }

/* Collections */
.collection-scroll { display: flex; gap: 12px; overflow-x: auto; padding-bottom: 4px; }
.collection-card { flex: 0 0 220px; border-radius: 12px; overflow: hidden; background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06); text-decoration: none; color: inherit; transition: border-color 0.15s; }
.collection-card:hover { border-color: #ff7a18; }
.collection-card img { width: 100%; height: 100px; object-fit: cover; display: block; }
.collection-info { padding: 10px 12px; }
.collection-info strong { display: block; font-size: 0.85rem; }
.collection-info .muted { font-size: 0.7rem; }

@media (max-width: 640px) {
  .hero-compact { padding: 14px 0 4px; }
  .hero-title { font-size: 1.3rem; }
  .hero-stat strong { font-size: 1.3rem; }
  .home-layout { flex-direction: column; }
  .side-nav { width: 100%; position: static; max-height: none; }
  .home-main { width: 100%; }
}

@media (max-width: 480px) {
  .hero-title { font-size: 1.1rem; }
  .hero-sub { font-size: 0.8rem; }
}
</style>

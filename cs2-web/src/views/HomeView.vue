<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { useRoute } from 'vue-router';

import { api, resolveAssetUrl } from '../api';
import { useHead } from '../composables/useHead';
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
const searchWord = ref('');

onMounted(async () => {
  useHead('CS2战术百科', '以地图为入口的CS2战术手册，浏览投掷物线路、团队配合战术');
  // Read search query from URL
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
const nonFeaturedTactics = computed(() => allTactics.value.filter(t => !t.featured));

const filteredTactics = computed(() => {
  const source = nonFeaturedTactics.value;
  return source.filter(t => {
    if (filterMapSlug.value && t.map.slug !== filterMapSlug.value) return false;
    if (filterSide.value && t.side !== filterSide.value) return false;
    return true;
  });
});
</script>

<template>
  <div class="home-root">
    <!-- ── Hero ────────────────────────────────────────────── -->
    <section class="hero-panel">
      <div class="hero-text">
        <div class="kicker">CS2 Tactics Playbook</div>
        <h1 class="hero-title">战术手册</h1>
        <p class="hero-subtitle">
          以地图为入口，按阵营、道具、执行阶段浏览。快速找到下一局要用的配合。
        </p>
        <div class="hero-actions">
          <router-link class="primary-button" to="/maps">浏览全部地图</router-link>
          <router-link class="secondary-button" to="/favorites">我的收藏</router-link>
        </div>
      </div>
      <div class="hero-stats">
        <div class="hero-stat">
          <strong>{{ maps.length }}</strong>
          <span>张地图</span>
        </div>
        <div class="hero-stat">
          <strong>{{ allTactics.length }}</strong>
          <span>条战术</span>
        </div>
      </div>
    </section>

    <!-- ── Loading skeleton ──────────────────────────────────── -->
    <section v-if="loading" class="section-block">
      <div class="loading-grid">
        <div v-for="n in 4" :key="'sk'+n" class="skeleton-card">
          <div class="skeleton-box" style="aspect-ratio:16/9"></div>
          <div class="skeleton-box skeleton-line" style="width:60%;margin-top:12px"></div>
          <div class="skeleton-box skeleton-line" style="width:80%;margin-top:6px"></div>
        </div>
      </div>
    </section>

    <!-- ── Search info ──────────────────────────────────────── -->
    <div v-if="searchWord && !loading" class="glass-panel" style="padding:12px 18px;margin-bottom:0">
      <span class="muted">搜索"<strong>{{ searchWord }}</strong>"的结果 — {{ allTactics.length }} 条战术</span>
      <button class="ghost-button" style="margin-left:12px" @click="searchWord='';filterMapSlug='';filterSide=''">清除</button>
    </div>

    <!-- ── 推荐战术 ──────────────────────────────────────────── -->
    <section v-if="!loading && featuredTactics.length" class="section-block">
      <div class="section-heading">
        <h2>推荐战术</h2>
      </div>
      <div class="card-grid">
        <TacticCard v-for="t in featuredTactics" :key="'feat-'+t.id" :tactic="t" />
      </div>
    </section>

    <!-- ── Map entry cards (horizontal scroll) ─────────────── -->
    <section class="section-block" v-if="!loading && maps.length">
      <div class="section-heading">
        <h2>快速选图</h2>
      </div>
      <div class="map-scroll">
        <router-link
          v-for="map in maps"
          :key="map.slug"
          class="map-entry-card"
          :to="`/maps/${map.slug}`"
        >
          <img :src="resolveAssetUrl(map.cover_url)" :alt="map.name" class="map-entry-icon" />
          <div class="map-entry-body">
            <strong>{{ map.name }}</strong>
            <span class="chip">{{ map.tactic_count }} 条战术</span>
          </div>
        </router-link>
      </div>
    </section>

    <!-- ── Collections ─────────────────────────────────────── -->
    <section v-if="!loading && collections.length" class="section-block">
      <div class="section-heading">
        <h2>战术合集</h2>
        <router-link to="/collections" class="chip">全部</router-link>
      </div>
      <div class="collection-scroll">
        <router-link
          v-for="col in collections" :key="col.id"
          :to="`/collections/${col.slug}`"
          class="collection-card"
        >
          <img v-if="col.cover_url" :src="resolveAssetUrl(col.cover_url)" alt="" />
          <div class="collection-info">
            <strong>{{ col.title }}</strong>
            <span class="muted">{{ col.tactic_count }} 条战术</span>
          </div>
        </router-link>
      </div>
    </section>

    <!-- ── All tactics ─────────────────────────────────────── -->
    <section class="section-block" v-if="!loading">
      <div class="section-heading">
        <h2>全部战术</h2>
        <span class="muted" v-if="!loadError">{{ filteredTactics.length }} 条</span>
      </div>

      <!-- Filter chips -->
      <div class="home-filter-bar">
        <div class="filter-row">
          <button
            class="filter-chip"
            :class="{ active: !filterMapSlug }"
            @click="filterMapSlug = ''"
          >全部地图</button>
          <button
            v-for="map in maps"
            :key="map.slug"
            class="filter-chip"
            :class="{ active: filterMapSlug === map.slug }"
            @click="filterMapSlug = map.slug"
          >{{ map.name }}</button>
        </div>
        <div class="filter-row">
          <button
            class="filter-chip"
            :class="{ active: !filterSide }"
            @click="filterSide = ''"
          >全部阵营</button>
          <button
            class="filter-chip"
            :class="{ active: filterSide === 'T' }"
            @click="filterSide = 'T'"
          >T 进攻</button>
          <button
            class="filter-chip"
            :class="{ active: filterSide === 'CT' }"
            @click="filterSide = 'CT'"
          >CT 防守</button>
        </div>
      </div>

      <div class="card-grid">
        <TacticCard v-for="tactic in filteredTactics" :key="tactic.id" :tactic="tactic" />
      </div>

      <div v-if="filteredTactics.length === 0" class="empty-card">
        <p class="muted">没有匹配的战术</p>
      </div>
    </section>

    <div v-if="loadError" class="empty-card">
      <p class="muted">{{ loadError }}</p>
    </div>
  </div>
</template>

<style scoped>
.home-root {
  display: flex;
  flex-direction: column;
  gap: 32px;
}

/* ── Hero ─────────────────────────────── */
.hero-panel {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 24px;
  padding: 48px 0 16px;
  position: relative;
}
.hero-panel::before {
  content: "";
  position: absolute;
  top: -100px;
  left: 50%;
  transform: translateX(-50%);
  width: 600px;
  height: 400px;
  background: radial-gradient(ellipse, rgba(255, 122, 24, 0.08), transparent 70%);
  pointer-events: none;
}
.hero-text {
  max-width: 600px;
  position: relative;
  z-index: 1;
}
.hero-title {
  margin: 0 0 16px;
  font-size: clamp(2.4rem, 6vw, 3.6rem);
  font-weight: 900;
  letter-spacing: -0.02em;
  background: linear-gradient(135deg, #fff 0%, #ffc08a 50%, #ff7a18 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}
.hero-subtitle {
  color: #8896ad;
  font-size: 1.1rem;
  line-height: 1.7;
  margin-bottom: 22px;
  max-width: 480px;
}
.hero-actions {
  display: flex;
  gap: 12px;
}
.hero-actions .primary-button {
  padding: 10px 24px;
  font-size: 0.95rem;
  border-radius: 10px;
}
.hero-stats {
  display: flex;
  gap: 32px;
  flex-shrink: 0;
  position: relative;
  z-index: 1;
}
.hero-stat {
  text-align: center;
  padding: 16px 24px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  backdrop-filter: blur(12px);
}
.hero-stat strong {
  display: block;
  font-size: 2.2rem;
  font-weight: 900;
  background: linear-gradient(135deg, #ff7a18, #ffb866);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}
.hero-stat span {
  font-size: 0.8rem;
  color: #7788a0;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

/* ── Map scroll ────────────────────────── */
.map-scroll {
  display: flex;
  gap: 14px;
  overflow-x: auto;
  padding-bottom: 8px;
  scroll-snap-type: x mandatory;
  -webkit-overflow-scrolling: touch;
}
.map-scroll::-webkit-scrollbar {
  height: 6px;
}
.map-scroll::-webkit-scrollbar-thumb {
  background: #333;
  border-radius: 3px;
}
.map-entry-card {
  flex: 0 0 220px;
  scroll-snap-align: start;
  display: flex;
  flex-direction: column;
  border-radius: 20px;
  overflow: hidden;
  background: rgba(13, 20, 31, 0.9);
  border: 1px solid rgba(255, 255, 255, 0.08);
  transition: border-color 0.2s, transform 0.15s;
  text-decoration: none;
  color: inherit;
}
.map-entry-card:hover {
  border-color: #ff7a18;
  transform: translateY(-2px);
}
.map-entry-icon {
  width: 100%;
  aspect-ratio: 2 / 1;
  object-fit: cover;
}
.map-entry-body {
  padding: 12px 14px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.map-entry-body strong {
  font-size: 14px;
}

/* ── Filter chips ──────────────────────── */
.home-filter-bar {
  margin-bottom: 18px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.filter-row {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
.filter-chip {
  padding: 5px 14px;
  border-radius: 999px;
  border: 1px solid #444;
  background: #1a1a2e;
  color: #ddd;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s;
}
.filter-chip:hover {
  border-color: #ff7a18;
  color: #fff;
}
.filter-chip.active {
  background: #ff7a18;
  border-color: #ff7a18;
  color: #fff;
  font-weight: 700;
}

@media (max-width: 640px) {
  .hero-panel {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
    padding: 24px 0 8px;
  }
  .hero-stats {
    gap: 16px;
  }
  .hero-stat strong {
    font-size: 1.5rem;
  }
  .filter-chip {
    padding: 8px 16px;
    font-size: 13px;
  }
}

@media (max-width: 480px) {
  .hero-panel {
    padding: 16px 0 4px;
    gap: 12px;
  }
  .hero-title {
    font-size: 1.6rem;
  }
  .hero-subtitle {
    font-size: 0.9rem;
  }
  .hero-stats {
    gap: 12px;
    flex-wrap: wrap;
  }
  .hero-stat strong {
    font-size: 1.3rem;
  }
  .hero-stat span {
    font-size: 0.72rem;
  }
  .filter-chip {
    padding: 9px 18px;
    font-size: 14px;
  }
  .filter-row {
    gap: 4px;
  }
  .home-root {
    gap: 20px;
  }
}

/* ── Collections ─────────────────────────── */
.collection-scroll {
  display: flex;
  gap: 12px;
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
  padding-bottom: 4px;
}
.collection-card {
  flex: 0 0 260px;
  border-radius: 14px;
  overflow: hidden;
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.08);
  text-decoration: none;
  color: inherit;
  transition: border-color 0.15s;
}
.collection-card:hover {
  border-color: #ff7a18;
}
.collection-card img {
  width: 100%;
  height: 120px;
  object-fit: cover;
  display: block;
}
.collection-info {
  padding: 12px 14px;
}
.collection-info strong {
  display: block;
  font-size: 0.95rem;
  margin-bottom: 4px;
}
.collection-info .muted {
  font-size: 0.75rem;
}

@media (max-width: 480px) {
  .collection-card {
    flex: 0 0 200px;
  }
  .collection-card img {
    height: 100px;
  }
}
</style>

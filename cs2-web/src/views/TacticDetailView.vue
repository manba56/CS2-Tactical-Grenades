<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import { api, resolveAssetUrl } from '../api';
import { useHead } from '../composables/useHead';
import { label, DIFFICULTY_LABELS, SIDE_LABELS, UTILITY_LABELS } from '../utils/labels';
import TacticCard from '../components/TacticCard.vue';
import { useSessionStore } from '../stores/session';
import type { TacticDetail } from '../types';

const route = useRoute();
const router = useRouter();
const session = useSessionStore();

const tactic = ref<TacticDetail | null>(null);
const error = ref('');
const isFavorite = computed(() => tactic.value?.is_favorite ?? false);
const lightboxUrl = ref('');
const showRadar = ref(false);
const bilibiliEmbedUrl = computed(() => {
  const url = (tactic.value as any)?.video_url as string | undefined;
  if (!url) return null;
  const bvMatch = url.match(/BV\w+/);
  return bvMatch ? `//player.bilibili.com/player.html?bvid=${bvMatch[0]}&page=1` : null;
});
const routeShots = computed(() => tactic.value?.screenshots?.filter(s => s.type === 'route') ?? []);
const spotShots = computed(() => tactic.value?.screenshots?.filter(s => (s.type || 'spot') !== 'route') ?? []);
const galleryUrls = computed(() => {
  const urls = [
    ...routeShots.value.map((shot) => resolveAssetUrl(shot.url)),
    ...spotShots.value.map((shot) => resolveAssetUrl(shot.url)),
    ...(tactic.value?.steps || []).flatMap((step) => step.lineup?.media || []).map((url) => resolveAssetUrl(url)),
  ];
  return Array.from(new Set(urls.filter(Boolean)));
});
const quickExecItems = computed(() => (tactic.value?.steps || []).map((step) => ({
  order: step.order,
  role: step.role,
  action: step.instruction,
  utility: step.lineup?.utility_type || step.type,
  stand: step.lineup?.start_point?.name || '',
  aim: step.lineup?.aim_point?.name || '',
  land: step.lineup?.land_point?.name || '',
})));

async function load() {
  error.value = '';
  lightboxUrl.value = '';
  showRadar.value = false;
  try {
    tactic.value = await api.getTacticDetail(route.params.tacticSlug as string, session.token);
    if (tactic.value) {
      const cover = tactic.value.cover_url || '';
      useHead(tactic.value.title, tactic.value.summary, cover || undefined);
    }
    if (session.token && tactic.value) {
      await api.trackRecent(tactic.value.id, session.token);
    }
  } catch (err) {
    tactic.value = null;
    error.value = err instanceof Error ? err.message : '加载失败';
  }
}

async function toggleFavorite() {
  if (!session.token || !tactic.value) {
    router.push(`/login?redirect=${encodeURIComponent(route.fullPath)}&action=favorite`);
    return;
  }
  if (tactic.value.is_favorite) {
    await api.removeFavorite(tactic.value.id, session.token);
    tactic.value.is_favorite = false;
  } else {
    await api.addFavorite(tactic.value.id, session.token);
    tactic.value.is_favorite = true;
  }
}

function copyShareLink() {
  const text = tactic.value
    ? `${tactic.value.title} — CS2 Tactics Lab\n${window.location.href}`
    : window.location.href;
  navigator.clipboard.writeText(text);
}

function openLightbox(url: string) {
  lightboxUrl.value = url;
}

function moveLightbox(delta: number) {
  if (!lightboxUrl.value || galleryUrls.value.length === 0) return;
  const current = galleryUrls.value.indexOf(lightboxUrl.value);
  const next = (current + delta + galleryUrls.value.length) % galleryUrls.value.length;
  lightboxUrl.value = galleryUrls.value[next];
}

// Auto-favorite after login redirect
onMounted(async () => {
  await load();
  if (route.query.action === 'favorite' && session.token && tactic.value && !tactic.value.is_favorite) {
    try {
      await api.addFavorite(tactic.value.id, session.token);
      tactic.value.is_favorite = true;
    } catch (_) { /* ignore */ }
    router.replace({ query: {} });
  }
});

watch(() => route.params.tacticSlug, async () => {
  await load();
});

function routePath(r: { points: { x: number; y: number }[] }): string {
  if (!r.points || r.points.length < 2) return '';
  return r.points.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x}% ${p.y}%`).join(' ');
}

</script>

<template>
  <section v-if="error" class="empty-card danger">{{ error }}</section>
  <template v-else-if="tactic">
    <section class="detail-grid">
      <div class="detail-hero">
        <div class="glass-panel">
          <div class="eyebrow-row">
            <span class="chip strong">{{ tactic.map.name }}</span>
            <span class="chip">{{ label(tactic.side, SIDE_LABELS) }}</span>
            <span class="chip">{{ tactic.phase }}</span>
            <span class="chip">{{ label(tactic.difficulty, DIFFICULTY_LABELS) }}</span>
          </div>
          <h1 class="detail-title">{{ tactic.title }}</h1>
          <p class="section-intro">{{ tactic.summary }}</p>
          <div class="chip-row">
            <span class="chip strong">{{ tactic.goal }}</span>
            <span class="chip">{{ tactic.players }} 人参与</span>
            <span v-for="tag in tactic.tags" :key="tag" class="chip">{{ tag }}</span>
          </div>
          <div class="split-actions section-block">
            <button class="primary-button" @click="toggleFavorite">
              {{ isFavorite ? '取消收藏' : '收藏战术' }}
            </button>
            <button class="secondary-button" @click="copyShareLink">复制链接</button>
            <router-link class="secondary-button" :to="`/maps/${tactic.map.slug}`">返回地图页</router-link>
          </div>
        </div>

        <!-- Anchor nav -->
        <nav class="anchor-nav">
          <a v-if="bilibiliEmbedUrl" href="#video">视频</a>
          <a v-if="routeShots.length" href="#routes">路线截图</a>
          <a href="#note">注意事项</a>
          <a v-if="tactic.routes?.length" href="#path">进攻路线</a>
          <a v-if="tactic.steps?.length" href="#steps">执行顺序</a>
          <a v-if="tactic.related?.length" href="#related">相关战术</a>
        </nav>

        <div v-if="quickExecItems.length" class="glass-panel quick-exec-panel">
          <div class="section-heading">
            <h2>快速执行模式</h2>
            <span class="muted">{{ tactic.players }} 人执行</span>
          </div>
          <div class="quick-exec-grid">
            <article v-for="item in quickExecItems" :key="item.order" class="quick-exec-card">
              <div class="quick-exec-top">
                <strong>#{{ item.order }} {{ item.role }}</strong>
                <span class="chip">{{ label(item.utility, UTILITY_LABELS) }}</span>
              </div>
              <p>{{ item.action }}</p>
              <div class="quick-exec-meta">
                <span v-if="item.stand">站位：{{ item.stand }}</span>
                <span v-if="item.aim">瞄点：{{ item.aim }}</span>
                <span v-if="item.land">落点：{{ item.land }}</span>
              </div>
            </article>
          </div>
        </div>

      <!-- B站视频演示 -->
      <div v-if="bilibiliEmbedUrl" id="video" class="glass-panel bilibili-stage">
          <div class="section-heading">
            <h2>视频演示</h2>
          </div>
          <div class="bilibili-wrapper">
            <iframe
              :src="bilibiliEmbedUrl"
              scrolling="no"
              border="0"
              frameborder="no"
              framespacing="0"
              allowfullscreen="true"
              class="bilibili-iframe"
            />
          </div>
        </div>

        <!-- Route screenshots as primary map view -->
        <div v-if="routeShots.length" id="routes" class="glass-panel map-stage">
          <div class="section-heading">
            <h2>路线截图</h2>
            <button class="secondary-button" @click="showRadar = !showRadar">
              {{ showRadar ? '隐藏雷达底图' : '显示雷达底图' }}
            </button>
          </div>
          <div class="screenshot-main-list">
            <div v-for="(shot, idx) in routeShots" :key="idx" class="shot-full-block">
              <p class="shot-desc">{{ shot.description || `路线截图 #${idx + 1}` }}</p>
              <img
                :src="resolveAssetUrl(shot.url)"
                :alt="shot.description || `路线截图 #${idx + 1}`"
                class="shot-full-img"
                loading="lazy"
                @click="openLightbox(resolveAssetUrl(shot.url))"
              />
            </div>
          </div>
        </div>

        <!-- Radar template (collapsible) -->
        <div v-if="showRadar" class="glass-panel map-stage">
          <div class="section-heading">
            <h2>雷达底图</h2>
          </div>
          <img :src="resolveAssetUrl(tactic.map_radar_url)" :alt="tactic.map.name" />
          <template v-for="point in tactic.map_points" :key="point.id">
            <span
              class="map-point"
              :style="{
                left: `${point.x}%`,
                top: `${point.y}%`,
                background: point.side === 'CT' ? '#65d6ce' : point.side === 'T' ? '#ff7a18' : '#ffffff',
              }"
            />
          </template>
        </div>
      </div>

      <aside id="note" class="glass-panel">
        <div class="section-heading">
          <h2>执行注意事项</h2>
        </div>
        <p>{{ tactic.note }}</p>
        <div class="section-block">
          <div class="muted">所需道具</div>
          <div class="chip-row">
            <span v-for="utility in tactic.utility_types" :key="utility" class="chip strong">{{ label(utility, UTILITY_LABELS) }}</span>
          </div>
        </div>

        <!-- Spot screenshots in sidebar -->
        <div v-if="spotShots.length" class="section-block">
          <div class="muted">点位截图</div>
          <div class="screenshot-grid">
            <div v-for="(shot, idx) in spotShots" :key="idx" class="screenshot-card" @click="openLightbox(resolveAssetUrl(shot.url))">
              <img :src="resolveAssetUrl(shot.url)" :alt="shot.description || `点位 #${idx + 1}`" loading="lazy" />
              <span class="screenshot-caption">{{ shot.description || `点位 #${idx + 1}` }}</span>
            </div>
          </div>
        </div>
      </aside>
    </section>

    <section v-if="tactic.routes && tactic.routes.length" id="path" class="glass-panel section-block">
      <div class="section-heading">
        <h2>进攻路线</h2>
      </div>
      <div class="route-map-stage">
        <img :src="resolveAssetUrl(tactic.map_radar_url)" :alt="tactic.map.name" />
        <svg class="route-overlay" viewBox="0 0 100 100" preserveAspectRatio="none">
          <defs>
            <marker
              v-for="r in tactic.routes" :key="'arrow-'+r.player"
              :id="`arrow-${r.player}`"
              viewBox="0 0 10 10" refX="10" refY="5"
              markerWidth="6" markerHeight="6" orient="auto"
            >
              <path d="M0,0 L10,5 L0,10 Z" :fill="r.color" />
            </marker>
          </defs>
          <path
            v-for="r in tactic.routes" :key="r.player"
            :d="routePath(r)"
            :stroke="r.color"
            stroke-width="0.8"
            fill="none"
            stroke-linecap="round"
            :marker-end="`url(#arrow-${r.player})`"
          />
        </svg>
        <!-- Route legend -->
        <div class="route-legend">
          <div v-for="r in tactic.routes" :key="r.player" class="route-legend-item">
            <span class="dot" :style="{ background: r.color }" />
            P{{ r.player }} {{ r.label }}
          </div>
        </div>
      </div>
    </section>

    <section id="steps" class="section-block glass-panel">
      <div class="section-heading">
        <h2>执行顺序</h2>
      </div>
      <div class="timeline">
        <article v-for="step in tactic.steps" :key="step.order" class="timeline-item">
          <div class="timeline-item-header">
            <strong>#{{ step.order }} · {{ step.role }}</strong>
            <span class="chip">{{ step.type }}</span>
          </div>
          <p>{{ step.instruction }}</p>
          <div v-if="step.lineup" class="section-block">
            <div class="chip-row">
              <span class="chip strong">{{ step.lineup.title }}</span>
              <span class="chip">{{ label(step.lineup.utility_type, UTILITY_LABELS) }}</span>
              <span class="chip">{{ step.lineup.difficulty }}</span>
            </div>
            <p class="muted">{{ step.lineup.purpose }}</p>
            <!-- Screenshot gallery — all media images -->
            <div v-if="step.lineup.media.length" class="screenshot-grid">
              <div
                v-for="(url, idx) in step.lineup.media" :key="idx"
                class="screenshot-card"
                @click="openLightbox(resolveAssetUrl(url))"
              >
                <img :src="resolveAssetUrl(url)" :alt="`${step.lineup.title} ${idx + 1}`" loading="lazy" />
                <span class="screenshot-caption">瞄点截图 {{ idx + 1 }}</span>
              </div>
            </div>
            <!-- Empty placeholder when no media -->
            <div v-else class="screenshot-placeholder">
              <span>在此添加道具瞄点截图</span>
            </div>
          </div>
        </article>
      </div>
    </section>

    <section id="related" v-if="tactic.related?.length" class="section-block">
      <div class="section-heading">
        <h2>相关战术</h2>
      </div>
      <div class="card-grid">
        <TacticCard v-for="item in tactic.related" :key="item.id" :tactic="item" />
      </div>
    </section>
    <!-- Lightbox -->
    <div v-if="lightboxUrl" class="screenshot-lightbox" @click="lightboxUrl = ''">
      <button class="lightbox-nav prev" @click.stop="moveLightbox(-1)">‹</button>
      <img :src="lightboxUrl" alt="enlarged screenshot" />
      <button class="lightbox-nav next" @click.stop="moveLightbox(1)">›</button>
    </div>
  </template>
</template>

<style scoped>
.bilibili-wrapper {
  position: relative;
  width: 100%;
  padding-top: 56.25%;
  background: #000;
  border-radius: 8px;
  overflow: hidden;
}
.bilibili-iframe {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  border: none;
}
.quick-exec-panel {
  margin-top: 12px;
}
.quick-exec-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 10px;
}
.quick-exec-card {
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 8px;
  padding: 12px;
  background: rgba(255,255,255,0.03);
}
.quick-exec-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.quick-exec-card p {
  margin: 10px 0;
  color: #e5eefb;
  line-height: 1.5;
}
.quick-exec-meta {
  display: flex;
  flex-direction: column;
  gap: 4px;
  color: #8fa1b8;
  font-size: 12px;
}
.lightbox-nav {
  position: fixed;
  top: 50%;
  transform: translateY(-50%);
  z-index: 101;
  width: 44px;
  height: 44px;
  border-radius: 50%;
  border: 1px solid rgba(255,255,255,0.22);
  background: rgba(8,14,23,0.82);
  color: #fff;
  font-size: 28px;
  cursor: pointer;
}
.lightbox-nav.prev { left: 20px; }
.lightbox-nav.next { right: 20px; }

@media (max-width: 480px) {
  .bilibili-wrapper {
    border-radius: 4px;
  }
  .section-heading h2 {
    font-size: 1.1rem;
  }
}

/* ── Anchor nav ───────────────────────────── */
.anchor-nav {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  padding: 12px 0 4px;
  margin-top: 8px;
}
.anchor-nav a {
  padding: 5px 12px;
  border-radius: 999px;
  background: rgba(255,255,255,0.06);
  color: #aaa;
  font-size: 0.78rem;
  text-decoration: none;
  border: 1px solid rgba(255,255,255,0.08);
  transition: all 0.15s;
  scroll-behavior: smooth;
}
.anchor-nav a:hover {
  background: rgba(255,122,24,0.15);
  border-color: #ff7a18;
  color: #ff7a18;
}
html {
  scroll-behavior: smooth;
}

@media (max-width: 480px) {
  .anchor-nav {
    flex-wrap: nowrap;
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
    padding-bottom: 8px;
  }
  .anchor-nav a {
    flex-shrink: 0;
  }
}
</style>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import { api, resolveAssetUrl } from '../api';
import { useHead } from '../composables/useHead';
import { useI18n } from '../composables/useI18n';
import {
  DIFFICULTY_LABELS,
  DIFFICULTY_LABELS_EN,
  PHASE_LABELS,
  PHASE_LABELS_EN,
  SIDE_LABELS,
  SIDE_LABELS_EN,
  UTILITY_LABELS,
  UTILITY_LABELS_EN,
  labelByLanguage,
} from '../utils/labels';
import TacticCard from '../components/TacticCard.vue';
import { useSessionStore } from '../stores/session';
import type { ProgressMap, TacticDetail, TrainingStatus } from '../types';
import {
  TRAINING_STATUSES,
  progressLabel,
  readLocalTacticProgress,
  setProgressValue,
  writeLocalTacticProgress,
} from '../utils/personalPlaybook';

const route = useRoute();
const router = useRouter();
const session = useSessionStore();
const { language, t } = useI18n();

const tactic = ref<TacticDetail | null>(null);
const error = ref('');
const isFavorite = computed(() => tactic.value?.is_favorite ?? false);
const lightboxUrl = ref('');
const showRadar = ref(false);
const detailMode = ref<'execute' | 'detail'>('execute');
const completedExecOrders = ref<number[]>([]);
const shareNotice = ref('');
const tacticProgress = ref<ProgressMap>(readLocalTacticProgress());
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
  type: step.type,
  utility: step.lineup?.utility_type || step.type,
  difficulty: step.lineup?.difficulty || '',
  lineupId: step.lineup?.id || null,
  lineupTitle: step.lineup?.title || '',
  lineupSummary: step.lineup?.summary || step.lineup?.purpose || '',
  stand: step.lineup?.start_point?.name || '',
  aim: step.lineup?.aim_point?.name || '',
  land: step.lineup?.land_point?.name || '',
  mapUrl: step.lineup && tactic.value
    ? `/maps?map=${tactic.value.map.slug}&land=${step.lineup.land_point_id}&lineup=${step.lineup.id}`
    : '',
})));
const completedExecCount = computed(() => completedExecOrders.value.length);
const execProgress = computed(() =>
  quickExecItems.value.length ? Math.round((completedExecCount.value / quickExecItems.value.length) * 100) : 0,
);
const tacticUtilityLineups = computed(() => {
  const unique = new Map<number, TacticDetail['lineups'][number]>();
  for (const lineup of tactic.value?.lineups || []) {
    unique.set(lineup.id, lineup);
  }
  return Array.from(unique.values());
});
const tacticUtilityGroups = computed(() => {
  const groups = new Map<string, typeof tacticUtilityLineups.value>();
  for (const lineup of tacticUtilityLineups.value) {
    const items = groups.get(lineup.utility_type) || [];
    items.push(lineup);
    groups.set(lineup.utility_type, items);
  }
  return Array.from(groups.entries()).map(([utility, lineups]) => ({ utility, lineups }));
});
const activeTacticProgress = computed(() =>
  tactic.value ? tacticProgress.value[String(tactic.value.id)] : undefined,
);

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
      const bundle = await api.getFavorites(session.token);
      tacticProgress.value = bundle.tactic_progress || {};
    }
  } catch (err) {
    tactic.value = null;
    error.value = err instanceof Error ? err.message : t('loadingFailedRefresh');
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
  shareNotice.value = t('linkCopied');
  window.setTimeout(() => {
    shareNotice.value = '';
  }, 1800);
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

function toggleExecDone(order: number) {
  completedExecOrders.value = completedExecOrders.value.includes(order)
    ? completedExecOrders.value.filter((item) => item !== order)
    : [...completedExecOrders.value, order];
}

function isExecDone(order: number) {
  return completedExecOrders.value.includes(order);
}

function resetExecProgress() {
  completedExecOrders.value = [];
}

async function setCurrentTacticProgress(status: TrainingStatus | null) {
  if (!tactic.value) return;
  tacticProgress.value = setProgressValue(tacticProgress.value, tactic.value.id, status);
  if (session.token) {
    try {
      await api.setTacticProgress(tactic.value.id, status, session.token);
    } catch {
      // Keep optimistic UI; the next detail load will reconcile.
    }
  } else {
    writeLocalTacticProgress(tacticProgress.value);
  }
}

function utilityMapUrl(lineup: TacticDetail['lineups'][number]) {
  return `/maps?map=${tactic.value?.map.slug || ''}&land=${lineup.land_point_id}&lineup=${lineup.id}`;
}

function utilityLabel(value: string) {
  return labelByLanguage(value, UTILITY_LABELS, UTILITY_LABELS_EN, language.value);
}

function difficultyLabel(value: string) {
  return labelByLanguage(value, DIFFICULTY_LABELS, DIFFICULTY_LABELS_EN, language.value);
}

function sideLabel(value: string) {
  return labelByLanguage(value, SIDE_LABELS, SIDE_LABELS_EN, language.value);
}

function phaseLabel(value: string) {
  return labelByLanguage(value, PHASE_LABELS, PHASE_LABELS_EN, language.value);
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
  completedExecOrders.value = [];
  detailMode.value = 'execute';
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
            <span class="chip">{{ sideLabel(tactic.side) }}</span>
            <span class="chip">{{ phaseLabel(tactic.phase) }}</span>
            <span class="chip">{{ difficultyLabel(tactic.difficulty) }}</span>
          </div>
          <h1 class="detail-title">{{ tactic.title }}</h1>
          <p class="section-intro">{{ tactic.summary }}</p>
          <div class="chip-row">
            <span class="chip strong">{{ tactic.goal }}</span>
            <span class="chip">{{ tactic.players }} {{ t('participants') }}</span>
            <span v-for="tag in tactic.tags" :key="tag" class="chip">{{ tag }}</span>
          </div>
          <div class="split-actions section-block">
            <button class="primary-button" @click="toggleFavorite">
              {{ isFavorite ? t('unfavorite') : t('favoriteTactic') }}
            </button>
            <button class="secondary-button" @click="copyShareLink">{{ t('copyLink') }}</button>
            <router-link class="secondary-button" :to="`/maps/${tactic.map.slug}`">{{ t('backToMap') }}</router-link>
            <span v-if="shareNotice" class="share-notice">{{ shareNotice }}</span>
          </div>
          <div class="progress-picker">
            <span class="muted">{{ progressLabel(activeTacticProgress, language) }}</span>
            <button
              class="progress-chip"
              :class="{ active: !activeTacticProgress }"
              type="button"
              @click="setCurrentTacticProgress(null)"
            >
              {{ progressLabel(undefined, language) }}
            </button>
            <button
              v-for="option in TRAINING_STATUSES"
              :key="option.value"
              class="progress-chip"
              :class="{ active: activeTacticProgress === option.value }"
              type="button"
              @click="setCurrentTacticProgress(option.value)"
            >
              {{ language === 'en' ? option.en : option.zh }}
            </button>
          </div>
          <div class="mode-switch">
            <button class="ghost-button" :class="{ active: detailMode === 'execute' }" @click="detailMode = 'execute'">{{ t('executeChecklist') }}</button>
            <button class="ghost-button" :class="{ active: detailMode === 'detail' }" @click="detailMode = 'detail'">{{ t('fullDetail') }}</button>
          </div>
        </div>

        <!-- Anchor nav -->
        <nav class="anchor-nav">
          <a v-if="bilibiliEmbedUrl" href="#video">{{ t('video') }}</a>
          <a v-if="routeShots.length" href="#routes">{{ t('routeScreenshots') }}</a>
          <a href="#note">{{ t('notes') }}</a>
          <a v-if="tactic.routes?.length" href="#path">{{ t('attackRoute') }}</a>
          <a v-if="tactic.steps?.length" href="#steps">{{ t('executeOrder') }}</a>
          <a v-if="tactic.related?.length" href="#related">{{ t('relatedTactics') }}</a>
        </nav>

        <div v-if="quickExecItems.length" class="glass-panel quick-exec-panel">
          <div class="section-heading">
            <h2>{{ t('executeChecklist') }}</h2>
            <div class="exec-progress">
              <span class="muted">{{ completedExecCount }} / {{ quickExecItems.length }} {{ t('completed') }}</span>
              <button class="secondary-button small" type="button" @click="resetExecProgress">{{ t('reset') }}</button>
            </div>
          </div>
          <div class="exec-progress-bar">
            <span :style="{ width: `${execProgress}%` }" />
          </div>
          <div class="quick-exec-grid">
            <article v-for="item in quickExecItems" :key="item.order" class="quick-exec-card" :class="{ done: isExecDone(item.order) }">
              <div class="quick-exec-top">
                <button class="exec-check" type="button" @click="toggleExecDone(item.order)">
                  {{ isExecDone(item.order) ? '✓' : item.order }}
                </button>
                <div>
                  <strong>{{ item.role }}</strong>
                  <small v-if="item.lineupTitle">{{ item.lineupTitle }}</small>
                </div>
                <span class="chip">{{ utilityLabel(item.utility) }}</span>
              </div>
              <p>{{ item.action }}</p>
              <div class="quick-exec-meta">
                <span v-if="item.stand">{{ t('stand') }}: {{ item.stand }}</span>
                <span v-if="item.aim">{{ t('aim') }}: {{ item.aim }}</span>
                <span v-if="item.land">{{ t('landingPoint') }}: {{ item.land }}</span>
              </div>
              <p v-if="item.lineupSummary" class="muted exec-summary">{{ item.lineupSummary }}</p>
              <div class="quick-exec-actions">
                <router-link v-if="item.mapUrl" class="secondary-button small" :to="item.mapUrl">{{ t('viewUtilityLanding') }}</router-link>
                <span v-if="item.difficulty" class="chip">{{ difficultyLabel(item.difficulty) }}</span>
              </div>
            </article>
          </div>
        </div>

      <!-- Video demo -->
      <div v-if="detailMode === 'detail' && bilibiliEmbedUrl" id="video" class="glass-panel bilibili-stage">
          <div class="section-heading">
            <h2>{{ t('videoDemo') }}</h2>
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
        <div v-if="detailMode === 'detail' && routeShots.length" id="routes" class="glass-panel map-stage">
          <div class="section-heading">
            <h2>{{ t('routeScreenshots') }}</h2>
            <button class="secondary-button" @click="showRadar = !showRadar">
              {{ showRadar ? t('hideRadarBase') : t('showRadarBase') }}
            </button>
          </div>
          <div class="screenshot-main-list">
            <div v-for="(shot, idx) in routeShots" :key="idx" class="shot-full-block">
              <p class="shot-desc">{{ shot.description || `${t('routeScreenshotFallback')} #${idx + 1}` }}</p>
              <img
                :src="resolveAssetUrl(shot.url)"
                :alt="shot.description || `${t('routeScreenshotFallback')} #${idx + 1}`"
                class="shot-full-img"
                loading="lazy"
                @click="openLightbox(resolveAssetUrl(shot.url))"
              />
            </div>
          </div>
        </div>

        <!-- Radar template (collapsible) -->
        <div v-if="detailMode === 'detail' && showRadar" class="glass-panel map-stage">
          <div class="section-heading">
            <h2>{{ t('radarBase') }}</h2>
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
          <h2>{{ t('executionNotes') }}</h2>
        </div>
        <p>{{ tactic.note }}</p>
        <div class="section-block">
          <div class="muted">{{ t('requiredUtility') }}</div>
          <div class="chip-row">
            <span v-for="utility in tactic.utility_types" :key="utility" class="chip strong">{{ utilityLabel(utility) }}</span>
          </div>
        </div>

        <div v-if="tacticUtilityGroups.length" class="section-block utility-plan">
          <div class="muted">{{ t('utilityCombo') }}</div>
          <section v-for="group in tacticUtilityGroups" :key="group.utility" class="utility-plan-group">
            <strong>{{ utilityLabel(group.utility) }}</strong>
            <router-link
              v-for="lineup in group.lineups"
              :key="lineup.id"
              class="utility-plan-item"
              :to="utilityMapUrl(lineup)"
            >
              <span>{{ lineup.title }}</span>
              <small>{{ lineup.start_point?.name }} -> {{ lineup.aim_point?.name }} -> {{ lineup.land_point?.name }}</small>
            </router-link>
          </section>
        </div>

        <!-- Spot screenshots in sidebar -->
        <div v-if="spotShots.length" class="section-block">
          <div class="muted">{{ t('pointScreenshots') }}</div>
          <div class="screenshot-grid">
            <div v-for="(shot, idx) in spotShots" :key="idx" class="screenshot-card" @click="openLightbox(resolveAssetUrl(shot.url))">
              <img :src="resolveAssetUrl(shot.url)" :alt="shot.description || `${t('pointScreenshotFallback')} #${idx + 1}`" loading="lazy" />
              <span class="screenshot-caption">{{ shot.description || `${t('pointScreenshotFallback')} #${idx + 1}` }}</span>
            </div>
          </div>
        </div>
      </aside>
    </section>

    <section v-if="detailMode === 'detail' && tactic.routes && tactic.routes.length" id="path" class="glass-panel section-block">
      <div class="section-heading">
        <h2>{{ t('attackRoute') }}</h2>
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

    <section v-if="detailMode === 'detail'" id="steps" class="section-block glass-panel">
      <div class="section-heading">
        <h2>{{ t('executeOrder') }}</h2>
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
              <span class="chip">{{ utilityLabel(step.lineup.utility_type) }}</span>
              <span class="chip">{{ difficultyLabel(step.lineup.difficulty) }}</span>
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
                <span class="screenshot-caption">{{ t('aimScreenshot') }} {{ idx + 1 }}</span>
              </div>
            </div>
            <!-- Empty placeholder when no media -->
            <div v-else class="screenshot-placeholder">
              <span>{{ t('addUtilityAimImage') }}</span>
            </div>
          </div>
        </article>
      </div>
    </section>

    <section id="related" v-if="tactic.related?.length" class="section-block">
      <div class="section-heading">
        <h2>{{ t('relatedTactics') }}</h2>
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
.mode-switch,
.exec-progress,
.quick-exec-actions,
.progress-picker {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}
.mode-switch {
  margin-top: 12px;
}
.mode-switch .active {
  border-color: rgba(255,122,24,0.45);
  background: rgba(255,122,24,0.12);
  color: #ffb88c;
}
.share-notice {
  color: #8de8be;
  font-size: 0.8rem;
}
.progress-picker {
  margin-top: 10px;
  padding: 8px;
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 8px;
  background: rgba(255,255,255,0.03);
}
.progress-chip {
  min-height: 28px;
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 999px;
  background: rgba(255,255,255,0.03);
  color: #bcc8d6;
  padding: 5px 9px;
  font-size: 0.72rem;
}
.progress-chip:hover,
.progress-chip.active {
  border-color: rgba(255,122,24,0.4);
  background: rgba(255,122,24,0.12);
  color: #ffbd82;
}
.exec-progress-bar {
  height: 6px;
  overflow: hidden;
  border-radius: 999px;
  background: rgba(255,255,255,0.08);
  margin-bottom: 12px;
}
.exec-progress-bar span {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #65d6ce, #ff7a18);
  transition: width 0.2s ease;
}
.quick-exec-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
  gap: 10px;
}
.quick-exec-card {
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 8px;
  padding: 12px;
  background: rgba(255,255,255,0.03);
}
.quick-exec-card.done {
  border-color: rgba(101,214,206,0.35);
  background: rgba(101,214,206,0.08);
}
.quick-exec-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.quick-exec-top > div {
  display: grid;
  gap: 2px;
  min-width: 0;
  flex: 1;
}
.quick-exec-top small {
  color: #8fa1b8;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.exec-check {
  flex: 0 0 auto;
  width: 34px;
  height: 34px;
  border: 1px solid rgba(255,255,255,0.16);
  border-radius: 999px;
  background: rgba(255,255,255,0.05);
  color: #fff;
  font-weight: 900;
}
.quick-exec-card.done .exec-check {
  background: #65d6ce;
  color: #06131d;
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
.exec-summary {
  font-size: 0.78rem;
}
.secondary-button.small {
  padding: 7px 11px;
  font-size: 0.76rem;
}
.utility-plan {
  display: grid;
  gap: 10px;
}
.utility-plan-group {
  display: grid;
  gap: 7px;
}
.utility-plan-group > strong {
  color: #ffb88c;
  font-size: 0.8rem;
}
.utility-plan-item {
  display: grid;
  gap: 2px;
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 8px;
  background: rgba(255,255,255,0.03);
  padding: 9px;
}
.utility-plan-item:hover {
  border-color: rgba(255,122,24,0.36);
  background: rgba(255,122,24,0.09);
}
.utility-plan-item small {
  color: #8fa1b8;
  line-height: 1.35;
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

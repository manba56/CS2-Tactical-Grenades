<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import { api, resolveAssetUrl } from '../api';
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

async function load() {
  try {
    tactic.value = await api.getTacticDetail(route.params.tacticSlug as string, session.token);
    if (session.token && tactic.value) {
      await api.trackRecent(tactic.value.id, session.token);
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : '加载失败';
  }
}

async function toggleFavorite() {
  if (!session.token || !tactic.value) {
    router.push(`/login?redirect=${encodeURIComponent(route.fullPath)}`);
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

function routePath(r: { points: { x: number; y: number }[] }): string {
  if (!r.points || r.points.length < 2) return '';
  return r.points.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x}% ${p.y}%`).join(' ');
}

onMounted(load);
</script>

<template>
  <section v-if="error" class="empty-card danger">{{ error }}</section>
  <template v-else-if="tactic">
    <section class="detail-grid">
      <div class="detail-hero">
        <div class="glass-panel">
          <div class="eyebrow-row">
            <span class="chip strong">{{ tactic.map.name }}</span>
            <span class="chip">{{ tactic.side }}</span>
            <span class="chip">{{ tactic.phase }}</span>
            <span class="chip">{{ tactic.difficulty }}</span>
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
            <router-link class="secondary-button" :to="`/maps/${tactic.map.slug}`">返回地图页</router-link>
          </div>
        </div>

        <div class="glass-panel map-stage">
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

      <section v-if="tactic.screenshots && tactic.screenshots.length" class="glass-panel section-block">
        <div class="section-heading">
          <h2>点位截图</h2>
          <span class="chip">{{ tactic.screenshots.length }} 张截图</span>
        </div>
        <div class="screenshot-grid">
          <div v-for="(shot, idx) in tactic.screenshots" :key="idx" class="screenshot-card" @click="lightboxUrl = resolveAssetUrl(shot.url)">
            <img :src="resolveAssetUrl(shot.url)" :alt="shot.description || `截图 #${idx + 1}`" />
            <span class="screenshot-caption">{{ shot.description || `截图 #${idx + 1}` }}</span>
          </div>
        </div>
      </section>

      <aside class="glass-panel">
        <div class="section-heading">
          <h2>执行注意事项</h2>
        </div>
        <p>{{ tactic.note }}</p>
        <div class="section-block">
          <div class="muted">所需道具</div>
          <div class="chip-row">
            <span v-for="utility in tactic.utility_types" :key="utility" class="chip strong">{{ utility }}</span>
          </div>
        </div>
      </aside>
    </section>

    <section v-if="tactic.routes && tactic.routes.length" class="glass-panel section-block">
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

    <section class="section-block glass-panel">
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
              <span class="chip">{{ step.lineup.utility_type }}</span>
              <span class="chip">{{ step.lineup.difficulty }}</span>
            </div>
            <p class="muted">{{ step.lineup.purpose }}</p>
            <!-- Screenshot gallery — all media images -->
            <div v-if="step.lineup.media.length" class="screenshot-grid">
              <div
                v-for="(url, idx) in step.lineup.media" :key="idx"
                class="screenshot-card"
                @click="lightboxUrl = resolveAssetUrl(url)"
              >
                <img :src="resolveAssetUrl(url)" :alt="`${step.lineup.title} ${idx + 1}`" />
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

    <section class="section-block" v-if="tactic.related.length">
      <div class="section-heading">
        <h2>相关战术</h2>
      </div>
      <div class="card-grid">
        <TacticCard v-for="item in tactic.related" :key="item.id" :tactic="item" />
      </div>
    </section>
    <!-- Lightbox -->
    <div v-if="lightboxUrl" class="screenshot-lightbox" @click="lightboxUrl = ''">
      <img :src="lightboxUrl" alt="enlarged screenshot" />
    </div>
  </template>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';

import { resolveAssetUrl } from '../api';
import { useI18n } from '../composables/useI18n';
import type { TacticCard as TacticCardType } from '../types';
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

const props = defineProps<{
  tactic: TacticCardType;
}>();

const imageBroken = ref(false);
const detailTo = computed(() => `/tactics/${props.tactic.slug}`);
const visibleUtilities = computed(() => props.tactic.utility_types.slice(0, 3));
const extraUtilities = computed(() => Math.max(props.tactic.utility_types.length - visibleUtilities.value.length, 0));
const { language, t } = useI18n();
</script>

<template>
  <router-link class="tactic-card" :to="detailTo" :aria-label="`${t('viewTacticDetail')}：${tactic.title}`">
    <div class="tactic-card-cover-wrapper">
      <img
        v-if="tactic.cover_url && !imageBroken"
        :src="resolveAssetUrl(tactic.cover_url)"
        :alt="tactic.title"
        class="tactic-card-cover"
        loading="lazy"
        @error="imageBroken = true"
      />
      <div v-else class="tactic-card-cover-placeholder">
        <strong>{{ tactic.map.name }}</strong>
        <span>{{ tactic.goal || t('tactic') }}</span>
      </div>
      <div class="tactic-card-badges">
        <span class="map-badge">{{ tactic.map.name }}</span>
        <span class="side-badge" :class="'side-' + tactic.side">
          {{ labelByLanguage(tactic.side, SIDE_LABELS, SIDE_LABELS_EN, language) }}
        </span>
      </div>
    </div>
    <div class="tactic-card-body">
      <div class="tactic-card-meta">
        <span>{{ labelByLanguage(tactic.phase, PHASE_LABELS, PHASE_LABELS_EN, language) }}</span>
        <span>{{ tactic.players }}{{ t('playersSuffix') }}</span>
        <span class="diff-badge" :class="'diff-' + tactic.difficulty">
          {{ labelByLanguage(tactic.difficulty, DIFFICULTY_LABELS, DIFFICULTY_LABELS_EN, language) }}
        </span>
      </div>
      <h3 class="tactic-card-title">{{ tactic.title }}</h3>
      <p class="tactic-card-goal">{{ tactic.goal }}</p>
      <p class="tactic-card-summary">{{ tactic.summary }}</p>
      <div class="chip-row">
        <span
          v-for="utility in visibleUtilities"
          :key="utility"
          class="chip util-badge"
          :class="'util-' + utility"
        >
          {{ labelByLanguage(utility, UTILITY_LABELS, UTILITY_LABELS_EN, language) }}
        </span>
        <span v-if="extraUtilities" class="chip muted-chip">+{{ extraUtilities }}</span>
      </div>
      <span class="tactic-card-link">{{ t('viewDetail') }}</span>
    </div>
  </router-link>
</template>

<style scoped>
.tactic-card {
  display: flex;
  flex-direction: column;
  height: 100%;
  color: inherit;
  text-decoration: none;
}

.tactic-card-cover-wrapper {
  aspect-ratio: 16 / 9;
}

.tactic-card-cover {
  height: 100%;
  transition: transform 0.24s ease;
}

.tactic-card:hover .tactic-card-cover {
  transform: scale(1.035);
}

.tactic-card-cover-placeholder {
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  gap: 4px;
  width: 100%;
  height: 100%;
  padding: 16px;
  background:
    linear-gradient(135deg, rgba(255,122,24,0.18), transparent 55%),
    linear-gradient(180deg, rgba(20,31,47,0.95), rgba(8,13,22,0.95));
  color: #fff;
}

.tactic-card-cover-placeholder strong {
  font-size: 1rem;
}

.tactic-card-cover-placeholder span {
  color: #a7b4c6;
  font-size: 0.78rem;
}

.tactic-card-badges {
  position: absolute;
  inset: 10px 10px auto;
  display: flex;
  justify-content: space-between;
  gap: 8px;
  pointer-events: none;
}

.map-badge,
.side-badge {
  max-width: 70%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  border: 1px solid rgba(255,255,255,0.14);
  border-radius: 999px;
  background: rgba(8,13,22,0.78);
  color: #eef4fb;
  padding: 4px 8px;
  font-size: 0.72rem;
  font-weight: 700;
}

.side-badge {
  max-width: 30%;
}

.side-T {
  color: #ffd18a;
  border-color: rgba(230,162,60,0.35);
}

.side-CT {
  color: #9dccff;
  border-color: rgba(64,158,255,0.35);
}

.tactic-card-body {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 9px;
  padding: 13px 14px 14px;
}

.tactic-card-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 22px;
  color: #8796aa;
  font-size: 0.72rem;
  white-space: nowrap;
}

.tactic-card-title {
  display: -webkit-box;
  min-height: 2.55em;
  margin: 0;
  overflow: hidden;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  line-height: 1.28;
  font-size: 1rem;
}

.tactic-card-goal {
  display: -webkit-box;
  margin: 0;
  overflow: hidden;
  color: #ffbd82;
  font-size: 0.82rem;
  font-weight: 700;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 1;
}

.tactic-card-summary {
  display: -webkit-box;
  min-height: 3em;
  margin: 0;
  overflow: hidden;
  color: #aeb9cb;
  font-size: 0.84rem;
  line-height: 1.5;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.chip-row {
  min-height: 28px;
  gap: 6px;
  margin-top: auto;
}

.chip {
  padding: 4px 8px;
  font-size: 0.72rem;
}

.muted-chip {
  color: #91a3ba;
  background: rgba(255,255,255,0.05);
}

.tactic-card-link {
  color: #7cdad3;
  font-size: 0.78rem;
  font-weight: 800;
}

.tactic-card:hover .tactic-card-link {
  color: #a6f0eb;
}
</style>

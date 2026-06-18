<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';

import { api } from '../api';
import { useHead } from '../composables/useHead';
import { useI18n } from '../composables/useI18n';
import TacticCard from '../components/TacticCard.vue';
import { useSessionStore } from '../stores/session';
import type { FavoriteBundle, TacticDetail, TrainingStatus, UtilityLineupDetail } from '../types';
import {
  SIDE_LABELS,
  SIDE_LABELS_EN,
  UTILITY_LABELS,
  UTILITY_LABELS_EN,
  labelByLanguage,
} from '../utils/labels';
import {
  TRAINING_STATUSES,
  progressLabel,
} from '../utils/personalPlaybook';

const session = useSessionStore();
const { language, t } = useI18n();
const bundle = ref<FavoriteBundle | null>(null);
const error = ref('');
const filterMap = ref('');
const filterSide = ref('');
const filterUtility = ref('');
const filterProgress = ref('');

type PlaybookItem = {
  id: string;
  kind: 'tactic' | 'lineup';
  map: { slug: string; name: string };
  side: 'T' | 'CT';
  utility_types: string[];
  progress?: TrainingStatus;
  title: string;
  summary: string;
  to: string;
  tactic?: TacticDetail;
  lineup?: UtilityLineupDetail;
};

const allPersonalTactics = computed(() => {
  if (!bundle.value) return [];
  const seen = new Set<number>();
  return [...bundle.value.favorites, ...bundle.value.recent].filter((item) => {
    if (seen.has(item.id)) return false;
    seen.add(item.id);
    return true;
  });
});

const mapOptions = computed(() => Array.from(new Map(allPersonalTactics.value.map(t => [t.map.slug, t.map])).values()));
const utilityOptions = computed(() => Array.from(new Set(allPersonalTactics.value.flatMap(t => t.utility_types))).sort());

function matchesFilters(item: FavoriteBundle['favorites'][number]) {
  if (filterMap.value && item.map.slug !== filterMap.value) return false;
  if (filterSide.value && item.side !== filterSide.value) return false;
  if (filterUtility.value && !item.utility_types.includes(filterUtility.value)) return false;
  return true;
}

const filteredFavorites = computed(() => bundle.value ? bundle.value.favorites.filter(matchesFilters) : []);
const filteredRecent = computed(() => bundle.value ? bundle.value.recent.filter(matchesFilters) : []);
const frequentBundle = computed(() => allPersonalTactics.value.filter(matchesFilters).slice(0, 6));

const favoriteLineupItems = computed<PlaybookItem[]>(() => (bundle.value?.favorite_lineups || []).map((lineup) => ({
  id: `lineup-${lineup.id}`,
  kind: 'lineup',
  map: lineup.map || { slug: String(lineup.map_id), name: lineup.land_point?.name || lineup.title },
  side: lineup.side,
  utility_types: [lineup.utility_type],
  progress: bundle.value?.lineup_progress?.[String(lineup.id)],
  title: lineup.title,
  summary: lineup.summary || lineup.purpose,
  to: `/maps?map=${lineup.map?.slug || ''}&land=${lineup.land_point_id}&lineup=${lineup.id}`,
  lineup,
})));

const progressTacticItems = computed<PlaybookItem[]>(() => {
  if (!bundle.value) return [];
  return allPersonalTactics.value.map((tactic) => ({
    id: `tactic-${tactic.id}`,
    kind: 'tactic',
    map: tactic.map,
    side: tactic.side,
    utility_types: tactic.utility_types,
    progress: bundle.value?.tactic_progress?.[String(tactic.id)],
    title: tactic.title,
    summary: tactic.summary,
    to: `/tactics/${tactic.slug}`,
    tactic,
  })).filter((item) => item.progress);
});

const progressLineupItems = computed<PlaybookItem[]>(() => {
  if (!bundle.value) return [];
  return (bundle.value.favorite_lineups || []).map((lineup) => ({
    id: `progress-lineup-${lineup.id}`,
    kind: 'lineup' as const,
    map: lineup.map || { slug: String(lineup.map_id), name: lineup.land_point?.name || lineup.title },
    side: lineup.side,
    utility_types: [lineup.utility_type],
    progress: bundle.value?.lineup_progress?.[String(lineup.id)],
    title: lineup.title,
    summary: lineup.summary || lineup.purpose,
    to: `/maps?map=${lineup.map?.slug || ''}&land=${lineup.land_point_id}&lineup=${lineup.id}`,
    lineup,
  })).filter((item) => item.progress);
});

const progressItems = computed(() => [...progressTacticItems.value, ...progressLineupItems.value]);

function matchesProgress(item: PlaybookItem) {
  if (filterMap.value && item.map.slug !== filterMap.value) return false;
  if (filterSide.value && item.side !== filterSide.value) return false;
  if (filterUtility.value && !item.utility_types.includes(filterUtility.value)) return false;
  if (filterProgress.value && item.progress !== filterProgress.value) return false;
  return true;
}

const filteredLineupFavorites = computed(() => favoriteLineupItems.value.filter(matchesProgress));
const filteredProgressItems = computed(() => progressItems.value.filter(matchesProgress));

onMounted(async () => {
  useHead(t('favoritesTitle'), t('favoritesIntro'));

  try {
    bundle.value = await api.getFavorites(session.token);
  } catch (err) {
    error.value = err instanceof Error ? err.message : t('loadingFailedRefresh');
  }
});
</script>

<template>
  <section class="section-heading">
    <div>
      <div class="kicker">{{ t('personalShelf') }}</div>
      <h1>{{ t('favoritesTitle') }}</h1>
    </div>
    <p class="section-intro">{{ t('favoritesIntro') }}</p>
  </section>

  <section v-if="error" class="empty-card danger">{{ error }}</section>

  <template v-else-if="bundle">
    <section class="glass-panel favorite-filter-panel">
      <select v-model="filterMap" class="filter-select">
        <option value="">{{ t('allMaps') }}</option>
        <option v-for="map in mapOptions" :key="map.slug" :value="map.slug">{{ map.name }}</option>
      </select>
      <select v-model="filterSide" class="filter-select">
        <option value="">{{ t('allSides') }}</option>
        <option value="T">{{ labelByLanguage('T', SIDE_LABELS, SIDE_LABELS_EN, language) }}</option>
        <option value="CT">{{ labelByLanguage('CT', SIDE_LABELS, SIDE_LABELS_EN, language) }}</option>
      </select>
      <select v-model="filterUtility" class="filter-select">
        <option value="">{{ t('allUtilities') }}</option>
        <option v-for="utility in utilityOptions" :key="utility" :value="utility">
          {{ labelByLanguage(utility, UTILITY_LABELS, UTILITY_LABELS_EN, language) }}
        </option>
      </select>
      <select v-model="filterProgress" class="filter-select">
        <option value="">{{ language === 'en' ? 'All progress' : '全部进度' }}</option>
        <option v-for="option in TRAINING_STATUSES" :key="option.value" :value="option.value">
          {{ language === 'en' ? option.en : option.zh }}
        </option>
      </select>
      <button class="ghost-button" @click="filterMap='';filterSide='';filterUtility='';filterProgress=''">{{ t('clear') }}</button>
    </section>

    <section v-if="frequentBundle.length" class="section-block favorite-bundle">
      <div class="section-heading">
        <h2>{{ t('frequentBundle') }}</h2>
        <span class="muted">{{ frequentBundle.length }} {{ t('itemSuffix') }}</span>
      </div>
      <div class="favorites-grid">
        <TacticCard v-for="item in frequentBundle" :key="item.id" :tactic="item" />
      </div>
    </section>

    <section class="section-block favorite-bundle">
      <div class="section-heading">
        <h2>{{ t('myFavorites') }}</h2>
        <span class="muted">{{ filteredFavorites.length }} {{ t('itemSuffix') }}</span>
      </div>
      <div v-if="filteredFavorites.length" class="favorites-grid">
        <TacticCard v-for="item in filteredFavorites" :key="item.id" :tactic="item" />
      </div>
      <div v-else class="empty-card">{{ t('emptyFavorites') }}</div>
    </section>

    <section class="section-block favorite-bundle">
      <div class="section-heading">
        <h2>{{ language === 'en' ? 'Favorite Utility' : '收藏道具' }}</h2>
        <span class="muted">{{ filteredLineupFavorites.length }} {{ t('itemSuffix') }}</span>
      </div>
      <div v-if="filteredLineupFavorites.length" class="utility-favorites-grid">
        <router-link v-for="item in filteredLineupFavorites" :key="item.id" class="utility-favorite-card" :to="item.to">
          <strong>{{ item.title }}</strong>
          <span>{{ item.summary }}</span>
          <small>{{ progressLabel(item.progress, language) }}</small>
        </router-link>
      </div>
      <div v-else class="empty-card">{{ language === 'en' ? 'No favorite utility yet.' : '还没有收藏道具。' }}</div>
    </section>

    <section class="section-block favorite-bundle">
      <div class="section-heading">
        <h2>{{ language === 'en' ? 'Training Progress' : '训练进度' }}</h2>
        <span class="muted">{{ filteredProgressItems.length }} {{ t('itemSuffix') }}</span>
      </div>
      <div v-if="filteredProgressItems.length" class="utility-favorites-grid">
        <router-link v-for="item in filteredProgressItems" :key="item.id" class="utility-favorite-card" :to="item.to">
          <strong>{{ item.title }}</strong>
          <span>{{ item.summary }}</span>
          <small>{{ progressLabel(item.progress, language) }}</small>
        </router-link>
      </div>
      <div v-else class="empty-card">{{ language === 'en' ? 'No training progress yet.' : '还没有训练进度。' }}</div>
    </section>

    <section class="section-block favorite-bundle">
      <div class="section-heading">
        <h2>{{ t('recentViews') }}</h2>
        <span class="muted">{{ filteredRecent.length }} {{ t('itemSuffix') }}</span>
      </div>
      <div v-if="filteredRecent.length" class="favorites-grid">
        <TacticCard v-for="item in filteredRecent" :key="item.id" :tactic="item" />
      </div>
      <div v-else class="empty-card">{{ t('emptyRecent') }}</div>
    </section>
  </template>
</template>

<style scoped>
.favorite-filter-panel {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  align-items: center;
  padding: 12px;
  margin-bottom: 18px;
}
.favorite-filter-panel .filter-select {
  min-width: 140px;
  border: 1px solid rgba(255,255,255,0.1);
  background: rgba(8,14,23,0.76);
  color: #fff;
  border-radius: 8px;
  padding: 9px 10px;
}
.utility-favorites-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 12px;
}
.utility-favorite-card {
  display: grid;
  gap: 6px;
  min-height: 112px;
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 8px;
  background: rgba(255,255,255,0.03);
  color: #dfe9f6;
  padding: 12px;
  text-decoration: none;
}
.utility-favorite-card:hover {
  border-color: rgba(255,122,24,0.4);
  background: rgba(255,122,24,0.1);
}
.utility-favorite-card span {
  color: #91a3ba;
  font-size: 0.8rem;
  line-height: 1.45;
}
.utility-favorite-card small {
  width: fit-content;
  border: 1px solid rgba(255,122,24,0.26);
  border-radius: 999px;
  color: #ffbd82;
  padding: 4px 8px;
}
</style>

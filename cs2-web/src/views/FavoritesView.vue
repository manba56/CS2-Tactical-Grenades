<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';

import { api } from '../api';
import { useHead } from '../composables/useHead';
import { useI18n } from '../composables/useI18n';
import TacticCard from '../components/TacticCard.vue';
import { useSessionStore } from '../stores/session';
import type { FavoriteBundle } from '../types';
import {
  SIDE_LABELS,
  SIDE_LABELS_EN,
  UTILITY_LABELS,
  UTILITY_LABELS_EN,
  labelByLanguage,
} from '../utils/labels';

const session = useSessionStore();
const { language, t } = useI18n();
const bundle = ref<FavoriteBundle | null>(null);
const error = ref('');
const filterMap = ref('');
const filterSide = ref('');
const filterUtility = ref('');

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
      <button class="ghost-button" @click="filterMap='';filterSide='';filterUtility=''">{{ t('clear') }}</button>
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
</style>

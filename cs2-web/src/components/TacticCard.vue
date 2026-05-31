<script setup lang="ts">
import { resolveAssetUrl } from '../api';
import type { TacticCard as TacticCardType } from '../types';
import { label, DIFFICULTY_LABELS, SIDE_LABELS, UTILITY_LABELS } from '../utils/labels';

defineProps<{
  tactic: TacticCardType;
}>();
</script>

<template>
  <article class="tactic-card">
    <div class="tactic-card-cover-wrapper">
      <img :src="resolveAssetUrl(tactic.cover_url)" :alt="tactic.title" class="tactic-card-cover" />
    </div>
    <div class="tactic-card-body">
      <div class="eyebrow-row">
        <span>{{ tactic.map.name }}</span>
        <span>{{ label(tactic.side, SIDE_LABELS) }}</span>
        <span>{{ label(tactic.difficulty, DIFFICULTY_LABELS) }}</span>
      </div>
      <h3>{{ tactic.title }}</h3>
      <p>{{ tactic.summary }}</p>
      <div class="chip-row">
        <span class="chip strong">{{ tactic.goal }}</span>
        <span v-for="utility in tactic.utility_types" :key="utility" class="chip">
          {{ label(utility, UTILITY_LABELS) }}
        </span>
      </div>
      <router-link class="text-link" :to="`/tactics/${tactic.slug}`">查看战术详情</router-link>
    </div>
  </article>
</template>

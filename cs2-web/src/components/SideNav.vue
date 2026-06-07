<script setup lang="ts">
import type { MapSummary, TacticCard as TacticCardType } from '../types';

defineProps<{
  maps: MapSummary[];
  allTactics: TacticCardType[];
  activeMapSlug: string;
  activeSide: string;
  activeDifficulty: string;
}>();

const emit = defineEmits<{
  (e: 'select-map', slug: string): void;
  (e: 'select-side', side: string): void;
  (e: 'select-difficulty', diff: string): void;
  (e: 'clear-filters'): void;
}>();
</script>

<template>
  <aside class="side-nav">
    <div class="side-section">
      <div class="side-label">热门地图</div>
      <a
        v-for="map in maps" :key="map.slug"
        class="side-map-item"
        :class="{ active: activeMapSlug === map.slug }"
        href="#"
        @click.prevent="emit('select-map', map.slug)"
      >
        <span class="side-map-name">{{ map.name }}</span>
        <span class="side-map-count">{{ (map as any).tactic_count || 0 }}</span>
      </a>
    </div>

    <div class="side-section">
      <div class="side-label">阵营</div>
      <div class="side-chips">
        <button :class="{ active: !activeSide }" @click="emit('select-side','')">全部</button>
        <button :class="{ active: activeSide === 'T' }" @click="emit('select-side','T')">
          <span class="side-dot t"></span>进攻方
        </button>
        <button :class="{ active: activeSide === 'CT' }" @click="emit('select-side','CT')">
          <span class="side-dot ct"></span>防守方
        </button>
      </div>
    </div>

    <div class="side-section">
      <div class="side-label">难度</div>
      <div class="side-chips">
        <button :class="{ active: !activeDifficulty }" @click="emit('select-difficulty','')">全部</button>
        <button :class="{ active: activeDifficulty === 'easy' }" @click="emit('select-difficulty','easy')">简单</button>
        <button :class="{ active: activeDifficulty === 'medium' }" @click="emit('select-difficulty','medium')">中等</button>
        <button :class="{ active: activeDifficulty === 'hard' }" @click="emit('select-difficulty','hard')">困难</button>
      </div>
    </div>

    <button class="side-reset" @click="emit('clear-filters')">清除筛选</button>
  </aside>
</template>

<style scoped>
.side-nav {
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding: 16px 12px;
  overflow-y: auto;
}
.side-section {}
.side-label {
  font-size: 0.68rem;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: #7a8ba0;
  margin-bottom: 8px;
}
.side-map-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 7px 10px;
  border-radius: 8px;
  text-decoration: none;
  color: #bcc8d6;
  font-size: 0.82rem;
  transition: background 0.15s;
}
.side-map-item:hover { background: rgba(255,255,255,0.04); }
.side-map-item.active { background: rgba(255,122,24,0.12); color: #ffb88c; }
.side-map-name { font-weight: 500; }
.side-map-count { font-size: 0.7rem; color: #5a6478; min-width: 20px; text-align: right; }

.side-chips { display: flex; flex-wrap: wrap; gap: 5px; }
.side-chips button {
  padding: 4px 10px;
  border-radius: 6px;
  border: 1px solid rgba(255,255,255,0.08);
  background: rgba(255,255,255,0.02);
  color: #8896ad;
  font-size: 0.74rem;
  cursor: pointer;
  transition: all 0.15s;
  display: flex; align-items: center; gap: 5px;
}
.side-chips button:hover { border-color: rgba(255,122,24,0.3); color: #fff; }
.side-chips button.active { background: rgba(255,122,24,0.15); border-color: rgba(255,122,24,0.3); color: #ffb88c; }

.side-dot { width: 8px; height: 8px; border-radius: 50%; }
.side-dot.t { background: #e6a23c; }
.side-dot.ct { background: #409eff; }

.side-reset {
  padding: 6px 12px;
  border-radius: 6px;
  border: 1px solid rgba(255,255,255,0.08);
  background: none;
  color: #6b7d95;
  font-size: 0.74rem;
  cursor: pointer;
  margin-top: 4px;
}
.side-reset:hover { color: #ff7a18; border-color: rgba(255,122,24,0.3); }
</style>

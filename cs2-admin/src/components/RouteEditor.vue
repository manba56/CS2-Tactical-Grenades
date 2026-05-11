<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue';
import { resolveAssetUrl } from '../api';

export interface RoutePoint {
  x: number;
  y: number;
}

export interface RouteData {
  player: number;
  color: string;
  label: string;
  points: RoutePoint[];
}

const PLAYER_COLORS = ['#ff7a18', '#409eff', '#67c23a', '#e6a23c', '#f56c6c'];
const PLAYER_LABELS = ['突破位', '道具位', '补枪位', '自由人', '狙击位'];

const props = defineProps<{
  mapSlug: string;
  modelValue: RouteData[];
}>();

const emit = defineEmits<{
  'update:modelValue': [value: RouteData[]];
}>();

const routes = ref<RouteData[]>([]);
const activePlayer = ref(1);
const draggingIdx = ref<number | null>(null);
const containerRef = ref<HTMLElement | null>(null);

// Init from modelValue
watch(() => props.modelValue, (val) => {
  routes.value = val ? JSON.parse(JSON.stringify(val)) : [];
}, { immediate: true });

const radarUrl = computed(() => {
  const slug = props.mapSlug || 'mirage';
  return resolveAssetUrl(`/static/assets/maps/${slug}-layout.svg`);
});

function emitChange() {
  emit('update:modelValue', JSON.parse(JSON.stringify(routes.value)));
}

function currentRoute(): RouteData {
  let r = routes.value.find(r => r.player === activePlayer.value);
  if (!r) {
    r = {
      player: activePlayer.value,
      color: PLAYER_COLORS[activePlayer.value - 1],
      label: PLAYER_LABELS[activePlayer.value - 1],
      points: [],
    };
    routes.value.push(r);
  }
  return r;
}

function getContainerRect(): DOMRect | null {
  return containerRef.value?.getBoundingClientRect() ?? null;
}

function pageToPercent(clientX: number, clientY: number): { x: number; y: number } | null {
  const rect = getContainerRect();
  if (!rect) return null;
  const x = ((clientX - rect.left) / rect.width) * 100;
  const y = ((clientY - rect.top) / rect.height) * 100;
  if (x < 0 || x > 100 || y < 0 || y > 100) return null;
  return { x: Math.round(x * 10) / 10, y: Math.round(y * 10) / 10 };
}

function onMapClick(e: MouseEvent) {
  if (draggingIdx.value !== null) return;
  const pt = pageToPercent(e.clientX, e.clientY);
  if (!pt) return;
  currentRoute().points.push(pt);
  emitChange();
}

function onNodeMouseDown(e: MouseEvent, idx: number) {
  e.stopPropagation();
  draggingIdx.value = idx;

  const onMove = (ev: MouseEvent) => {
    const pt = pageToPercent(ev.clientX, ev.clientY);
    if (!pt) return;
    currentRoute().points[idx] = pt;
    emitChange();
  };
  const onUp = () => {
    draggingIdx.value = null;
    window.removeEventListener('mousemove', onMove);
    window.removeEventListener('mouseup', onUp);
  };
  window.addEventListener('mousemove', onMove);
  window.addEventListener('mouseup', onUp);
}

function onNodeContextMenu(e: MouseEvent, idx: number) {
  e.preventDefault();
  e.stopPropagation();
  currentRoute().points.splice(idx, 1);
  emitChange();
}

function clearCurrentRoute() {
  const r = routes.value.find(r => r.player === activePlayer.value);
  if (r) r.points = [];
  emitChange();
}

function routePath(r: RouteData): string {
  if (r.points.length < 2) return '';
  const pts = r.points.map(p => `${p.x}% ${p.y}%`);
  // Build line segments with gaps for arrows
  let d = '';
  for (let i = 1; i < pts.length; i++) {
    d += `M${pts[i - 1]} L${pts[i]} `;
  }
  return d;
}
</script>

<template>
  <div class="route-editor">
    <div class="route-toolbar">
      <span class="label">路线编辑</span>
      <div class="player-tabs">
        <button
          v-for="p in 5" :key="p"
          class="player-tab"
          :class="{ active: activePlayer === p }"
          :style="{ borderColor: PLAYER_COLORS[p - 1], color: activePlayer === p ? PLAYER_COLORS[p - 1] : '' }"
          @click="activePlayer = p"
        >
          P{{ p }}
          <span class="dot" :style="{ background: PLAYER_COLORS[p - 1] }" />
        </button>
      </div>
      <button class="ghost-button" @click="clearCurrentRoute">清除当前路线</button>
    </div>

    <div ref="containerRef" class="route-canvas" @click="onMapClick">
      <img :src="radarUrl" class="radar-bg" alt="map radar" />

      <!-- SVG overlay for routes -->
      <svg class="route-svg" viewBox="0 0 100 100" preserveAspectRatio="none">
        <!-- Arrow marker per color -->
        <defs>
          <marker
            v-for="(color, i) in PLAYER_COLORS" :key="i"
            :id="`arrow-${i}`"
            viewBox="0 0 10 10" refX="10" refY="5"
            markerWidth="6" markerHeight="6" orient="auto"
          >
            <path d="M0,0 L10,5 L0,10 Z" :fill="color" />
          </marker>
        </defs>
        <!-- Route lines -->
        <path
          v-for="r in routes" :key="r.player"
          :d="routePath(r)"
          :stroke="r.color"
          stroke-width="0.8"
          fill="none"
          stroke-linecap="round"
          stroke-linejoin="round"
          :marker-end="`url(#arrow-${r.player - 1})`"
        />
      </svg>

      <!-- Draggable nodes -->
      <div
        v-for="r in routes" :key="r.player"
      >
        <div
          v-for="(pt, idx) in r.points" :key="idx"
          class="route-node"
          :style="{
            left: `${pt.x}%`,
            top: `${pt.y}%`,
            background: r.color,
            boxShadow: activePlayer === r.player ? `0 0 0 4px ${r.color}40` : '',
          }"
          @mousedown="(e) => onNodeMouseDown(e, idx)"
          @contextmenu="(e) => onNodeContextMenu(e, idx)"
        >
          <span class="node-label">{{ r.player }}.{{ idx + 1 }}</span>
        </div>
      </div>
    </div>

    <div class="route-legend">
      <div v-for="r in routes" :key="r.player" class="legend-item">
        <span class="legend-dot" :style="{ background: r.color }" />
        P{{ r.player }} {{ r.label }} — {{ r.points.length }} 点
      </div>
      <div v-if="routes.length === 0" class="muted">点击地图添加路线节点，右键删除节点，拖拽移动节点</div>
    </div>
  </div>
</template>

<style scoped>
.route-editor {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.route-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}
.route-toolbar .label {
  font-weight: 600;
  font-size: 14px;
}
.player-tabs {
  display: flex;
  gap: 4px;
}
.player-tab {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border: 2px solid #333;
  border-radius: 6px;
  background: #1a1a2e;
  color: #888;
  cursor: pointer;
  font-size: 12px;
  font-weight: 600;
}
.player-tab.active {
  background: #222240;
  font-weight: 700;
}
.player-tab .dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
}
.route-canvas {
  position: relative;
  width: 100%;
  aspect-ratio: 1000 / 700;
  border: 2px solid #333;
  border-radius: 8px;
  overflow: hidden;
  cursor: crosshair;
  background: #0a0a14;
}
.radar-bg {
  width: 100%;
  height: 100%;
  display: block;
  user-select: none;
  pointer-events: none;
}
.route-svg {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}
.route-node {
  position: absolute;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  border: 2px solid white;
  transform: translate(-50%, -50%);
  cursor: grab;
  z-index: 2;
}
.route-node:active {
  cursor: grabbing;
}
.node-label {
  position: absolute;
  left: 16px;
  top: -6px;
  font-size: 10px;
  color: #ccc;
  white-space: nowrap;
  pointer-events: none;
}
.route-legend {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
  font-size: 12px;
}
.legend-item {
  display: flex;
  align-items: center;
  gap: 4px;
  color: #aaa;
}
.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}
.muted {
  color: #666;
  font-size: 12px;
}
.ghost-button {
  padding: 4px 10px;
  border: 1px solid #444;
  border-radius: 4px;
  background: transparent;
  color: #aaa;
  cursor: pointer;
  font-size: 11px;
}
.ghost-button:hover {
  border-color: #ff7a18;
  color: #ff7a18;
}
</style>

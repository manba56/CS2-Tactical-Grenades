<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { resolveAssetUrl } from '../api';

// ── Types ───────────────────────────────────────────────────────
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
const PLAYER_LABELS = ['突破手', '辅助/道具', '补枪/跟枪', '自由人', '狙击手'];
const PLAYER_TOOLTIPS = [
  'P1 突破手：第一时间进点，拉枪线、吃伤害',
  'P2 辅助/道具：跟突破手身后，丢烟丢闪',
  'P3 补枪/跟枪：突破手倒了立即补上',
  'P4 自由人：另一侧制造动静、断后',
  'P5 狙击手：架点、首杀，拿 AWP',
];

// ── Props & emits ───────────────────────────────────────────────
const props = defineProps<{
  mapSlug: string;
  modelValue: RouteData[];
}>();

const emit = defineEmits<{
  'update:modelValue': [value: RouteData[]];
}>();

// ── State ───────────────────────────────────────────────────────
const routes = ref<RouteData[]>([]);
const activePlayer = ref(1);
const containerRef = ref<HTMLElement | null>(null);
const isDrawing = ref(false);
const drawingPoints = ref<RoutePoint[]>([]);
const showTutorial = ref(false);

// ── Lifecycle: attach pen listeners directly to the canvas ──────
onMounted(() => {
  const el = containerRef.value;
  if (!el) return;
  el.addEventListener('mousedown', onPenDown);
  el.addEventListener('touchstart', onPenDown, { passive: false });
  el.addEventListener('dragstart', (e) => e.preventDefault());
});

onBeforeUnmount(() => {
  const el = containerRef.value;
  if (!el) return;
  el.removeEventListener('mousedown', onPenDown);
  el.removeEventListener('touchstart', onPenDown);
  window.removeEventListener('mousemove', onPenMove);
  window.removeEventListener('mouseup', onPenUp);
});

watch(() => props.modelValue, (val) => {
  routes.value = val ? JSON.parse(JSON.stringify(val)) : [];
}, { immediate: true });

const radarUrl = computed(() => {
  const slug = props.mapSlug || 'mirage';
  return resolveAssetUrl(`/static/assets/maps/radars/${slug}-radar.png`);
});

function emitChange() {
  emit('update:modelValue', JSON.parse(JSON.stringify(routes.value)));
}

// ── Coordinate helpers ──────────────────────────────────────────
function getContainerRect(): DOMRect | null {
  return containerRef.value?.getBoundingClientRect() ?? null;
}

function pageToPercent(clientX: number, clientY: number): { x: number; y: number } {
  const rect = getContainerRect();
  if (!rect) return { x: 0, y: 0 };
  const x = ((clientX - rect.left) / rect.width) * 100;
  const y = ((clientY - rect.top) / rect.height) * 100;
  return {
    x: Math.round(Math.max(0, Math.min(100, x)) * 10) / 10,
    y: Math.round(Math.max(0, Math.min(100, y)) * 10) / 10,
  };
}

// ── Current route ───────────────────────────────────────────────
function currentRoute(): RouteData {
  let r = routes.value.find(rp => rp.player === activePlayer.value);
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

// ── Pen drawing ─────────────────────────────────────────────────
const SAMPLE_DIST = 1.5;
let lastSample = { x: 0, y: 0 };

function eventXY(e: MouseEvent | TouchEvent): { x: number; y: number } {
  if ('touches' in e) {
    const t = e.touches[0] || (e as TouchEvent).changedTouches[0];
    return { x: t.clientX, y: t.clientY };
  }
  return { x: (e as MouseEvent).clientX, y: (e as MouseEvent).clientY };
}

function onPenDown(e: MouseEvent | TouchEvent) {
  if ('button' in e && e.button !== 0) return;
  e.preventDefault();
  e.stopPropagation();

  const { x, y } = eventXY(e);
  isDrawing.value = true;
  drawingPoints.value = [];
  const pt = pageToPercent(x, y);
  drawingPoints.value.push(pt);
  lastSample = pt;

  window.addEventListener('mousemove', onPenMove);
  window.addEventListener('mouseup', onPenUp);
  window.addEventListener('touchmove', onPenMove, { passive: false });
  window.addEventListener('touchend', onPenUp);
}

function onPenMove(e: MouseEvent | TouchEvent) {
  if (!isDrawing.value) return;
  if ('touches' in e) e.preventDefault();

  const { x, y } = eventXY(e);
  const pt = pageToPercent(x, y);
  const dist = Math.hypot(pt.x - lastSample.x, pt.y - lastSample.y);
  if (dist >= SAMPLE_DIST) {
    drawingPoints.value.push(pt);
    lastSample = pt;
  }
}

function onPenUp() {
  window.removeEventListener('mousemove', onPenMove);
  window.removeEventListener('mouseup', onPenUp);
  window.removeEventListener('touchmove', onPenMove);
  window.removeEventListener('touchend', onPenUp);

  if (!isDrawing.value) return;
  isDrawing.value = false;

  if (drawingPoints.value.length < 2) {
    if (drawingPoints.value.length === 1) {
      const route = currentRoute();
      route.points.push(drawingPoints.value[0]);
      emitChange();
    }
    drawingPoints.value = [];
    return;
  }

  const simplified = simplifyPath(drawingPoints.value, 1.0);
  const smoothed = smoothPath(simplified, 2);

  const route = currentRoute();
  for (const pt of smoothed) {
    route.points.push({ x: pt.x, y: pt.y });
  }
  emitChange();
  drawingPoints.value = [];
}

// ── Path simplification (Ramer-Douglas-Peucker) ─────────────────
function simplifyPath(points: RoutePoint[], epsilon: number): RoutePoint[] {
  if (points.length <= 2) return [...points];

  let maxDist = 0;
  let maxIdx = 0;
  const first = points[0];
  const last = points[points.length - 1];

  for (let i = 1; i < points.length - 1; i++) {
    const dist = perpendicularDist(points[i], first, last);
    if (dist > maxDist) { maxDist = dist; maxIdx = i; }
  }

  if (maxDist > epsilon) {
    const left = simplifyPath(points.slice(0, maxIdx + 1), epsilon);
    const right = simplifyPath(points.slice(maxIdx), epsilon);
    return [...left.slice(0, -1), ...right];
  }
  return [first, last];
}

function perpendicularDist(p: RoutePoint, a: RoutePoint, b: RoutePoint): number {
  const dx = b.x - a.x;
  const dy = b.y - a.y;
  if (dx === 0 && dy === 0) return Math.hypot(p.x - a.x, p.y - a.y);
  const t = ((p.x - a.x) * dx + (p.y - a.y) * dy) / (dx * dx + dy * dy);
  const clamped = Math.max(0, Math.min(1, t));
  const px = a.x + clamped * dx;
  const py = a.y + clamped * dy;
  return Math.hypot(p.x - px, p.y - py);
}

// ── Path smoothing (moving average) ─────────────────────────────
function smoothPath(points: RoutePoint[], passes: number): RoutePoint[] {
  let result = points;
  for (let p = 0; p < passes; p++) {
    const smoothed: RoutePoint[] = [];
    smoothed.push(result[0]);
    for (let i = 1; i < result.length - 1; i++) {
      smoothed.push({
        x: Math.round((result[i - 1].x + result[i].x + result[i + 1].x) / 3 * 10) / 10,
        y: Math.round((result[i - 1].y + result[i].y + result[i + 1].y) / 3 * 10) / 10,
      });
    }
    smoothed.push(result[result.length - 1]);
    result = smoothed;
  }
  return result;
}

// ── SVG path ────────────────────────────────────────────────────
function routePathD(r: RouteData): string {
  const pts = r.points;
  if (pts.length === 0) return '';
  if (pts.length === 1) return `M${pts[0].x}% ${pts[0].y}%`;
  let d = `M${pts[0].x}% ${pts[0].y}%`;
  for (let i = 1; i < pts.length; i++) {
    d += ` L${pts[i].x}% ${pts[i].y}%`;
  }
  return d;
}

function drawingPathD(): string {
  const pts = drawingPoints.value;
  if (pts.length === 0) return '';
  let d = `M${pts[0].x}% ${pts[0].y}%`;
  for (let i = 1; i < pts.length; i++) {
    d += ` L${pts[i].x}% ${pts[i].y}%`;
  }
  return d;
}

// ── Actions ─────────────────────────────────────────────────────
function clearCurrentRoute() {
  const r = routes.value.find(rp => rp.player === activePlayer.value);
  if (r) r.points = [];
  emitChange();
}

function undoLastRoute() {
  const r = routes.value.find(rp => rp.player === activePlayer.value);
  if (r && r.points.length > 0) {
    r.points.pop();
    emitChange();
  }
}

function clearAll() {
  if (confirm('清除所有玩家的路线？')) {
    routes.value = [];
    emitChange();
  }
}

// ── Draw route end arrow ────────────────────────────────────────
function lastPoint(r: RouteData): RoutePoint | null {
  return r.points.length > 0 ? r.points[r.points.length - 1] : null;
}
</script>

<template>
  <div class="route-editor">
    <!-- Toolbar -->
    <div class="route-toolbar">
      <span class="label">钢笔绘制</span>
      <div class="player-tabs">
        <button
          v-for="p in 5" :key="p"
          class="player-tab"
          :class="{ active: activePlayer === p }"
          :style="{ borderColor: PLAYER_COLORS[p - 1], color: activePlayer === p ? PLAYER_COLORS[p - 1] : '' }"
          :title="PLAYER_TOOLTIPS[p - 1]"
          @click="activePlayer = p"
        >
          P{{ p }}
          <span class="dot" :style="{ background: PLAYER_COLORS[p - 1] }" />
        </button>
      </div>
      <button class="ghost-button" @click="undoLastRoute" title="撤销最后一个节点">撤销节点</button>
      <button class="ghost-button" @click="clearCurrentRoute">清除 {{ PLAYER_LABELS[activePlayer - 1] }} 路线</button>
      <button class="ghost-button" @click="clearAll">全部清除</button>
      <button class="ghost-button" @click="showTutorial = !showTutorial">
        {{ showTutorial ? '隐藏教程' : '显示教程 ▲' }}
      </button>
    </div>

    <div class="editor-layout">
      <!-- Canvas -->
      <div class="canvas-col">
        <div
          ref="containerRef"
          class="route-canvas"
          @contextmenu.prevent
        >
          <img :src="radarUrl" class="radar-bg" alt="map radar" />

          <!-- SVG routes overlay -->
          <svg class="route-svg" viewBox="0 0 100 100" preserveAspectRatio="none">
            <defs>
              <marker
                v-for="i in 5" :key="i"
                :id="`arrow-${i}`"
                viewBox="0 0 10 10" refX="10" refY="5"
                markerWidth="6" markerHeight="6" orient="auto"
              >
                <path d="M0,0 L10,5 L0,10 Z" :fill="PLAYER_COLORS[i - 1]" />
              </marker>
            </defs>

            <!-- Completed routes -->
            <path
              v-for="r in routes" :key="r.player"
              :d="routePathD(r)"
              :stroke="r.color"
              stroke-width="1.2"
              fill="none"
              stroke-linecap="round"
              stroke-linejoin="round"
              :marker-end="r.points.length >= 2 ? `url(#arrow-${r.player})` : ''"
            />

            <!-- Live drawing preview -->
            <path
              v-if="isDrawing && drawingPoints.length >= 2"
              :d="drawingPathD()"
              :stroke="PLAYER_COLORS[activePlayer - 1]"
              stroke-width="2"
              fill="none"
              stroke-linecap="round"
              stroke-linejoin="round"
              opacity="0.7"
              stroke-dasharray="4,2"
            />
          </svg>

          <!-- Route end points -->
          <div
            v-for="r in routes" :key="r.player"
          >
            <div
              v-if="lastPoint(r)"
              class="route-end-dot"
              :style="{
                left: `${lastPoint(r)!.x}%`,
                top: `${lastPoint(r)!.y}%`,
                background: r.color,
                boxShadow: `0 0 6px ${r.color}80`,
              }"
            />
          </div>
        </div>

        <!-- Legend -->
        <div class="route-legend">
          <div v-for="r in routes" :key="r.player" class="legend-item">
            <span class="legend-dot" :style="{ background: r.color }" />
            P{{ r.player }} {{ r.label }} — {{ r.points.length }} 点
          </div>
          <div v-if="routes.every(r => r.points.length === 0)" class="muted">
            按住鼠标拖拽绘制路线，松手即完成
          </div>
        </div>
      </div>

      <!-- Tutorial -->
      <aside v-if="showTutorial" class="tutorial-panel">
        <h4>钢笔工具教程</h4>
        <div class="tutorial-grid">
          <div class="tut-item">
            <kbd>按住拖拽</kbd>
            <span>在雷达图上自由绘制路线</span>
          </div>
          <div class="tut-item">
            <kbd>松手</kbd>
            <span>完成绘制，路线自动平滑</span>
          </div>
          <div class="tut-item">
            <kbd>单击</kbd>
            <span>放置单个点位</span>
          </div>
          <div class="tut-item">
            <kbd>撤销节点</kbd>
            <span>删除当前玩家路线的最后一个点</span>
          </div>
          <div class="tut-item">
            <kbd>清除路线</kbd>
            <span>清除当前选中玩家的整条路线</span>
          </div>
          <div class="tut-item">
            <kbd>P1~P5</kbd>
            <span>切换玩家，每人独立路线和颜色</span>
          </div>
        </div>
        <div class="tut-divider" />
        <h4>位置说明</h4>
        <div class="tutorial-grid">
          <div class="tut-item">
            <span class="dot-sm" style="background:#ff7a18" />
            <span><b>P1 突破手</b> — 第一时间进点</span>
          </div>
          <div class="tut-item">
            <span class="dot-sm" style="background:#409eff" />
            <span><b>P2 辅助/道具</b> — 丢烟丢闪</span>
          </div>
          <div class="tut-item">
            <span class="dot-sm" style="background:#67c23a" />
            <span><b>P3 补枪/跟枪</b> — 补枪交易</span>
          </div>
          <div class="tut-item">
            <span class="dot-sm" style="background:#e6a23c" />
            <span><b>P4 自由人</b> — 另一侧行动</span>
          </div>
          <div class="tut-item">
            <span class="dot-sm" style="background:#f56c6c" />
            <span><b>P5 狙击手</b> — 架点首杀</span>
          </div>
        </div>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.route-editor {
  display: flex;
  flex-direction: column;
  gap: 10px;
  outline: none;
}
.editor-layout {
  display: flex;
  gap: 14px;
  align-items: flex-start;
}
.canvas-col {
  flex: 1;
  min-width: 0;
}
.route-toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.route-toolbar .label {
  font-weight: 600;
  font-size: 14px;
  color: #ffcc00;
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
  margin-top: 8px;
  user-select: none;
}
.radar-bg {
  width: 100%;
  height: 100%;
  display: block;
  pointer-events: none;
}
.route-svg {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}
.route-end-dot {
  position: absolute;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  border: 2px solid white;
  transform: translate(-50%, -50%);
  z-index: 2;
  pointer-events: none;
}
.route-legend {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
  font-size: 12px;
  margin-top: 8px;
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

/* Tutorial */
.tutorial-panel {
  width: 250px;
  flex-shrink: 0;
  border: 1px solid #333;
  border-radius: 8px;
  padding: 14px;
  background: #141428;
  font-size: 12px;
  color: #aaa;
  position: sticky;
  top: 10px;
  max-height: calc(100vh - 120px);
  overflow-y: auto;
}
.tutorial-panel h4 {
  margin: 0 0 10px;
  color: #ff7a18;
  font-size: 13px;
}
.tutorial-grid {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.tut-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.tut-item kbd {
  display: inline-block;
  background: #222;
  border: 1px solid #555;
  border-radius: 3px;
  padding: 1px 6px;
  font-size: 11px;
  color: #ffcc00;
  font-family: monospace;
  align-self: flex-start;
}
.dot-sm {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  margin-right: 4px;
}
.tut-divider {
  border-top: 1px solid #333;
  margin: 12px 0;
}
</style>

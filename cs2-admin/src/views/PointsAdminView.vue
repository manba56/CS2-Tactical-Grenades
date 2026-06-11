<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';

import { api, resolveAssetUrl } from '../api';
import AssetPicker from '../components/AssetPicker.vue';
import { useSessionStore } from '../stores/session';
import type { AdminLineup, AdminMap, AdminPoint } from '../types';

const session = useSessionStore();
const maps = ref<AdminMap[]>([]);
const points = ref<AdminPoint[]>([]);
const lineups = ref<AdminLineup[]>([]);
const editingId = ref<number | null>(null);
const selectedMapId = ref(1);
const typeFilter = ref('');
const error = ref('');
const uploadingMedia = ref<'aim_image_url' | 'effect_image_url' | ''>('');
const form = reactive({
  map_id: 1,
  name: '',
  key: '',
  x: 50,
  y: 50,
  side: 'BOTH',
  point_type: 'site',
  tagsText: '',
  description: '',
  aim_image_url: '',
  effect_image_url: '',
  video_url: '',
});

const POINT_TYPE_OPTIONS = [
  { value: 'site', label: '落点', color: '#f5d76e' },
  { value: 'staging', label: '起点', color: '#65d6ce' },
  { value: 'aim', label: '瞄点', color: '#ff7a18' },
  { value: 'utility', label: '通用道具点', color: '#9dccff' },
  { value: 'anchor', label: '站位点', color: '#c792ea' },
];

function pointTypeLabel(value: string) {
  return POINT_TYPE_OPTIONS.find((item) => item.value === value)?.label || value;
}

function pointTypeColor(value: string) {
  return POINT_TYPE_OPTIONS.find((item) => item.value === value)?.color || '#ff7a18';
}

const currentMap = computed(() => maps.value.find((map) => map.id === selectedMapId.value) || null);
const currentRadarUrl = computed(() =>
  currentMap.value ? resolveAssetUrl(`/static/assets/maps/radars/${currentMap.value.slug}-radar.png`) : '',
);

const mapPoints = computed(() => points.value.filter((point) => point.map_id === selectedMapId.value));
const visiblePoints = computed(() =>
  typeFilter.value ? mapPoints.value.filter((point) => point.point_type === typeFilter.value) : mapPoints.value,
);

const pointsByType = computed(() =>
  POINT_TYPE_OPTIONS.map((type) => ({
    ...type,
    items: visiblePoints.value.filter((point) => point.point_type === type.value),
  })).filter((group) => group.items.length > 0),
);

const selectedPoint = computed(() => editingId.value ? points.value.find((point) => point.id === editingId.value) || null : null);

const pointReferences = computed(() => {
  const refs = new Map<number, { start: number; aim: number; land: number; total: number }>();
  for (const point of points.value) {
    refs.set(point.id, { start: 0, aim: 0, land: 0, total: 0 });
  }
  for (const lineup of lineups.value) {
    for (const [role, pointId] of [
      ['start', lineup.start_point_id],
      ['aim', lineup.aim_point_id],
      ['land', lineup.land_point_id],
    ] as const) {
      const item = refs.get(pointId);
      if (!item) continue;
      item[role] += 1;
      item.total += 1;
    }
  }
  return refs;
});

function refsFor(pointId: number) {
  return pointReferences.value.get(pointId) || { start: 0, aim: 0, land: 0, total: 0 };
}

function pointName(pointId: number) {
  return points.value.find((point) => point.id === pointId)?.name || `#${pointId}`;
}

function relatedLineups(point: AdminPoint) {
  return lineups.value.filter((lineup) =>
    lineup.start_point_id === point.id ||
    lineup.aim_point_id === point.id ||
    lineup.land_point_id === point.id,
  );
}

function parseTags(text: string) {
  return text.split(',').map((item) => item.trim()).filter(Boolean);
}

async function load() {
  const [mapItems, pointItems, lineupItems] = await Promise.all([
    api.maps(session.token),
    api.points(session.token),
    api.lineups(session.token),
  ]);
  maps.value = mapItems;
  points.value = pointItems;
  lineups.value = lineupItems;
  if (mapItems[0] && (!selectedMapId.value || !mapItems.some((map) => map.id === selectedMapId.value))) {
    selectedMapId.value = mapItems[0].id;
  }
  if (!editingId.value) {
    form.map_id = selectedMapId.value;
  }
}

function selectMap(mapId: number) {
  selectedMapId.value = mapId;
  if (!editingId.value) {
    resetForm();
  }
}

function edit(item: AdminPoint) {
  editingId.value = item.id;
  selectedMapId.value = item.map_id;
  Object.assign(form, {
    ...item,
    tagsText: (item.tags || []).join(', '),
    description: item.description || '',
    aim_image_url: item.aim_image_url || '',
    effect_image_url: item.effect_image_url || '',
    video_url: item.video_url || '',
  });
}

function resetForm() {
  editingId.value = null;
  error.value = '';
  Object.assign(form, {
    map_id: selectedMapId.value || maps.value[0]?.id || 1,
    name: '',
    key: '',
    x: 50,
    y: 50,
    side: 'BOTH',
    point_type: typeFilter.value || 'site',
    tagsText: '',
    description: '',
    aim_image_url: '',
    effect_image_url: '',
    video_url: '',
  });
}

function coordsFromRadar(event: MouseEvent) {
  const target = event.currentTarget as HTMLElement;
  const rect = target.getBoundingClientRect();
  return {
    x: Number((((event.clientX - rect.left) / rect.width) * 100).toFixed(2)),
    y: Number((((event.clientY - rect.top) / rect.height) * 100).toFixed(2)),
  };
}

function createPointFromRadar(event: MouseEvent) {
  const { x, y } = coordsFromRadar(event);
  editingId.value = null;
  Object.assign(form, {
    map_id: selectedMapId.value,
    name: '',
    key: '',
    x,
    y,
    side: 'BOTH',
    point_type: typeFilter.value || 'site',
    tagsText: '',
    description: '',
    aim_image_url: '',
    effect_image_url: '',
    video_url: '',
  });
}

function validateForm() {
  error.value = '';
  if (!form.map_id) error.value = '请选择地图';
  else if (!form.name.trim()) error.value = '请填写点位名称';
  else if (!form.key.trim()) error.value = '请填写点位 Key';
  else if (!form.point_type) error.value = '请选择点位类型';
  else if (form.x < 0 || form.x > 100 || form.y < 0 || form.y > 100) error.value = '坐标必须在 0 到 100 之间';
  else if (points.value.some((point) =>
    point.map_id === form.map_id &&
    point.key === form.key.trim() &&
    point.id !== editingId.value,
  )) {
    error.value = '同一张地图下点位 Key 不能重复';
  }
  return !error.value;
}

async function submit() {
  if (!validateForm()) return;
  const payload = {
    map_id: form.map_id,
    name: form.name.trim(),
    key: form.key.trim(),
    x: form.x,
    y: form.y,
    side: form.side,
    point_type: form.point_type,
    tags: parseTags(form.tagsText),
    description: form.description,
    aim_image_url: form.aim_image_url,
    effect_image_url: form.effect_image_url,
    video_url: form.video_url,
  };
  if (editingId.value) {
    await api.updatePoint(editingId.value, payload, session.token);
  } else {
    await api.createPoint(payload, session.token);
  }
  await load();
  resetForm();
}

async function uploadPointMedia(field: 'aim_image_url' | 'effect_image_url', file?: File) {
  if (!file) return;
  uploadingMedia.value = field;
  error.value = '';
  try {
    const result = await api.uploadAsset(file, session.token);
    form[field] = result.url;
  } catch (err) {
    error.value = err instanceof Error ? err.message : '上传失败，请检查图片格式和大小';
  } finally {
    uploadingMedia.value = '';
  }
}

function lineupsLinkFor(point: AdminPoint, role: 'start' | 'aim' | 'land' = 'land') {
  const query: Record<string, string> = {
    map_id: String(point.map_id),
  };
  if (role === 'start') query.start_point_id = String(point.id);
  else if (role === 'aim') query.aim_point_id = String(point.id);
  else query.land_point_id = String(point.id);
  return {
    path: '/lineups',
    query,
  };
}

onMounted(load);
</script>

<template>
  <div class="page-header">
    <h1>点位管理</h1>
    <p class="muted">按地图维护落点、起点、瞄点和通用道具点，前台 /maps 会直接读取这些点位和线路关系。</p>
  </div>

  <div class="point-admin-layout">
    <aside class="panel point-sidebar">
      <label>
        地图
        <select :value="selectedMapId" class="select" @change="selectMap(Number(($event.target as HTMLSelectElement).value))">
          <option v-for="map in maps" :key="map.id" :value="map.id">{{ map.name }}</option>
        </select>
      </label>

      <div class="type-filter">
        <div class="muted">点位类型</div>
        <button class="ghost-button" :class="{ active: !typeFilter }" @click="typeFilter = ''">全部</button>
        <button
          v-for="item in POINT_TYPE_OPTIONS"
          :key="item.value"
          class="ghost-button"
          :class="{ active: typeFilter === item.value }"
          @click="typeFilter = item.value"
        >
          <span class="type-dot" :style="{ background: item.color }" />
          {{ item.label }}
        </button>
      </div>

      <button class="button" type="button" @click="resetForm">新建点位</button>
    </aside>

    <main class="point-workspace">
      <section class="panel radar-panel">
        <div class="inline-row" style="justify-content:space-between">
          <div>
            <strong>{{ currentMap?.name || '地图雷达' }}</strong>
            <p class="muted" style="margin:2px 0 0">点击已有点位编辑；点击空白处创建新点位。</p>
          </div>
          <span class="chip">{{ visiblePoints.length }} 个点位</span>
        </div>
        <div v-if="currentRadarUrl" class="radar-stage" @click="createPointFromRadar">
          <img :src="currentRadarUrl" :alt="currentMap?.name || 'radar'" />
          <button
            v-for="point in visiblePoints"
            :key="point.id"
            type="button"
            class="radar-point"
            :class="{ active: editingId === point.id }"
            :style="{ left: `${point.x}%`, top: `${point.y}%`, background: pointTypeColor(point.point_type) }"
            :title="point.name"
            @click.stop="edit(point)"
          >
            {{ refsFor(point.id).land || '' }}
          </button>
          <span
            v-for="point in visiblePoints"
            :key="`label-${point.id}`"
            class="radar-point-label"
            :class="{ active: editingId === point.id }"
            :style="{ left: `${point.x}%`, top: `${point.y}%` }"
          >
            {{ point.name }}
          </span>
          <span
            v-if="!editingId"
            class="radar-marker"
            :style="{ left: `${form.x}%`, top: `${form.y}%`, background: pointTypeColor(form.point_type) }"
          />
        </div>
      </section>

      <form class="panel point-form" @submit.prevent="submit">
        <div class="inline-row" style="justify-content:space-between">
          <h2>{{ editingId ? '编辑点位' : '新建点位' }}</h2>
          <span v-if="selectedPoint" class="chip">{{ refsFor(selectedPoint.id).total }} 次引用</span>
        </div>
        <p v-if="error" class="error-text">{{ error }}</p>
        <div class="form-grid">
          <label>
            名称
            <input v-model="form.name" class="field" required />
          </label>
          <label>
            Key
            <input v-model="form.key" class="field" required />
          </label>
          <label>
            类型
            <select v-model="form.point_type" class="select" required>
              <option v-for="item in POINT_TYPE_OPTIONS" :key="item.value" :value="item.value">
                {{ item.label }} / {{ item.value }}
              </option>
            </select>
          </label>
          <label>
            阵营
            <select v-model="form.side" class="select">
              <option value="T">T</option>
              <option value="CT">CT</option>
              <option value="BOTH">BOTH</option>
            </select>
          </label>
          <label>
            坐标 X
            <input v-model.number="form.x" type="number" min="0" max="100" class="field" required />
          </label>
          <label>
            坐标 Y
            <input v-model.number="form.y" type="number" min="0" max="100" class="field" required />
          </label>
          <label class="full">
            标签，逗号分隔
            <input v-model="form.tagsText" class="field" />
          </label>
          <label class="full">
            点位说明
            <textarea v-model="form.description" class="textarea" />
          </label>
          <label class="full">
            瞄点图 URL
            <div class="media-url-row">
              <input v-model="form.aim_image_url" class="field" />
              <img v-if="form.aim_image_url" :src="resolveAssetUrl(form.aim_image_url)" class="media-preview" />
            </div>
            <details class="asset-library">
              <summary class="ghost-button">从素材库选择瞄点图</summary>
              <AssetPicker compact @select="(url) => { form.aim_image_url = url; }" />
            </details>
            <label class="ghost-button upload-button">
              {{ uploadingMedia === 'aim_image_url' ? '上传中...' : '上传瞄点图' }}
              <input
                type="file"
                accept="image/*"
                hidden
                :disabled="uploadingMedia !== ''"
                @change="(event) => uploadPointMedia('aim_image_url', (event.target as HTMLInputElement).files?.[0])"
              />
            </label>
          </label>
          <label class="full">
            效果图 URL
            <div class="media-url-row">
              <input v-model="form.effect_image_url" class="field" />
              <img v-if="form.effect_image_url" :src="resolveAssetUrl(form.effect_image_url)" class="media-preview" />
            </div>
            <details class="asset-library">
              <summary class="ghost-button">从素材库选择效果图</summary>
              <AssetPicker compact @select="(url) => { form.effect_image_url = url; }" />
            </details>
            <label class="ghost-button upload-button">
              {{ uploadingMedia === 'effect_image_url' ? '上传中...' : '上传落点/效果图' }}
              <input
                type="file"
                accept="image/*"
                hidden
                :disabled="uploadingMedia !== ''"
                @change="(event) => uploadPointMedia('effect_image_url', (event.target as HTMLInputElement).files?.[0])"
              />
            </label>
          </label>
          <label class="full">
            视频 URL
            <input v-model="form.video_url" class="field" />
          </label>
        </div>
        <div class="toolbar">
          <button class="button">{{ editingId ? '保存修改' : '创建点位' }}</button>
          <button class="ghost-button" type="button" @click="resetForm">清空表单</button>
        </div>
      </form>

      <section class="panel point-list-panel">
        <div class="inline-row" style="justify-content:space-between">
          <h2>点位列表</h2>
          <span class="muted">{{ visiblePoints.length }} 个</span>
        </div>
        <div class="point-type-groups">
          <article v-for="group in pointsByType" :key="group.value" class="point-type-group">
            <div class="point-type-heading">
              <span class="type-dot" :style="{ background: group.color }" />
              <strong>{{ group.label }}</strong>
              <span class="muted">{{ group.items.length }} 个</span>
            </div>
            <div class="point-list">
              <div v-for="point in group.items" :key="point.id" class="point-list-item">
                <div>
                  <strong>{{ point.name }}</strong>
                  <p class="muted">{{ point.key }} · {{ point.x }} / {{ point.y }}</p>
                </div>
                <div class="point-ref-row">
                  <span class="chip">引用 {{ refsFor(point.id).total }}</span>
                  <span v-if="refsFor(point.id).land" class="chip strong">落点 {{ refsFor(point.id).land }}</span>
                  <button class="ghost-button" type="button" @click="edit(point)">编辑</button>
                  <router-link v-if="point.point_type === 'site'" class="ghost-button" :to="lineupsLinkFor(point)">
                    新建道具
                  </router-link>
                  <router-link v-else class="ghost-button" :to="lineupsLinkFor(point, point.point_type === 'aim' ? 'aim' : 'start')">
                    作为{{ point.point_type === 'aim' ? '瞄点' : '起点' }}建线路
                  </router-link>
                </div>
                <div v-if="relatedLineups(point).length" class="related-lineups">
                  <span v-for="lineup in relatedLineups(point).slice(0, 4)" :key="lineup.id" class="related-lineup-chip">
                    {{ lineup.title }}：
                    {{ lineup.start_point_id === point.id ? '起点' : lineup.aim_point_id === point.id ? '瞄点' : '落点' }}
                    {{ point.point_type === 'site' ? ` / 起点 ${pointName(lineup.start_point_id)}` : ` / 落点 ${pointName(lineup.land_point_id)}` }}
                  </span>
                  <span v-if="relatedLineups(point).length > 4" class="muted">
                    +{{ relatedLineups(point).length - 4 }} 条
                  </span>
                </div>
              </div>
            </div>
          </article>
        </div>
      </section>
    </main>
  </div>
</template>

<style scoped>
.point-admin-layout {
  display: grid;
  grid-template-columns: 230px minmax(0, 1fr);
  gap: 16px;
  align-items: start;
}
.point-sidebar {
  position: sticky;
  top: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.type-filter {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.type-filter .ghost-button {
  justify-content: flex-start;
}
.type-filter .ghost-button.active,
.point-list-item .ghost-button:hover {
  border-color: rgba(255,122,24,0.45);
  color: #ffb88c;
  background: rgba(255,122,24,0.12);
}
.type-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 999px;
}
.point-workspace {
  display: grid;
  grid-template-columns: minmax(0, 1.1fr) minmax(340px, 0.9fr);
  gap: 16px;
}
.radar-panel,
.point-list-panel {
  grid-column: 1 / -1;
}
.radar-stage {
  position: relative;
  overflow: hidden;
  margin-top: 12px;
  border-radius: 8px;
  border: 1px solid rgba(255,255,255,0.08);
  cursor: crosshair;
}
.radar-stage img {
  display: block;
  width: 100%;
}
.radar-point,
.radar-marker {
  position: absolute;
  width: 18px;
  height: 18px;
  border: 2px solid #fff;
  border-radius: 50%;
  color: #07111f;
  font-size: 10px;
  font-weight: 900;
  line-height: 1;
  transform: translate(-50%, -50%);
  box-shadow: 0 0 0 6px rgba(255,122,24,0.18);
}
.radar-point {
  cursor: pointer;
}
.radar-point:hover,
.radar-point.active {
  box-shadow: 0 0 0 5px rgba(255,122,24,0.32), 0 0 18px rgba(255,122,24,0.5);
  transform: translate(-50%, -50%) scale(1.14);
}
.radar-marker {
  pointer-events: none;
}
.radar-point-label {
  position: absolute;
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  border: 1px solid rgba(255,255,255,0.14);
  border-radius: 999px;
  background: rgba(8,14,23,0.86);
  color: #fff;
  padding: 3px 7px;
  font-size: 11px;
  transform: translate(-50%, 12px);
  pointer-events: none;
}
.radar-point-label.active {
  color: #ffb88c;
  border-color: rgba(255,122,24,0.55);
  background: rgba(255,122,24,0.18);
}
.point-form h2,
.point-list-panel h2 {
  margin: 0;
}
.error-text {
  margin: 10px 0;
  color: #ff9f96;
}
.media-url-row {
  display: flex;
  gap: 8px;
  align-items: center;
}
.media-url-row .field {
  flex: 1;
}
.media-preview {
  width: 76px;
  height: 52px;
  object-fit: cover;
  border-radius: 6px;
  border: 1px solid rgba(255,255,255,0.08);
}
.asset-library {
  margin-top: 8px;
}
.asset-library > summary {
  display: inline-flex;
  width: fit-content;
  list-style: none;
}
.asset-library > summary::-webkit-details-marker {
  display: none;
}
.asset-library[open] {
  padding: 10px;
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 8px;
  background: rgba(255,255,255,0.02);
}
.upload-button {
  display: inline-flex;
  width: fit-content;
  margin-top: 8px;
  cursor: pointer;
}
.point-type-groups {
  display: grid;
  gap: 14px;
}
.point-type-heading,
.point-ref-row {
  display: flex;
  align-items: center;
  gap: 10px;
}
.point-type-heading {
  margin-bottom: 8px;
}
.point-list {
  display: grid;
  gap: 8px;
}
.point-list-item {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 10px 14px;
  align-items: center;
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 8px;
  background: rgba(255,255,255,0.03);
  padding: 10px;
}
.point-list-item p {
  margin: 2px 0 0;
}
.point-ref-row {
  flex-wrap: wrap;
  justify-content: flex-end;
}
.related-lineups {
  grid-column: 1 / -1;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.related-lineup-chip {
  display: inline-flex;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 999px;
  background: rgba(255,255,255,0.04);
  color: rgba(255,255,255,0.82);
  padding: 4px 8px;
  font-size: 11px;
}
@media (max-width: 900px) {
  .point-admin-layout,
  .point-workspace {
    grid-template-columns: 1fr;
  }
  .point-sidebar {
    position: static;
  }
  .point-list-item {
    grid-template-columns: 1fr;
  }
  .point-ref-row {
    justify-content: flex-start;
  }
}
</style>

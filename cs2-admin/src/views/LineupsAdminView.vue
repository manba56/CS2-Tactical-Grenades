<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';
import { useRoute } from 'vue-router';

import { api, resolveAssetUrl } from '../api';
import AssetPicker from '../components/AssetPicker.vue';
import { useSessionStore } from '../stores/session';
import type { AdminLineup, AdminMap, AdminPoint } from '../types';

const session = useSessionStore();
const route = useRoute();
const maps = ref<AdminMap[]>([]);
const points = ref<AdminPoint[]>([]);
const lineups = ref<AdminLineup[]>([]);
const editingId = ref<number | null>(null);
const error = ref('');
const form = reactive({
  map_id: 1,
  title: '',
  slug: '',
  side: 'T',
  utility_type: 'smoke',
  start_point_id: 1,
  aim_point_id: 1,
  land_point_id: 1,
  purpose: '',
  difficulty: 'medium',
  summary: '',
  stepsText: '',
  screenshots: [] as { url: string; description: string }[],
  video_url: '',
  status: 'draft',
});
const pointEditor = reactive({
  role: 'start' as 'start' | 'aim' | 'land',
  id: 0,
  name: '',
  key: '',
  x: 50,
  y: 50,
  side: 'BOTH',
  point_type: 'utility',
  tagsText: '',
});

const POINT_TYPE_OPTIONS = [
  { value: 'site', label: '落点' },
  { value: 'staging', label: '起点' },
  { value: 'aim', label: '瞄点' },
  { value: 'utility', label: '通用道具点' },
  { value: 'anchor', label: '站位点' },
];
const ROLE_POINT_TYPES: Record<'start' | 'aim' | 'land', string[]> = {
  start: ['staging', 'utility', 'anchor'],
  aim: ['aim', 'utility', 'anchor'],
  land: ['site', 'utility', 'aim'],
};

function pointTypeLabel(value: string) {
  return POINT_TYPE_OPTIONS.find((item) => item.value === value)?.label || value;
}

function pointName(pointId: number) {
  return points.value.find((point) => point.id === pointId)?.name || `#${pointId}`;
}

function mapName(mapId: number) {
  return maps.value.find((map) => map.id === mapId)?.name || `#${mapId}`;
}

const filteredPoints = computed(() => points.value.filter((point) => point.map_id === form.map_id));
const startPointOptions = computed(() => rolePointOptions('start'));
const aimPointOptions = computed(() => rolePointOptions('aim'));
const landPointOptions = computed(() => rolePointOptions('land'));
const currentMap = computed(() => maps.value.find((map) => map.id === form.map_id) || null);
const radarUrl = computed(() => currentMap.value ? resolveAssetUrl(`/static/assets/maps/radars/${currentMap.value.slug}-radar.png`) : '');
const selectedStartPoint = computed(() => points.value.find((point) => point.id === form.start_point_id) || null);
const selectedLandPoint = computed(() => points.value.find((point) => point.id === form.land_point_id) || null);
const landPointLineupCount = computed(() =>
  lineups.value.filter((lineup) => lineup.land_point_id === form.land_point_id && lineup.id !== editingId.value).length,
);
const startLandLineupCount = computed(() =>
  lineups.value.filter((lineup) =>
    lineup.start_point_id === form.start_point_id &&
    lineup.land_point_id === form.land_point_id &&
    lineup.id !== editingId.value,
  ).length,
);
const selectedPointPreview = computed(() => [
  { label: '起点', point: filteredPoints.value.find((p) => p.id === form.start_point_id), color: '#65d6ce' },
  { label: '瞄点', point: filteredPoints.value.find((p) => p.id === form.aim_point_id), color: '#ff7a18' },
  { label: '落点', point: filteredPoints.value.find((p) => p.id === form.land_point_id), color: '#f5d76e' },
].filter((item) => item.point));
const previewPath = computed(() => selectedPointPreview.value
  .map((item, index) => `${index === 0 ? 'M' : 'L'}${item.point!.x} ${item.point!.y}`)
  .join(' '));

function selectedPointForRole(role = pointEditor.role) {
  const id = role === 'start'
    ? form.start_point_id
    : role === 'aim'
      ? form.aim_point_id
      : form.land_point_id;
  return points.value.find((point) => point.id === id) || null;
}

function rolePointOptions(role: 'start' | 'aim' | 'land') {
  const allowed = ROLE_POINT_TYPES[role];
  const preferred = filteredPoints.value.filter((point) => allowed.includes(point.point_type));
  const selected = selectedPointForRole(role);
  const options = preferred.length ? [...preferred] : [...filteredPoints.value];
  if (selected && selected.map_id === form.map_id && !options.some((point) => point.id === selected.id)) {
    options.unshift(selected);
  }
  return options;
}

function firstPointIdForRole(role: 'start' | 'aim' | 'land') {
  return rolePointOptions(role)[0]?.id || filteredPoints.value[0]?.id || 1;
}

function ensurePointForRole(role: 'start' | 'aim' | 'land') {
  const current = selectedPointForRole(role);
  if (current?.map_id === form.map_id) return;
  const pointId = firstPointIdForRole(role);
  if (role === 'start') form.start_point_id = pointId;
  else if (role === 'aim') form.aim_point_id = pointId;
  else form.land_point_id = pointId;
}

function normalizePointSelections() {
  ensurePointForRole('start');
  ensurePointForRole('aim');
  ensurePointForRole('land');
  loadPointEditor(pointEditor.role);
}

function applyRoutePreset() {
  const mapId = Number(route.query.map_id || 0);
  const startPointId = Number(route.query.start_point_id || 0);
  const aimPointId = Number(route.query.aim_point_id || 0);
  const landPointId = Number(route.query.land_point_id || 0);
  if (mapId && maps.value.some((map) => map.id === mapId)) {
    form.map_id = mapId;
  }
  if (startPointId && points.value.some((point) => point.id === startPointId && point.map_id === form.map_id)) {
    form.start_point_id = startPointId;
  }
  if (aimPointId && points.value.some((point) => point.id === aimPointId && point.map_id === form.map_id)) {
    form.aim_point_id = aimPointId;
  }
  if (landPointId && points.value.some((point) => point.id === landPointId && point.map_id === form.map_id)) {
    form.land_point_id = landPointId;
  }
}

function changeMap() {
  normalizePointSelections();
}

function loadPointEditor(role = pointEditor.role) {
  pointEditor.role = role;
  const point = selectedPointForRole(role);
  if (!point) return;
  Object.assign(pointEditor, {
    role,
    id: point.id,
    name: point.name,
    key: point.key,
    x: point.x,
    y: point.y,
    side: point.side,
    point_type: point.point_type,
    tagsText: (point.tags || []).join(', '),
  });
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
  if (!editingId.value && mapItems[0]) {
    form.map_id = mapItems[0].id;
  }
  if (!editingId.value) {
    applyRoutePreset();
    normalizePointSelections();
  }
  loadPointEditor();
}

function edit(item: AdminLineup) {
  editingId.value = item.id;
  Object.assign(form, {
    ...item,
    stepsText: (item.steps || []).join('\n'),
    screenshots: (item.media || []).map((url: string) => ({ url, description: '' })),
    video_url: item.video_url || '',
  });
  loadPointEditor();
}

function resetForm() {
  editingId.value = null;
  error.value = '';
  const mapId = maps.value[0]?.id || 1;
  Object.assign(form, {
    map_id: mapId,
    title: '',
    slug: '',
    side: 'T',
    utility_type: 'smoke',
    start_point_id: 1,
    aim_point_id: 1,
    land_point_id: 1,
    purpose: '',
    difficulty: 'medium',
    summary: '',
    stepsText: '',
    screenshots: [],
    video_url: '',
    status: 'draft',
  });
  normalizePointSelections();
}

async function saveLinkedPoint() {
  if (!pointEditor.id) return;
  const original = points.value.find((point) => point.id === pointEditor.id);
  if (!original) return;
  await api.updatePoint(pointEditor.id, {
    ...original,
    name: pointEditor.name,
    key: pointEditor.key,
    x: pointEditor.x,
    y: pointEditor.y,
    side: pointEditor.side,
    point_type: pointEditor.point_type,
    tags: pointEditor.tagsText.split(',').map((item) => item.trim()).filter(Boolean),
  }, session.token);
  await load();
  loadPointEditor(pointEditor.role);
}

async function aiFill() {
  const mapItem = maps.value.find(m => m.id === form.map_id);
  try {
    const resp = await api.aiGenerate({
      map: mapItem?.name || '',
      title: form.title || '',
      side: form.side,
      goal: form.purpose || '通用',
      phase: 'default',
      difficulty: form.difficulty,
      players: 1,
      utility_type: form.utility_type,
    }, session.token);

    if (resp.summary) form.summary = resp.summary;
    if (resp.note) form.purpose = resp.note;
    if (resp.steps) form.stepsText = resp.steps;
  } catch (e: any) {
    alert('AI 生成失败：' + (e.message || '请检查 API Key'));
  }
}

async function submit() {
  const selectedIds = [form.start_point_id, form.aim_point_id, form.land_point_id];
  if (selectedIds.some((id) => !points.value.some((point) => point.id === id && point.map_id === form.map_id))) {
    error.value = '起点、瞄点和落点必须属于当前地图';
    return;
  }
  error.value = '';
  const payload = {
    map_id: form.map_id,
    title: form.title,
    slug: form.slug,
    side: form.side,
    utility_type: form.utility_type,
    start_point_id: form.start_point_id,
    aim_point_id: form.aim_point_id,
    land_point_id: form.land_point_id,
    purpose: form.purpose,
    difficulty: form.difficulty,
    summary: form.summary,
    steps: form.stepsText.split('\n').map((item) => item.trim()).filter(Boolean),
    media: form.screenshots.filter(s => s.url).map(s => s.url),
    video_url: form.video_url,
    status: form.status,
  };
  if (editingId.value) {
    await api.updateLineup(editingId.value, payload, session.token);
    editingId.value = null;
  } else {
    await api.createLineup(payload, session.token);
  }
  await load();
}

function clone(item: AdminLineup) {
  Object.assign(form, { ...item, title: item.title + ' (副本)', slug: '' });
  editingId.value = null;
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function addScreenshot() { form.screenshots.push({ url: '', description: '' }); }
function removeScreenshot(i: number) { form.screenshots.splice(i, 1); }
async function uploadScreenshot(i: number, file: File) {
  try {
    const result = await api.uploadAsset(file, session.token);
    form.screenshots[i].url = result.url;
  } catch (err) {
    alert('上传失败');
  }
}

function selectScreenshotAsset(i: number, url: string) {
  form.screenshots[i].url = url;
}

async function remove(item: AdminLineup) {
  error.value = '';
  try {
    await api.deleteLineup(item.id, session.token);
    await load();
  } catch (err) {
    error.value = err instanceof Error ? err.message : '删除失败';
  }
}

async function archive(item: AdminLineup) {
  await api.archiveLineup(item.id, session.token);
  await load();
}

onMounted(load);
</script>

<template>
  <div class="page-header">
    <h1>线路管理</h1>
    <p class="muted">维护投掷物线路、起点、瞄点和落点关系。</p>
  </div>
  <p v-if="error" class="muted">{{ error }}</p>
  <div class="content-grid">
    <section class="panel list-stack">
      <article v-for="item in lineups" :key="item.id" class="list-item">
        <div class="inline-row">
          <strong>{{ item.title }}</strong>
          <span class="chip">{{ item.utility_type }}</span>
          <span class="chip">{{ item.status }}</span>
        </div>
        <p class="muted lineup-relation">
          {{ mapName(item.map_id) }} / {{ pointName(item.start_point_id) }} -> {{ pointName(item.land_point_id) }}
        </p>
        <p class="muted">{{ item.summary }}</p>
        <div class="toolbar">
          <button class="ghost-button" @click="edit(item)">编辑</button>
          <button class="ghost-button" @click="clone(item)">克隆</button>
          <button class="ghost-button" @click="archive(item)">归档</button>
          <button class="ghost-button" @click="remove(item)">删除</button>
        </div>
      </article>
    </section>

    <form class="panel" @submit.prevent="submit">
      <h2>{{ editingId ? '编辑线路' : '新增线路' }}
        <button type="button" class="primary-button" style="margin-left:12px;font-size:0.85rem;padding:6px 16px" @click="aiFill()">🤖 AI 一键生成</button>
      </h2>
      <div class="form-grid">
        <label>
          地图
          <select v-model.number="form.map_id" class="select" @change="changeMap">
            <option v-for="map in maps" :key="map.id" :value="map.id">{{ map.name }}</option>
          </select>
        </label>
        <label>
          标题
          <input v-model="form.title" class="field" />
        </label>
        <label>
          Slug
          <input v-model="form.slug" class="field" />
        </label>
        <label>
          阵营
          <select v-model="form.side" class="select">
            <option value="T">T</option>
            <option value="CT">CT</option>
          </select>
        </label>
        <label>
          道具类型
          <select v-model="form.utility_type" class="select">
            <option value="smoke">smoke</option>
            <option value="flash">flash</option>
            <option value="molotov">molotov</option>
            <option value="he">he</option>
            <option value="decoy">decoy</option>
          </select>
        </label>
        <label>
          难度
          <select v-model="form.difficulty" class="select">
            <option value="easy">easy</option>
            <option value="medium">medium</option>
            <option value="hard">hard</option>
          </select>
        </label>
        <label>
          起点
          <select v-model.number="form.start_point_id" class="select" @change="loadPointEditor('start')">
            <option v-for="point in startPointOptions" :key="point.id" :value="point.id">
              {{ point.name }} · {{ pointTypeLabel(point.point_type) }}
            </option>
          </select>
        </label>
        <label>
          瞄点
          <select v-model.number="form.aim_point_id" class="select" @change="loadPointEditor('aim')">
            <option v-for="point in aimPointOptions" :key="point.id" :value="point.id">
              {{ point.name }} · {{ pointTypeLabel(point.point_type) }}
            </option>
          </select>
        </label>
        <label>
          落点
          <select v-model.number="form.land_point_id" class="select" @change="loadPointEditor('land')">
            <option v-for="point in landPointOptions" :key="point.id" :value="point.id">
              {{ point.name }} · {{ pointTypeLabel(point.point_type) }}
            </option>
          </select>
          <span class="muted point-reference-hint">
            {{ selectedLandPoint?.name || '未选择落点' }} 已有关联线路 {{ landPointLineupCount }} 条
          </span>
          <span class="muted point-reference-hint">
            当前组合：{{ selectedStartPoint?.name || '未选择起点' }} -> {{ selectedLandPoint?.name || '未选择落点' }}，已有 {{ startLandLineupCount }} 条线路
          </span>
        </label>
        <div class="full lineup-preview" v-if="radarUrl">
          <div class="inline-row" style="justify-content:space-between">
            <strong>线路关系预览</strong>
            <span class="muted">起点 → 瞄点 → 落点</span>
          </div>
          <div class="lineup-radar-stage">
            <img :src="radarUrl" :alt="currentMap?.name || 'radar'" />
            <svg class="lineup-preview-svg" viewBox="0 0 100 100" preserveAspectRatio="none">
              <path v-if="previewPath" :d="previewPath" stroke="#ff7a18" stroke-width="0.8" fill="none" stroke-linecap="round" />
            </svg>
            <span
              v-for="item in selectedPointPreview"
              :key="item.label"
              class="lineup-preview-point"
              :style="{ left: `${item.point!.x}%`, top: `${item.point!.y}%`, background: item.color }"
            >
              {{ item.label }}
            </span>
          </div>
        </div>
        <div class="full linked-point-editor">
          <div class="inline-row" style="justify-content:space-between">
            <strong>编辑当前点位</strong>
            <span class="muted">点位是全局复用的，修改会影响引用它的内容</span>
          </div>
          <div class="toolbar">
            <button type="button" class="ghost-button" :class="{ active: pointEditor.role === 'start' }" @click="loadPointEditor('start')">起点</button>
            <button type="button" class="ghost-button" :class="{ active: pointEditor.role === 'aim' }" @click="loadPointEditor('aim')">瞄点</button>
            <button type="button" class="ghost-button" :class="{ active: pointEditor.role === 'land' }" @click="loadPointEditor('land')">落点</button>
          </div>
          <div class="linked-point-grid">
            <label>
              名称
              <input v-model="pointEditor.name" class="field" />
            </label>
            <label>
              Key
              <input v-model="pointEditor.key" class="field" />
            </label>
            <label>
              X
              <input v-model.number="pointEditor.x" type="number" min="0" max="100" class="field" />
            </label>
            <label>
              Y
              <input v-model.number="pointEditor.y" type="number" min="0" max="100" class="field" />
            </label>
            <label>
              阵营
              <select v-model="pointEditor.side" class="select">
                <option value="T">T</option>
                <option value="CT">CT</option>
                <option value="BOTH">BOTH</option>
              </select>
            </label>
            <label>
              类型
              <select v-model="pointEditor.point_type" class="select">
                <option v-for="item in POINT_TYPE_OPTIONS" :key="item.value" :value="item.value">
                  {{ item.label }} / {{ item.value }}
                </option>
              </select>
            </label>
            <label class="full">
              标签
              <input v-model="pointEditor.tagsText" class="field" />
            </label>
          </div>
          <button type="button" class="button" @click="saveLinkedPoint">保存点位修改</button>
        </div>
        <label>
          状态
          <select v-model="form.status" class="select">
            <option value="draft">draft</option>
            <option value="published">published</option>
            <option value="archived">archived</option>
          </select>
        </label>
        <label class="full">
          用途
          <textarea v-model="form.purpose" class="textarea" />
        </label>
        <label class="full">
          摘要
          <textarea v-model="form.summary" class="textarea" />
        </label>
        <label class="full">
          步骤（每行一条）
          <textarea v-model="form.stepsText" class="textarea" />
        </label>
        <div class="full">
          <div class="screenshots-section">
            <h3>截图 <button type="button" class="ghost-button" @click="addScreenshot()">+ 添加</button></h3>
            <p class="muted" style="font-size:11px">上传线路的瞄点截图或投掷示范图</p>
            <div v-if="form.screenshots.length === 0" class="screenshot-placeholder">暂无截图</div>
            <div v-for="(shot, idx) in form.screenshots" :key="idx" class="screenshot-row" style="display:flex;gap:8px;align-items:center;margin-bottom:8px">
              <input v-model="shot.description" class="field" placeholder="截图描述" style="flex:1" />
              <label v-if="!shot.url" class="ghost-button" style="cursor:pointer;white-space:nowrap">
                选择文件
                <input type="file" accept="image/*" hidden @change="(e:any) => uploadScreenshot(idx, e.target.files[0])" />
              </label>
              <details class="asset-library">
                <summary class="ghost-button">从素材库回填</summary>
                <AssetPicker compact @select="(url) => selectScreenshotAsset(idx, url)" />
              </details>
              <img
                v-if="shot.url"
                :src="resolveAssetUrl(shot.url)"
                style="width:60px;height:60px;object-fit:cover;border-radius:6px;border:1px solid rgba(255,255,255,0.08)"
              />
              <button type="button" class="ghost-button" @click="removeScreenshot(idx)">✕</button>
            </div>
          </div>
        </div>
        <label class="full">
          B站视频链接（可选，如 https://www.bilibili.com/video/BVxxx）
          <input v-model="form.video_url" class="field" placeholder="粘贴B站视频链接" />
        </label>
      </div>
      <div class="toolbar">
        <button class="button">{{ editingId ? '保存修改' : '创建线路' }}</button>
        <button class="ghost-button" type="button" @click="resetForm">清空表单</button>
      </div>
    </form>
  </div>
</template>

<style scoped>
.asset-library {
  min-width: 180px;
}
.lineup-relation {
  margin: 4px 0;
  font-size: 12px;
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
  flex-basis: 100%;
  padding: 10px;
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 8px;
  background: rgba(255,255,255,0.02);
}
.lineup-preview {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.lineup-radar-stage {
  position: relative;
  overflow: hidden;
  border-radius: 8px;
  border: 1px solid rgba(255,255,255,0.08);
}
.lineup-radar-stage img {
  display: block;
  width: 100%;
}
.lineup-preview-svg {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}
.lineup-preview-point {
  position: absolute;
  transform: translate(-50%, -50%);
  border: 2px solid #fff;
  border-radius: 999px;
  padding: 2px 6px;
  color: #07111f;
  font-size: 11px;
  font-weight: 800;
  white-space: nowrap;
}
.linked-point-editor {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 12px;
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 8px;
  background: rgba(255,255,255,0.03);
}
.linked-point-editor .ghost-button.active {
  border-color: rgba(255,122,24,0.45);
  color: #ffb88c;
  background: rgba(255,122,24,0.12);
}
.linked-point-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}
.linked-point-grid .full {
  grid-column: 1 / -1;
}
.point-reference-hint {
  display: block;
  margin-top: 4px;
  font-size: 11px;
}
@media (max-width: 720px) {
  .linked-point-grid {
    grid-template-columns: 1fr;
  }
}
</style>

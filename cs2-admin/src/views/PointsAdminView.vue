<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';

import { api, resolveAssetUrl } from '../api';
import AssetPicker from '../components/AssetPicker.vue';
import { useSessionStore } from '../stores/session';
import type { AdminMap, AdminPoint } from '../types';

const session = useSessionStore();
const maps = ref<AdminMap[]>([]);
const points = ref<AdminPoint[]>([]);
const editingId = ref<number | null>(null);
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
  { value: 'site', label: '落点' },
  { value: 'staging', label: '起点' },
  { value: 'aim', label: '瞄点' },
  { value: 'utility', label: '通用道具点' },
  { value: 'anchor', label: '站位点' },
];

function pointTypeLabel(value: string) {
  return POINT_TYPE_OPTIONS.find((item) => item.value === value)?.label || value;
}

const currentMap = computed(() => maps.value.find((map) => map.id === form.map_id) || null);
const currentRadarUrl = computed(() =>
  currentMap.value ? resolveAssetUrl(`/static/assets/maps/radars/${currentMap.value.slug}-radar.png`) : '',
);

const groupedPoints = computed(() =>
  maps.value.map((map) => ({
    map,
    items: points.value.filter((point) => point.map_id === map.id),
  })),
);

async function load() {
  const [mapItems, pointItems] = await Promise.all([api.maps(session.token), api.points(session.token)]);
  maps.value = mapItems;
  points.value = pointItems;
  if (!editingId.value && mapItems[0]) {
    form.map_id = mapItems[0].id;
  }
}

function edit(item: AdminPoint) {
  editingId.value = item.id;
  Object.assign(form, {
    ...item,
    tagsText: item.tags.join(', '),
    description: item.description || '',
    aim_image_url: item.aim_image_url || '',
    effect_image_url: item.effect_image_url || '',
    video_url: item.video_url || '',
  });
}

function resetForm() {
  editingId.value = null;
  Object.assign(form, {
    map_id: maps.value[0]?.id || 1,
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
}

function setPointFromRadar(event: MouseEvent) {
  const target = event.currentTarget as HTMLElement;
  const rect = target.getBoundingClientRect();
  form.x = Number((((event.clientX - rect.left) / rect.width) * 100).toFixed(2));
  form.y = Number((((event.clientY - rect.top) / rect.height) * 100).toFixed(2));
}

async function submit() {
  const payload = {
    map_id: form.map_id,
    name: form.name,
    key: form.key,
    x: form.x,
    y: form.y,
    side: form.side,
    point_type: form.point_type,
    tags: form.tagsText
      .split(',')
      .map((item) => item.trim())
      .filter(Boolean),
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
  resetForm();
  await load();
}

onMounted(load);
</script>

<template>
  <div class="page-header">
    <h1>点位管理</h1>
    <p class="muted">维护地图雷达坐标、瞄点图、效果图和视频，前台点击雷达点位即可查看。</p>
  </div>
  <div class="content-grid">
    <section class="panel list-stack">
      <article v-for="group in groupedPoints" :key="group.map.id" class="list-item">
        <strong>{{ group.map.name }}</strong>
        <div class="list-stack" style="margin-top: 12px">
          <div v-for="point in group.items" :key="point.id" class="list-item">
            <div class="inline-row">
              <span>{{ point.name }}</span>
              <span class="chip">{{ pointTypeLabel(point.point_type) }}</span>
              <span class="chip">{{ point.side }}</span>
            </div>
            <div class="muted">{{ point.x }} / {{ point.y }}</div>
            <div class="toolbar">
              <button class="ghost-button" @click="edit(point)">编辑</button>
            </div>
          </div>
        </div>
      </article>
    </section>

    <form class="panel" @submit.prevent="submit">
      <h2>{{ editingId ? '编辑点位' : '新增点位' }}</h2>
      <div class="form-grid">
        <label>
          地图
          <select v-model.number="form.map_id" class="select">
            <option v-for="map in maps" :key="map.id" :value="map.id">{{ map.name }}</option>
          </select>
        </label>
        <label>
          名称
          <input v-model="form.name" class="field" />
        </label>
        <label>
          Key
          <input v-model="form.key" class="field" />
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
          <input v-model.number="form.x" type="number" min="0" max="100" class="field" />
        </label>
        <label>
          坐标 Y
          <input v-model.number="form.y" type="number" min="0" max="100" class="field" />
        </label>
        <div class="full radar-picker">
          <div class="inline-row" style="justify-content:space-between">
            <strong>雷达图选点</strong>
            <span class="muted">点击雷达图设置 X / Y</span>
          </div>
          <div v-if="currentRadarUrl" class="radar-stage" @click="setPointFromRadar">
            <img :src="currentRadarUrl" :alt="currentMap?.name || 'radar'" />
            <span
              class="radar-marker"
              :style="{ left: `${form.x}%`, top: `${form.y}%` }"
            />
          </div>
        </div>
        <label>
          类型
          <select v-model="form.point_type" class="select">
            <option v-for="item in POINT_TYPE_OPTIONS" :key="item.value" :value="item.value">
              {{ item.label }} / {{ item.value }}
            </option>
          </select>
        </label>
        <label class="full">
          标签（逗号分隔）
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
        </label>
        <label class="full">
          视频 URL（可填 B 站 BV 链接）
          <input v-model="form.video_url" class="field" />
        </label>
      </div>
      <div class="toolbar">
        <button class="button">{{ editingId ? '保存修改' : '创建点位' }}</button>
        <button class="ghost-button" type="button" @click="resetForm">清空表单</button>
      </div>
    </form>
  </div>
</template>

<style scoped>
.radar-picker {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.radar-stage {
  position: relative;
  overflow: hidden;
  border-radius: 8px;
  border: 1px solid rgba(255,255,255,0.08);
  cursor: crosshair;
}
.radar-stage img {
  display: block;
  width: 100%;
}
.radar-marker {
  position: absolute;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  border: 2px solid #fff;
  background: #ff7a18;
  transform: translate(-50%, -50%);
  box-shadow: 0 0 0 6px rgba(255,122,24,0.22);
  pointer-events: none;
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
</style>

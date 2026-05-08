<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';

import { api } from '../api';
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
});

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
  });
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
    <p class="muted">维护地图坐标点，为线路和战术步骤提供锚点。</p>
  </div>
  <div class="content-grid">
    <section class="panel list-stack">
      <article v-for="group in groupedPoints" :key="group.map.id" class="list-item">
        <strong>{{ group.map.name }}</strong>
        <div class="list-stack" style="margin-top: 12px">
          <div v-for="point in group.items" :key="point.id" class="list-item">
            <div class="inline-row">
              <span>{{ point.name }}</span>
              <span class="chip">{{ point.point_type }}</span>
              <span class="chip">{{ point.side }}</span>
            </div>
            <div class="muted">{{ point.x }} / {{ point.y }}</div>
            <button class="ghost-button" @click="edit(point)">编辑</button>
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
        <label>
          类型
          <select v-model="form.point_type" class="select">
            <option value="site">site</option>
            <option value="staging">staging</option>
            <option value="aim">aim</option>
            <option value="utility">utility</option>
            <option value="anchor">anchor</option>
          </select>
        </label>
        <label class="full">
          标签（逗号分隔）
          <input v-model="form.tagsText" class="field" />
        </label>
      </div>
      <div class="toolbar">
        <button class="button">{{ editingId ? '保存修改' : '创建点位' }}</button>
        <button class="ghost-button" type="button" @click="resetForm">清空表单</button>
      </div>
    </form>
  </div>
</template>

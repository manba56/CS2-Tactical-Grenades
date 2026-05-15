<script setup lang="ts">
import { onMounted, reactive, ref, watch } from 'vue';

import { api, resolveAssetUrl } from '../api';
import { useSessionStore } from '../stores/session';
import type { AdminMap } from '../types';

const session = useSessionStore();
const maps = ref<AdminMap[]>([]);
const editingId = ref<number | null>(null);
const showForm = ref(false);
const form = reactive<Omit<AdminMap, 'id' | 'tactic_count'>>({
  name: '',
  slug: '',
  overview: '',
  cover_url: '',
  layout_url: '',
  callout_color: '#ff7a18',
  order: 0,
  status: 'draft',
  active_pool: true,
});

function mapPrefix(slug: string) {
  // Determine file prefix from slug (mirage→de_mirage, dust2→de_dust2, etc.)
  const mapping: Record<string, string> = {
    ancient: 'de_ancient', anubis: 'de_anubis', dust2: 'de_dust2',
    inferno: 'de_inferno', mirage: 'de_mirage', nuke: 'de_nuke',
    overpass: 'de_overpass', vertigo: 'de_vertigo', train: 'de_train',
  };
  return mapping[slug] || `de_${slug}`;
}

// Auto-fill URLs when slug changes
watch(() => form.slug, (newSlug) => {
  if (!editingId.value && newSlug.trim()) {
    const prefix = mapPrefix(newSlug.trim().toLowerCase());
    form.cover_url = `/static/assets/maps/icons/${prefix}.png`;
    form.layout_url = `/static/assets/maps/${newSlug.trim().toLowerCase()}-layout.svg`;
    if (!form.name) form.name = newSlug;
  }
});

async function load() {
  maps.value = await api.maps(session.token);
}

function edit(item: AdminMap) {
  editingId.value = item.id;
  showForm.value = true;
  Object.assign(form, { ...item });
}

function resetForm() {
  editingId.value = null;
  showForm.value = false;
  Object.assign(form, {
    name: '',
    slug: '',
    overview: '',
    cover_url: '',
    layout_url: '',
    callout_color: '#ff7a18',
    order: 0,
    status: 'draft',
    active_pool: true,
  });
}

async function submit() {
  if (editingId.value) {
    await api.updateMap(editingId.value, form, session.token);
  } else {
    await api.createMap(form, session.token);
  }
  resetForm();
  await load();
}

onMounted(load);
</script>

<template>
  <div class="page-header">
    <h1>地图管理</h1>
    <p class="muted">维护现役地图池、封面、2D 底图和前台展示顺序。</p>
  </div>
  <div class="content-grid">
    <section class="panel list-stack">
      <div class="toolbar">
        <span class="chip">{{ maps.length }} 张地图</span>
      </div>
      <article v-for="item in maps" :key="item.id" class="list-item">
        <div class="inline-row">
          <strong>{{ item.name }}</strong>
          <span class="chip">{{ item.status }}</span>
          <span class="chip">{{ item.tactic_count }} 战术</span>
        </div>
        <p class="muted">{{ item.overview }}</p>
        <div class="toolbar">
          <button class="ghost-button" @click="edit(item)">编辑</button>
        </div>
      </article>
    </section>

    <div class="panel" style="text-align:center;padding:24px" v-if="!showForm">
      <button class="button" @click="showForm = true">+ 新增地图</button>
    </div>

    <form class="panel" @submit.prevent="submit" v-if="showForm">
      <h2>{{ editingId ? '编辑地图' : '新增地图' }}</h2>
      <div class="form-grid">
        <label>
          名称
          <input v-model="form.name" class="field" />
        </label>
        <label>
          Slug
          <input v-model="form.slug" class="field" placeholder="如 mirage" />
        </label>
        <label class="full">
          概述
          <textarea v-model="form.overview" class="textarea" />
        </label>
        <label class="full">
          封面图 URL（填 Slug 自动生成）
          <div class="cover-row">
            <input v-model="form.cover_url" class="field" style="flex:1" />
            <img v-if="form.cover_url" :src="resolveAssetUrl(form.cover_url)" class="cover-preview" />
          </div>
        </label>
        <label class="full">
          底图 URL（填 Slug 自动生成）
          <input v-model="form.layout_url" class="field" />
        </label>
        <label>
          高亮色
          <input v-model="form.callout_color" class="field" />
        </label>
        <label>
          排序
          <input v-model.number="form.order" type="number" class="field" />
        </label>
        <label>
          状态
          <select v-model="form.status" class="select">
            <option value="draft">draft</option>
            <option value="published">published</option>
            <option value="archived">archived</option>
          </select>
        </label>
        <label>
          现役地图池
          <select v-model="form.active_pool" class="select">
            <option :value="true">true</option>
            <option :value="false">false</option>
          </select>
        </label>
      </div>
      <div class="toolbar">
        <button class="button">{{ editingId ? '保存修改' : '创建地图' }}</button>
        <button class="ghost-button" type="button" @click="resetForm">清空表单</button>
      </div>
    </form>
  </div>
</template>

<style scoped>
.cover-row {
  display: flex;
  gap: 8px;
  align-items: center;
}
.cover-preview {
  width: 60px;
  height: 40px;
  object-fit: cover;
  border-radius: 6px;
  border: 1px solid #333;
  flex-shrink: 0;
}
</style>

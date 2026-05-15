<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue';

import { api } from '../api';
import { useSessionStore } from '../stores/session';
import type { AdminMap } from '../types';

const session = useSessionStore();
const maps = ref<AdminMap[]>([]);
const editingId = ref<number | null>(null);
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

async function load() {
  maps.value = await api.maps(session.token);
}

function edit(item: AdminMap) {
  editingId.value = item.id;
  Object.assign(form, { ...item });
}

function resetForm() {
  editingId.value = null;
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

    <form class="panel" @submit.prevent="submit">
      <h2>{{ editingId ? '编辑地图' : '新增地图' }}</h2>
      <div class="form-grid">
        <label>
          名称
          <input v-model="form.name" class="field" />
        </label>
        <label>
          Slug
          <input v-model="form.slug" class="field" />
        </label>
        <label class="full">
          概述
          <textarea v-model="form.overview" class="textarea" />
        </label>
        <label class="full">
          封面图 URL
          <input v-model="form.cover_url" class="field" />
        </label>
        <label class="full">
          底图 URL
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

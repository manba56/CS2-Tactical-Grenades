<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue';

import { api } from '../api';
import { useSessionStore } from '../stores/session';
import type { AdminCollection, AdminTactic } from '../types';

const session = useSessionStore();
const items = ref<AdminCollection[]>([]);
const tactics = ref<AdminTactic[]>([]);
const error = ref('');
const editingId = ref<number | null>(null);

const form = reactive({
  title: '',
  slug: '',
  description: '',
  cover_url: '',
  tactic_ids: [] as number[],
  status: 'draft',
});

async function load() {
  try {
    [items.value, tactics.value] = await Promise.all([
      api.collections(session.token),
      api.tactics(session.token),
    ]);
  } catch (err) {
    error.value = err instanceof Error ? err.message : '加载失败';
  }
}

function edit(item: AdminCollection) {
  editingId.value = item.id;
  Object.assign(form, { ...item });
}

function resetForm() {
  editingId.value = null;
  Object.assign(form, {
    title: '', slug: '', description: '', cover_url: '',
    tactic_ids: [], status: 'draft',
  });
}

function toggleTactic(tid: number) {
  const idx = form.tactic_ids.indexOf(tid);
  if (idx >= 0) form.tactic_ids.splice(idx, 1);
  else form.tactic_ids.push(tid);
}

async function submit() {
  const payload = { ...form };
  if (editingId.value) {
    await api.updateCollection(editingId.value, payload, session.token);
  } else {
    await api.createCollection(payload, session.token);
  }
  resetForm();
  await load();
}

async function remove(item: AdminCollection) {
  if (!confirm(`删除合集"${item.title}"?`)) return;
  await api.deleteCollection(item.id, session.token);
  await load();
}

onMounted(load);
</script>

<template>
  <section>
    <div class="section-heading">
      <h1>战术合集</h1>
    </div>
    <p v-if="error" class="danger">{{ error }}</p>

    <!-- List -->
    <div class="list-section">
      <article v-for="item in items" :key="item.id" class="list-item">
        <div>
          <strong>{{ item.title }}</strong>
          <span class="chip" :class="item.status">{{ item.status }}</span>
          <span class="muted">包含 {{ item.tactic_ids?.length || 0 }} 条战术</span>
        </div>
        <div class="list-actions">
          <button class="ghost-button" @click="edit(item)">编辑</button>
          <button class="ghost-button danger" @click="remove(item)">删除</button>
        </div>
      </article>
      <div v-if="!items.length" class="empty-card">暂无合集</div>
    </div>

    <!-- Form -->
    <form class="panel" @submit.prevent="submit">
      <h2>{{ editingId ? '编辑合集' : '新增合集' }}</h2>
      <div class="form-grid">
        <label>标题 <input v-model="form.title" class="field" /></label>
        <label>Slug <input v-model="form.slug" class="field" /></label>
        <label>封面URL <input v-model="form.cover_url" class="field" /></label>
        <label>状态
          <select v-model="form.status" class="select">
            <option value="draft">draft</option>
            <option value="published">published</option>
          </select>
        </label>
        <label class="full">描述 <textarea v-model="form.description" class="textarea" /></label>

        <!-- Tactic picker -->
        <div class="full">
          <div class="muted">选择战术（当前已选 {{ form.tactic_ids.length }} 条）</div>
          <div class="tactic-pick-grid">
            <label
              v-for="t in tactics" :key="t.id"
              class="tactic-pick-chip"
              :class="{ picked: form.tactic_ids.includes(t.id) }"
            >
              <input
                type="checkbox"
                :checked="form.tactic_ids.includes(t.id)"
                @change="toggleTactic(t.id)"
              />
              {{ t.title }}
            </label>
          </div>
        </div>
      </div>
      <div class="form-actions">
        <button class="button">{{ editingId ? '保存修改' : '创建合集' }}</button>
        <button type="button" class="secondary-button" @click="resetForm">取消</button>
      </div>
    </form>
  </section>
</template>

<style scoped>
.list-section {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 24px;
}
.list-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-radius: 10px;
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.06);
}
.list-actions {
  display: flex;
  gap: 8px;
}
.tactic-pick-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
  max-height: 200px;
  overflow-y: auto;
}
.tactic-pick-chip {
  padding: 5px 10px;
  border-radius: 6px;
  border: 1px solid #444;
  font-size: 12px;
  cursor: pointer;
}
.tactic-pick-chip.picked {
  background: #ff7a18;
  border-color: #ff7a18;
  color: #fff;
}
.tactic-pick-chip input {
  display: none;
}
.form-actions {
  margin-top: 12px;
  display: flex;
  gap: 8px;
}
</style>

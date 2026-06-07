<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';

import { api, resolveAssetUrl } from '../api';
import { useSessionStore } from '../stores/session';
import type { AdminLineup, AdminMap, AdminPoint } from '../types';

const session = useSessionStore();
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

const filteredPoints = computed(() => points.value.filter((point) => point.map_id === form.map_id));

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
}

function edit(item: AdminLineup) {
  editingId.value = item.id;
  Object.assign(form, {
    ...item,
    stepsText: (item.steps || []).join('\n'),
    screenshots: (item.media || []).map((url: string) => ({ url, description: '' })),
    video_url: item.video_url || '',
  });
}

function resetForm() {
  editingId.value = null;
  error.value = '';
  const firstPoint = filteredPoints.value[0]?.id || 1;
  Object.assign(form, {
    map_id: maps.value[0]?.id || 1,
    title: '',
    slug: '',
    side: 'T',
    utility_type: 'smoke',
    start_point_id: firstPoint,
    aim_point_id: firstPoint,
    land_point_id: firstPoint,
    purpose: '',
    difficulty: 'medium',
    summary: '',
    stepsText: '',
    screenshots: [],
    video_url: '',
    status: 'draft',
  });
}

async function aiFill(field: 'summary' | 'purpose' | 'steps') {
  const desc = [form.title, form.title ? '——' : '', form.utility_type || 'smoke', form.side || 'T', '地图 id ' + form.map_id].join(' ');
  try {
    const resp = await api.aiGenerate(desc, field, session.token);
    if (field === 'steps') {
      form.stepsText = resp.result;
    } else {
      (form as any)[field] = resp.result;
    }
  } catch (e: any) {
    alert('AI 生成失败：' + (e.message || '请检查 API Key'));
  }
}

async function submit() {
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
      <h2>{{ editingId ? '编辑线路' : '新增线路' }}</h2>
      <div class="form-grid">
        <label>
          地图
          <select v-model.number="form.map_id" class="select">
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
          <select v-model.number="form.start_point_id" class="select">
            <option v-for="point in filteredPoints" :key="point.id" :value="point.id">{{ point.name }}</option>
          </select>
        </label>
        <label>
          瞄点
          <select v-model.number="form.aim_point_id" class="select">
            <option v-for="point in filteredPoints" :key="point.id" :value="point.id">{{ point.name }}</option>
          </select>
        </label>
        <label>
          落点
          <select v-model.number="form.land_point_id" class="select">
            <option v-for="point in filteredPoints" :key="point.id" :value="point.id">{{ point.name }}</option>
          </select>
        </label>
        <label>
          状态
          <select v-model="form.status" class="select">
            <option value="draft">draft</option>
            <option value="published">published</option>
            <option value="archived">archived</option>
          </select>
        </label>
        <label class="full">
          用途 <button type="button" class="ai-btn" @click="aiFill('purpose')">✨ AI</button>
          <textarea v-model="form.purpose" class="textarea" />
        </label>
        <label class="full">
          摘要 <button type="button" class="ai-btn" @click="aiFill('summary')">AI 生成</button>
          <textarea v-model="form.summary" class="textarea" />
        </label>
        <label class="full">
          步骤（每行一条） <button type="button" class="ai-btn" @click="aiFill('steps')">AI 生成</button>
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

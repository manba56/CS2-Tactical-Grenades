<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';

import { api, resolveAssetUrl } from '../api';
import RouteEditor from '../components/RouteEditor.vue';
import { useSessionStore } from '../stores/session';
import type { AdminLineup, AdminMap, AdminTactic, RouteData, ScreenshotItem } from '../types';

const session = useSessionStore();
const maps = ref<AdminMap[]>([]);
const lineups = ref<AdminLineup[]>([]);
const tactics = ref<AdminTactic[]>([]);
const editingId = ref<number | null>(null);
const form = reactive({
  map_id: 1,
  title: '',
  slug: '',
  side: 'T',
  goal: '',
  phase: 'exec',
  difficulty: 'medium',
  players: 3,
  summary: '',
  note: '',
  tagsText: '',
  cover_url: '',
  featured: false,
  status: 'draft',
  stepsText: '1|主道具位|utility|补首颗关键烟|',
  routes: [] as RouteData[],
  screenshots: [] as ScreenshotItem[],
});

const currentMapSlug = computed(() => {
  const map = maps.value.find(m => m.id === form.map_id);
  return map?.slug || 'mirage';
});

const filteredLineups = computed(() => lineups.value.filter((lineup) => lineup.map_id === form.map_id));

async function load() {
  const [mapItems, lineupItems, tacticItems] = await Promise.all([
    api.maps(session.token),
    api.lineups(session.token),
    api.tactics(session.token),
  ]);
  maps.value = mapItems;
  lineups.value = lineupItems;
  tactics.value = tacticItems;
  if (!editingId.value && mapItems[0]) {
    form.map_id = mapItems[0].id;
  }
}

function serializeSteps(stepItems: AdminTactic['step_items']) {
  return stepItems
    .map((item) => `${item.order}|${item.role}|${item.type}|${item.instruction}|${item.lineup_id ?? ''}`)
    .join('\n');
}

function parseSteps() {
  return form.stepsText
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const [order, role, type, instruction, lineupId] = line.split('|');
      return {
        order: Number(order),
        role,
        type,
        instruction,
        lineup_id: lineupId ? Number(lineupId) : null,
      };
    });
}

function addScreenshot(type: 'route' | 'spot' = 'spot') {
  form.screenshots.push({ url: '', description: '', type });
}
function removeScreenshot(index: number) {
  form.screenshots.splice(index, 1);
}
async function uploadScreenshot(index: number, file: File) {
  try {
    const result = await api.uploadAsset(file, session.token);
    form.screenshots[index].url = result.url;
  } catch (err) {
    console.error('Upload failed:', err);
    alert('上传失败');
  }
}

const routeScreenshots = computed(() =>
  form.screenshots.flatMap((s, i) => s.type === 'route' ? [{ shot: s, formIdx: i }] : [])
);
const spotScreenshots = computed(() =>
  form.screenshots.flatMap((s, i) => s.type === 'spot' ? [{ shot: s, formIdx: i }] : [])
);

function edit(item: AdminTactic) {
  editingId.value = item.id;
  Object.assign(form, {
    ...item,
    tagsText: item.tags.join(', '),
    stepsText: serializeSteps(item.step_items),
    routes: item.routes ? JSON.parse(JSON.stringify(item.routes)) : [],
    screenshots: item.screenshots ? JSON.parse(JSON.stringify(item.screenshots)) : [],
  });
}

function resetForm() {
  editingId.value = null;
  Object.assign(form, {
    map_id: maps.value[0]?.id || 1,
    title: '',
    slug: '',
    side: 'T',
    goal: '',
    phase: 'exec',
    difficulty: 'medium',
    players: 3,
    summary: '',
    note: '',
    tagsText: '',
    cover_url: '',
    featured: false,
    status: 'draft',
    stepsText: '1|主道具位|utility|补首颗关键烟|',
    routes: [] as RouteData[],
    screenshots: [] as ScreenshotItem[],
  });
}

async function submit() {
  const payload = {
    map_id: form.map_id,
    title: form.title,
    slug: form.slug,
    side: form.side,
    goal: form.goal,
    phase: form.phase,
    difficulty: form.difficulty,
    players: form.players,
    summary: form.summary,
    note: form.note,
    tags: form.tagsText.split(',').map((item) => item.trim()).filter(Boolean),
    cover_url: form.cover_url,
    featured: form.featured,
    status: form.status,
    step_items: parseSteps(),
    routes: form.routes,
    screenshots: form.screenshots,
  };

  if (editingId.value) {
    await api.updateTactic(editingId.value, payload, session.token);
  } else {
    await api.createTactic(payload, session.token);
  }
  resetForm();
  await load();
}

async function publish(item: AdminTactic) {
  await api.publishTactic(item.id, session.token);
  await load();
}

async function archive(item: AdminTactic) {
  await api.archiveTactic(item.id, session.token);
  await load();
}

onMounted(load);
</script>

<template>
  <div class="page-header">
    <h1>战术管理</h1>
    <p class="muted">用步骤顺序把多条线路拼成完整执行，并决定是否发布到前台。</p>
  </div>
  <div class="content-grid">
    <section class="panel list-stack">
      <article v-for="item in tactics" :key="item.id" class="list-item">
        <div class="inline-row">
          <strong>{{ item.title }}</strong>
          <span class="chip">{{ item.status }}</span>
          <span class="chip">{{ item.phase }}</span>
          <span class="chip">{{ item.players }} 人</span>
        </div>
        <p class="muted">{{ item.summary }}</p>
        <div class="toolbar">
          <button class="ghost-button" @click="edit(item)">编辑</button>
          <button class="ghost-button" @click="publish(item)">发布</button>
          <button class="ghost-button" @click="archive(item)">归档</button>
        </div>
      </article>
    </section>

    <form class="panel" @submit.prevent="submit">
      <h2>{{ editingId ? '编辑战术' : '新增战术' }}</h2>
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
          目标
          <input v-model="form.goal" class="field" placeholder="A 点爆弹 / 外场转地下" />
        </label>
        <label>
          执行阶段
          <select v-model="form.phase" class="select">
            <option value="pistol">pistol</option>
            <option value="default">default</option>
            <option value="mid-round">mid-round</option>
            <option value="exec">exec</option>
            <option value="retake">retake</option>
            <option value="late-round">late-round</option>
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
          参与人数
          <input v-model.number="form.players" type="number" min="1" max="5" class="field" />
        </label>
        <label class="full">
          摘要
          <textarea v-model="form.summary" class="textarea" />
        </label>
        <label class="full">
          注意事项
          <textarea v-model="form.note" class="textarea" />
        </label>
        <label class="full">
          封面 URL
          <input v-model="form.cover_url" class="field" />
        </label>
        <label class="full">
          标签（逗号分隔）
          <input v-model="form.tagsText" class="field" />
        </label>
        <label>
          Featured
          <select v-model="form.featured" class="select">
            <option :value="true">true</option>
            <option :value="false">false</option>
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
          步骤定义（每行：序号|角色|类型|说明|lineupId）
          <textarea v-model="form.stepsText" class="textarea" />
        </label>
        <div class="full">
          <RouteEditor v-model="form.routes" :map-slug="currentMapSlug" />
        </div>
        <!-- 路线截图 -->
        <div class="full">
          <div class="screenshots-section">
            <div class="screenshots-header">
              <h3>路线截图</h3>
              <span class="chip">先上传手绘路线图</span>
              <button type="button" class="ghost-button" @click="addScreenshot('route')">+ 添加路线截图</button>
            </div>
            <p class="muted">在外面画好的进攻路线图。雷达底图在 /static/assets/maps/radars/ 下，右键雷达图复制链接即可获取。</p>
            <div v-if="routeScreenshots.length === 0" class="screenshot-placeholder">
              还没有路线截图，点「+ 添加路线截图」
            </div>
            <div v-for="item in routeScreenshots" :key="item.formIdx" class="screenshot-card">
              <label class="field-label">描述</label>
              <textarea
                v-model="item.shot.description"
                class="field textarea"
                rows="2"
                placeholder="如：P1突破手路线、P2辅助路线、全体进攻路线"
              />
              <div class="screenshot-row" style="margin-top:8px">
                <input
                  type="file"
                  class="field"
                  accept="image/*"
                  @change="(e) => { const f = e.target?.files?.[0]; if (f) uploadScreenshot(item.formIdx, f); }"
                />
                <button type="button" class="ghost-button" @click="removeScreenshot(item.formIdx)">删除</button>
              </div>
              <img
                v-if="item.shot.url"
                :src="resolveAssetUrl(item.shot.url)"
                class="screenshot-preview"
                :alt="item.shot.description || '路线截图'"
              />
              <div v-else class="screenshot-placeholder">选择图片上传后自动预览</div>
            </div>
          </div>
        </div>

        <!-- 点位截图 -->
        <div class="full">
          <div class="screenshots-section">
            <div class="screenshots-header">
              <h3>点位截图</h3>
              <span class="chip">道具瞄点/落点</span>
              <button type="button" class="ghost-button" @click="addScreenshot('spot')">+ 添加点位截图</button>
            </div>
            <p class="muted">烟雾弹瞄点、闪光弹落点等道具截图。</p>
            <div v-if="spotScreenshots.length === 0" class="screenshot-placeholder">
              还没有点位截图，点「+ 添加点位截图」
            </div>
            <div v-for="item in spotScreenshots" :key="item.formIdx" class="screenshot-card">
              <label class="field-label">描述</label>
              <textarea
                v-model="item.shot.description"
                class="field textarea"
                rows="2"
                placeholder="如：A点烟雾弹瞄点、窗口闪落点..."
              />
              <div class="screenshot-row" style="margin-top:8px">
                <input
                  type="file"
                  class="field"
                  accept="image/*"
                  @change="(e) => { const f = e.target?.files?.[0]; if (f) uploadScreenshot(item.formIdx, f); }"
                />
                <button type="button" class="ghost-button" @click="removeScreenshot(item.formIdx)">删除</button>
              </div>
              <img
                v-if="item.shot.url"
                :src="resolveAssetUrl(item.shot.url)"
                class="screenshot-preview"
                :alt="item.shot.description || '点位截图'"
              />
              <div v-else class="screenshot-placeholder">选择图片上传后自动预览</div>
            </div>
          </div>
        </div>
      </div>
      <div class="toolbar">
        <button class="button">{{ editingId ? '保存修改' : '创建战术' }}</button>
        <button class="ghost-button" type="button" @click="resetForm">清空表单</button>
      </div>

      <div class="panel" style="margin-top: 18px; padding: 16px">
        <h3>当前地图可用线路</h3>
        <div class="list-stack">
          <div v-for="lineup in filteredLineups" :key="lineup.id" class="list-item">
            <div class="inline-row">
              <strong>#{{ lineup.id }}</strong>
              <span>{{ lineup.title }}</span>
              <span class="chip">{{ lineup.utility_type }}</span>
            </div>
          </div>
        </div>
      </div>
    </form>
  </div>
</template>

<style scoped>
.screenshots-section {
  margin-top: 12px;
}
.screenshots-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}
.screenshots-header h3 {
  margin: 0;
  font-size: 14px;
}
.screenshot-card {
  border: 1px solid #333;
  border-radius: 8px;
  padding: 10px;
  margin-bottom: 10px;
  background: #141428;
}
.screenshot-row {
  display: flex;
  gap: 8px;
  align-items: center;
}
.screenshot-preview {
  max-width: 100%;
  max-height: 300px;
  border-radius: 6px;
  margin-top: 8px;
  display: block;
}
.screenshot-placeholder {
  border: 2px dashed #333;
  border-radius: 6px;
  padding: 32px 16px;
  text-align: center;
  color: #555;
  font-size: 12px;
}
.field-label {
  display: block;
  font-size: 12px;
  color: #888;
  margin-bottom: 4px;
}
.textarea {
  resize: vertical;
  min-height: 50px;
}
</style>

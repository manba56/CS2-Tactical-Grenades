<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue';

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
  video_url: '',
  featured: false,
  status: 'draft',
  routes: [] as RouteData[],
  screenshots: [] as ScreenshotItem[],
});

const stepItems = ref<{ order: number; role: string; type: string; instruction: string; lineup_id: number | null }[]>(
  [{ order: 1, role: '主道具位', type: 'utility', instruction: '补首颗关键烟', lineup_id: null }]
);

const quickLineup = reactive({ title: '', utility_type: 'smoke', difficulty: 'easy' });
async function createInlineLineup() {
  if (!quickLineup.title) return;
  const map_points = await api.points(session.token);
  const mapId = form.map_id;
  const firstPoint = map_points.find((p: any) => p.map_id === mapId);
  const pid = firstPoint?.id || 1;
  const result = await api.createLineup({
    map_id: mapId, title: quickLineup.title, slug: '',
    side: form.side, utility_type: quickLineup.utility_type,
    start_point_id: pid, aim_point_id: pid, land_point_id: pid,
    purpose: '', difficulty: quickLineup.difficulty,
    summary: '', steps: [], media: [], video_url: '', status: 'published',
  } as any, session.token);
  await load();
  // Auto-select the new lineup in the last step
  const lastStep = stepItems.value[stepItems.value.length - 1];
  if (lastStep && !lastStep.lineup_id) lastStep.lineup_id = (result as any).id;
  quickLineup.title = '';
  alert(`线路"${(result as any).title}"已创建并关联`);
}

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
  _syncCoverUrl();
}


function _syncCoverUrl() {
  if (editingId.value) return;
  const map = maps.value.find(m => m.id === form.map_id);
  if (!map) return;
  form.cover_url = map.cover_url
    || `/static/assets/maps/radars/${map.slug}-radar.png`
    || map.layout_url;
}

watch(() => form.map_id, () => _syncCoverUrl());

function serializeSteps(stepItems: AdminTactic['step_items']) {
  return stepItems
    .map((item) => `${item.order}|${item.role}|${item.type}|${item.instruction}|${item.lineup_id ?? ''}`)
    .join('\n');
}

function getStepPayload() {
  return stepItems.value.map((s, i) => ({ ...s, order: i + 1 }));
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

const slugPreview = computed(() => {
  if (form.slug) return form.slug;
  return (form.title || 'tactic').replace(/[^\\w\\-\\u4e00-\\u9fff]+/g, '-').replace(/^-|-$/g, '').toLowerCase() || 'tactic';
});

function edit(item: AdminTactic) {
  editingId.value = item.id;
  Object.assign(form, {
    ...item,
    tagsText: item.tags.join(', '),
    video_url: item.video_url || '',
    routes: item.routes ? JSON.parse(JSON.stringify(item.routes)) : [],
    screenshots: item.screenshots ? JSON.parse(JSON.stringify(item.screenshots)) : [],
  });
  stepItems.value = (item.step_items || [{ order: 1, role: '主道具位', type: 'utility', instruction: '', lineup_id: null }])
    .map((s: any) => ({ order: s.order, role: s.role, type: s.type, instruction: s.instruction, lineup_id: s.lineup_id }));
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
    video_url: '',
    featured: false,
    status: 'draft',
    routes: [] as RouteData[],
    screenshots: [] as ScreenshotItem[],
  });
  stepItems.value = [{ order: 1, role: '主道具位', type: 'utility', instruction: '补首颗关键烟', lineup_id: null }];
}

async function submit() {
  // Duplicate detection
  if (!editingId.value) {
    const dup = tactics.value.find(t => t.title === form.title);
    if (dup && !confirm(`已有同名战术"${form.title}"（ID: ${dup.id}），确定创建副本？`)) return;
  }

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
    video_url: form.video_url,
    featured: form.featured,
    status: form.status,
    step_items: getStepPayload(),
    routes: form.routes,
    screenshots: form.screenshots,
  };

  if (editingId.value) {
    await api.updateTactic(editingId.value, payload, session.token);
    editingId.value = null;
  } else {
    const created = await api.createTactic(payload, session.token);
    editingId.value = (created as any).id;
    form.slug = (created as any).slug || '';
  }
  await load();
}

function clone(item: AdminTactic) {
  Object.assign(form, { ...item, title: item.title + ' (副本)', slug: '' });
  editingId.value = null;
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

async function aiFill() {
  const mapItem = maps.value.find(m => m.id === form.map_id);
  try {
    const resp = await api.aiGenerate({
      map: mapItem?.name || '',
      side: form.side,
      goal: form.goal,
      phase: form.phase,
      difficulty: form.difficulty,
      players: form.players,
      utility_type: stepItems.value[0]?.type || 'utility',
    }, session.token);

    if (resp.summary) form.summary = resp.summary;
    if (resp.note) form.note = resp.note;
    if (resp.steps) {
      stepItems.value = resp.steps.split('\n').filter(Boolean).map((line, i) => ({
        order: i+1, role: '主道具位', type: 'utility', instruction: line, lineup_id: null
      }));
    }
  } catch (e: any) {
    alert('AI 生成失败：' + (e.message || '请检查 API Key'));
  }
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
          <button class="ghost-button" @click="clone(item)">克隆</button>
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
          <select v-model.number="form.map_id" class="select" @change="_syncCoverUrl()">
            <option v-for="map in maps" :key="map.id" :value="map.id">{{ map.name }}</option>
          </select>
        </label>
        <label>
          标题
          <input v-model="form.title" class="field" />
        </label>
        <label>
          Slug <span class="muted" style="font-size:11px">预览: {{ slugPreview }}</span>
          <input v-model="form.slug" class="field" :placeholder="slugPreview" />
        </label>
        <label>
          阵营
          <select v-model="form.side" class="select">
            <option value="T">T</option>
            <option value="CT">CT</option>
          </select>
        </label>
        <label>
          目标 <button type="button" class="ai-btn" @click="aiFill()">AI 生成</button>
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
          摘要 <button type="button" class="ai-btn" @click="aiFill()">AI 生成</button>
          <textarea v-model="form.summary" class="textarea" />
        </label>
        <label class="full">
          注意事项
          <textarea v-model="form.note" class="textarea" />
        </label>
        <label class="full">
          封面 URL（选地图自动填，可手动改）
          <div class="cover-row">
            <input v-model="form.cover_url" class="field" style="flex:1" />
            <img v-if="form.cover_url" :src="resolveAssetUrl(form.cover_url)" class="cover-preview" />
          </div>
        </label>
        <label class="full">
          标签（逗号分隔）
          <input v-model="form.tagsText" class="field" />
        </label>
        <label class="full">
          B站视频链接（可选，如 https://www.bilibili.com/video/BVxxx）
          <input v-model="form.video_url" class="field" placeholder="粘贴B站视频链接" />
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
        <!-- Visual step editor -->
        <div class="full steps-editor">
          <h3>执行步骤 <button type="button" class="ai-btn" @click="aiFill()">AI 生成</button></h3>
          <div v-for="(step, i) in stepItems" :key="i" class="step-row">
            <span class="step-num">{{ i + 1 }}</span>
            <select v-model="step.role" class="select" style="min-width:100px">
              <option value="主道具位">主道具位</option><option value="二道具位">二道具位</option>
              <option value="主突破">主突破</option><option value="补枪位">补枪位</option>
              <option value="侦查位">侦查位</option><option value="辅助位">辅助位</option>
            </select>
            <select v-model="step.type" class="select" style="min-width:90px">
              <option value="utility">utility</option><option value="move">move</option>
              <option value="hold">hold</option><option value="trade">trade</option>
            </select>
            <select v-model="step.lineup_id" class="select" style="min-width:120px">
              <option :value="null">无线路</option>
              <option v-for="l in filteredLineups" :key="l.id" :value="l.id">{{ l.title }}</option>
            </select>
            <input v-model="step.instruction" class="field" placeholder="步骤说明" style="flex:1" />
            <button type="button" class="ghost-button" @click="stepItems.splice(i,1)" :disabled="stepItems.length<=1">✕</button>
          </div>
          <button type="button" class="ghost-button" @click="stepItems.push({order:stepItems.length+1,role:'主道具位',type:'utility',instruction:'',lineup_id:null})">+ 添加步骤</button>
          <p class="muted" style="font-size:11px;margin-top:4px">选择角色和动作类型，绑定已有的线路道具</p>
          <!-- Quick-create lineup inline -->
          <details style="margin-top:8px">
            <summary class="ghost-button" style="cursor:pointer;font-size:12px">+ 快速新建线路</summary>
            <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:8px;padding:10px;border:1px solid rgba(255,255,255,0.08);border-radius:8px">
              <input v-model="quickLineup.title" class="field" placeholder="线路标题" style="flex:1;min-width:140px" />
              <select v-model="quickLineup.utility_type" class="select"><option value="smoke">smoke</option><option value="flash">flash</option><option value="molotov">molotov</option><option value="he">he</option><option value="decoy">decoy</option></select>
              <select v-model="quickLineup.difficulty" class="select"><option value="easy">easy</option><option value="medium">medium</option><option value="hard">hard</option></select>
              <button type="button" class="primary-button small" @click="createInlineLineup()" :disabled="!quickLineup.title">创建并关联</button>
            </div>
          </details>
        </div>
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

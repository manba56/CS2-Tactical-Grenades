<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';

import { api, resolveAssetUrl } from '../api';
import AssetPicker from '../components/AssetPicker.vue';
import { useSessionStore } from '../stores/session';
import type { AdminLineup, AdminMap, AdminPoint } from '../types';

type PairRole = 'aim' | 'land';
type PointDraft = {
  name: string;
  key: string;
  x: number;
  y: number;
  side: string;
  tagsText: string;
  description: string;
  aim_image_url: string;
  effect_image_url: string;
  video_url: string;
};

const session = useSessionStore();
const maps = ref<AdminMap[]>([]);
const points = ref<AdminPoint[]>([]);
const lineups = ref<AdminLineup[]>([]);
const selectedMapId = ref(1);
const activeRole = ref<PairRole>('aim');
const editingLineupId = ref<number | null>(null);
const editingAimPointId = ref<number | null>(null);
const editingLandPointId = ref<number | null>(null);
const error = ref('');
const uploadingMedia = ref<PairRole | ''>('');

const lineupForm = reactive({
  title: '',
  slug: '',
  side: 'T',
  utility_type: 'smoke',
  purpose: '',
  difficulty: 'medium',
  summary: '',
  stepsText: '',
  video_url: '',
  status: 'draft',
});

const aimDraft = reactive<PointDraft>({
  name: '',
  key: '',
  x: 50,
  y: 50,
  side: 'BOTH',
  tagsText: '',
  description: '',
  aim_image_url: '',
  effect_image_url: '',
  video_url: '',
});

const landDraft = reactive<PointDraft>({
  name: '',
  key: '',
  x: 50,
  y: 50,
  side: 'BOTH',
  tagsText: '',
  description: '',
  aim_image_url: '',
  effect_image_url: '',
  video_url: '',
});

const POINT_ROLE_META: Record<PairRole, { label: string; color: string; pointType: 'staging' | 'site' }> = {
  aim: { label: '瞄点', color: '#65d6ce', pointType: 'staging' },
  land: { label: '落点', color: '#f5d76e', pointType: 'site' },
};

const currentMap = computed(() => maps.value.find((map) => map.id === selectedMapId.value) || null);
const currentRadarUrl = computed(() =>
  currentMap.value ? resolveAssetUrl(`/static/assets/maps/radars/${currentMap.value.slug}-radar.png`) : '',
);
const mapPoints = computed(() => points.value.filter((point) => point.map_id === selectedMapId.value));
const aimPoints = computed(() => mapPoints.value.filter((point) => point.point_type !== 'site'));
const landPoints = computed(() => mapPoints.value.filter((point) => point.point_type === 'site'));
const visiblePoints = computed(() => [...aimPoints.value, ...landPoints.value]);
const activeDraft = computed(() => activeRole.value === 'aim' ? aimDraft : landDraft);
const selectedAimPoint = computed(() => editingAimPointId.value ? points.value.find((point) => point.id === editingAimPointId.value) || null : null);
const selectedLandPoint = computed(() => editingLandPointId.value ? points.value.find((point) => point.id === editingLandPointId.value) || null : null);
const editingLineup = computed(() => editingLineupId.value ? lineups.value.find((lineup) => lineup.id === editingLineupId.value) || null : null);

const landLineupCount = computed(() =>
  editingLandPointId.value
    ? lineups.value.filter((lineup) => lineup.land_point_id === editingLandPointId.value).length
    : 0,
);
const pairLineupCount = computed(() =>
  editingAimPointId.value && editingLandPointId.value
    ? lineups.value.filter((lineup) =>
      lineup.start_point_id === editingAimPointId.value &&
      lineup.land_point_id === editingLandPointId.value &&
      lineup.id !== editingLineupId.value,
    ).length
    : 0,
);
const pairLineups = computed(() =>
  lineups.value.filter((lineup) =>
    lineup.map_id === selectedMapId.value &&
    lineup.start_point_id === editingAimPointId.value &&
    lineup.land_point_id === editingLandPointId.value,
  ),
);
const mapLineups = computed(() => lineups.value.filter((lineup) => lineup.map_id === selectedMapId.value));
const previewPath = computed(() => `M${aimDraft.x} ${aimDraft.y} L${landDraft.x} ${landDraft.y}`);

function roleForPoint(point: AdminPoint): PairRole {
  return point.point_type === 'site' ? 'land' : 'aim';
}

function roleLabel(role: PairRole) {
  return POINT_ROLE_META[role].label;
}

function roleColor(role: PairRole) {
  return POINT_ROLE_META[role].color;
}

function pointRoleColor(point: AdminPoint) {
  return roleColor(roleForPoint(point));
}

function refsFor(pointId: number) {
  const asAim = lineups.value.filter((lineup) => lineup.start_point_id === pointId).length;
  const asLand = lineups.value.filter((lineup) => lineup.land_point_id === pointId).length;
  return { aim: asAim, land: asLand, total: asAim + asLand };
}

function pointName(pointId: number) {
  return points.value.find((point) => point.id === pointId)?.name || `#${pointId}`;
}

function parseTags(text: string) {
  return text.split(',').map((item) => item.trim()).filter(Boolean);
}

function clampCoordinate(value: number) {
  return Math.min(100, Math.max(0, Math.round(Number.isFinite(value) ? value : 0)));
}

function normalizeDraftCoordinates(draft: PointDraft) {
  draft.x = clampCoordinate(draft.x);
  draft.y = clampCoordinate(draft.y);
}

function coordsFromRadar(event: MouseEvent) {
  const target = event.currentTarget as HTMLElement;
  const rect = target.getBoundingClientRect();
  return {
    x: clampCoordinate(((event.clientX - rect.left) / rect.width) * 100),
    y: clampCoordinate(((event.clientY - rect.top) / rect.height) * 100),
  };
}

function applyPointToDraft(point: AdminPoint, role = roleForPoint(point)) {
  selectedMapId.value = point.map_id;
  activeRole.value = role;
  if (role === 'aim') editingAimPointId.value = point.id;
  else editingLandPointId.value = point.id;

  Object.assign(role === 'aim' ? aimDraft : landDraft, {
    name: point.name,
    key: point.key,
    x: clampCoordinate(point.x),
    y: clampCoordinate(point.y),
    side: point.side,
    tagsText: (point.tags || []).join(', '),
    description: point.description || '',
    aim_image_url: point.aim_image_url || '',
    effect_image_url: point.effect_image_url || '',
    video_url: point.video_url || '',
  });
}

function selectPoint(point: AdminPoint) {
  applyPointToDraft(point);
}

function setActiveRole(role: PairRole) {
  activeRole.value = role;
}

function setDraftCoords(event: MouseEvent) {
  const coords = coordsFromRadar(event);
  Object.assign(activeDraft.value, coords);
}

function resetDraft(draft: PointDraft, role: PairRole) {
  Object.assign(draft, {
    name: '',
    key: '',
    x: role === 'aim' ? 42 : 58,
    y: 50,
    side: 'BOTH',
    tagsText: '',
    description: '',
    aim_image_url: '',
    effect_image_url: '',
    video_url: '',
  });
}

function resetForm() {
  editingLineupId.value = null;
  editingAimPointId.value = null;
  editingLandPointId.value = null;
  error.value = '';
  Object.assign(lineupForm, {
    title: '',
    slug: '',
    side: 'T',
    utility_type: 'smoke',
    purpose: '',
    difficulty: 'medium',
    summary: '',
    stepsText: '',
    video_url: '',
    status: 'draft',
  });
  resetDraft(aimDraft, 'aim');
  resetDraft(landDraft, 'land');
  activeRole.value = 'aim';
}

function selectMap(mapId: number) {
  selectedMapId.value = mapId;
  resetForm();
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
  if (mapItems[0] && !mapItems.some((map) => map.id === selectedMapId.value)) {
    selectedMapId.value = mapItems[0].id;
  }
}

function editLineup(lineup: AdminLineup) {
  editingLineupId.value = lineup.id;
  selectedMapId.value = lineup.map_id;
  Object.assign(lineupForm, {
    title: lineup.title || '',
    slug: lineup.slug || '',
    side: lineup.side || 'T',
    utility_type: lineup.utility_type || 'smoke',
    purpose: lineup.purpose || '',
    difficulty: lineup.difficulty || 'medium',
    summary: lineup.summary || '',
    stepsText: (lineup.steps || []).join('\n'),
    video_url: lineup.video_url || '',
    status: lineup.status || 'draft',
  });
  const aimPoint = points.value.find((point) => point.id === lineup.start_point_id);
  const landPoint = points.value.find((point) => point.id === lineup.land_point_id);
  if (aimPoint) applyPointToDraft(aimPoint, 'aim');
  if (landPoint) applyPointToDraft(landPoint, 'land');
  activeRole.value = 'aim';
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function validatePointDraft(role: PairRole, draft: PointDraft, editingId: number | null) {
  normalizeDraftCoordinates(draft);
  if (!draft.name.trim()) return `${roleLabel(role)}名称不能为空`;
  if (!draft.key.trim()) return `${roleLabel(role)} Key 不能为空`;
  const duplicated = points.value.some((point) =>
    point.map_id === selectedMapId.value &&
    point.key === draft.key.trim() &&
    point.id !== editingId,
  );
  if (duplicated) return `同一张地图下 ${draft.key.trim()} 已存在`;
  return '';
}

function buildPointPayload(role: PairRole, draft: PointDraft, original?: AdminPoint) {
  normalizeDraftCoordinates(draft);
  return {
    map_id: selectedMapId.value,
    name: draft.name.trim(),
    key: draft.key.trim(),
    x: draft.x,
    y: draft.y,
    side: draft.side,
    point_type: POINT_ROLE_META[role].pointType,
    tags: parseTags(draft.tagsText),
    description: draft.description,
    aim_image_url: role === 'aim' ? draft.aim_image_url : original?.aim_image_url || '',
    effect_image_url: role === 'land' ? draft.effect_image_url : original?.effect_image_url || '',
    video_url: draft.video_url,
  };
}

async function savePoint(role: PairRole, draft: PointDraft, editingId: number | null) {
  const original = editingId ? points.value.find((point) => point.id === editingId) : undefined;
  const payload = buildPointPayload(role, draft, original);
  if (editingId) {
    const updated = await api.updatePoint(editingId, payload, session.token);
    return updated.id;
  }
  const created = await api.createPoint(payload, session.token);
  return created.id;
}

function defaultLineupTitle() {
  const mapName = currentMap.value?.name || '地图';
  return `${mapName} ${aimDraft.name.trim()} -> ${landDraft.name.trim()} ${lineupForm.utility_type}`;
}

async function submitPair() {
  error.value = '';
  const aimError = validatePointDraft('aim', aimDraft, editingAimPointId.value);
  const landError = validatePointDraft('land', landDraft, editingLandPointId.value);
  if (aimError || landError) {
    error.value = aimError || landError;
    return;
  }

  const aimPointId = await savePoint('aim', aimDraft, editingAimPointId.value);
  const landPointId = await savePoint('land', landDraft, editingLandPointId.value);
  editingAimPointId.value = aimPointId;
  editingLandPointId.value = landPointId;

  const payload = {
    map_id: selectedMapId.value,
    title: lineupForm.title.trim() || defaultLineupTitle(),
    slug: lineupForm.slug.trim(),
    side: lineupForm.side,
    utility_type: lineupForm.utility_type,
    start_point_id: aimPointId,
    aim_point_id: aimPointId,
    land_point_id: landPointId,
    purpose: lineupForm.purpose,
    difficulty: lineupForm.difficulty,
    summary: lineupForm.summary,
    steps: lineupForm.stepsText.split('\n').map((item) => item.trim()).filter(Boolean),
    media: editingLineup.value?.media || [],
    video_url: lineupForm.video_url,
    status: lineupForm.status,
  };

  if (editingLineupId.value) {
    await api.updateLineup(editingLineupId.value, payload, session.token);
  } else {
    const created = await api.createLineup(payload, session.token);
    editingLineupId.value = created.id;
  }
  await load();
}

async function uploadPointMedia(role: PairRole, file?: File) {
  if (!file) return;
  uploadingMedia.value = role;
  error.value = '';
  try {
    const result = await api.uploadAsset(file, session.token);
    if (role === 'aim') aimDraft.aim_image_url = result.url;
    else landDraft.effect_image_url = result.url;
  } catch (err) {
    error.value = err instanceof Error ? err.message : '上传失败，请检查图片格式和大小';
  } finally {
    uploadingMedia.value = '';
  }
}

onMounted(load);
</script>

<template>
  <div class="page-header">
    <h1>点位管理</h1>
    <p class="muted">只维护瞄点和落点；保存时会用线路记录“瞄点 -> 落点”的道具关联。</p>
  </div>

  <div class="point-admin-layout">
    <aside class="panel point-sidebar">
      <label>
        地图
        <select :value="selectedMapId" class="select" @change="selectMap(Number(($event.target as HTMLSelectElement).value))">
          <option v-for="map in maps" :key="map.id" :value="map.id">{{ map.name }}</option>
        </select>
      </label>

      <div class="role-switch">
        <div class="muted">雷达点击填入</div>
        <button class="ghost-button" :class="{ active: activeRole === 'aim' }" type="button" @click="setActiveRole('aim')">
          <span class="type-dot" :style="{ background: roleColor('aim') }" />
          瞄点
        </button>
        <button class="ghost-button" :class="{ active: activeRole === 'land' }" type="button" @click="setActiveRole('land')">
          <span class="type-dot" :style="{ background: roleColor('land') }" />
          落点
        </button>
      </div>

      <button class="button" type="button" @click="resetForm">新建关联</button>
    </aside>

    <main class="point-workspace">
      <section class="panel radar-panel">
        <div class="inline-row" style="justify-content:space-between">
          <div>
            <strong>{{ currentMap?.name || '地图雷达' }}</strong>
            <p class="muted" style="margin:2px 0 0">点击空白处给当前选中的瞄点/落点取整数坐标；点击已有点会回填对应表单。</p>
          </div>
          <span class="chip">{{ visiblePoints.length }} 个点</span>
        </div>

        <div v-if="currentRadarUrl" class="radar-stage" @click="setDraftCoords">
          <img :src="currentRadarUrl" :alt="currentMap?.name || 'radar'" />
          <svg class="radar-svg" viewBox="0 0 100 100" preserveAspectRatio="none">
            <path :d="previewPath" stroke="#ff7a18" stroke-width="0.8" fill="none" stroke-linecap="round" />
          </svg>
          <button
            v-for="point in visiblePoints"
            :key="point.id"
            type="button"
            class="radar-point"
            :class="{ active: point.id === editingAimPointId || point.id === editingLandPointId }"
            :style="{ left: `${point.x}%`, top: `${point.y}%`, background: pointRoleColor(point) }"
            :title="`${roleLabel(roleForPoint(point))}：${point.name}`"
            @click.stop="selectPoint(point)"
          >
            {{ roleForPoint(point) === 'land' ? refsFor(point.id).land || '' : '' }}
          </button>
          <span
            v-for="point in visiblePoints"
            :key="`label-${point.id}`"
            class="radar-point-label"
            :class="{ active: point.id === editingAimPointId || point.id === editingLandPointId }"
            :style="{ left: `${point.x}%`, top: `${point.y}%` }"
          >
            {{ point.name }}
          </span>
          <span class="radar-marker aim-marker" :style="{ left: `${aimDraft.x}%`, top: `${aimDraft.y}%` }">瞄</span>
          <span class="radar-marker land-marker" :style="{ left: `${landDraft.x}%`, top: `${landDraft.y}%` }">落</span>
        </div>
      </section>

      <form class="panel pair-form" @submit.prevent="submitPair">
        <div class="inline-row" style="justify-content:space-between">
          <h2>{{ editingLineupId ? '编辑道具关联' : '新建道具关联' }}</h2>
          <span class="chip">当前组合已有 {{ pairLineupCount }} 条</span>
        </div>
        <p v-if="error" class="error-text">{{ error }}</p>

        <div class="form-grid">
          <label>
            标题
            <input v-model="lineupForm.title" class="field" placeholder="留空会自动生成" />
          </label>
          <label>
            Slug
            <input v-model="lineupForm.slug" class="field" />
          </label>
          <label>
            阵营
            <select v-model="lineupForm.side" class="select">
              <option value="T">T</option>
              <option value="CT">CT</option>
            </select>
          </label>
          <label>
            道具
            <select v-model="lineupForm.utility_type" class="select">
              <option value="smoke">smoke</option>
              <option value="flash">flash</option>
              <option value="molotov">molotov</option>
              <option value="he">he</option>
              <option value="decoy">decoy</option>
            </select>
          </label>
          <label>
            难度
            <select v-model="lineupForm.difficulty" class="select">
              <option value="easy">easy</option>
              <option value="medium">medium</option>
              <option value="hard">hard</option>
            </select>
          </label>
          <label>
            状态
            <select v-model="lineupForm.status" class="select">
              <option value="draft">draft</option>
              <option value="published">published</option>
              <option value="archived">archived</option>
            </select>
          </label>
          <label class="full">
            用途
            <textarea v-model="lineupForm.purpose" class="textarea" />
          </label>
          <label class="full">
            摘要
            <textarea v-model="lineupForm.summary" class="textarea" />
          </label>
          <label class="full">
            步骤（每行一条）
            <textarea v-model="lineupForm.stepsText" class="textarea" />
          </label>
          <label class="full">
            视频 URL
            <input v-model="lineupForm.video_url" class="field" />
          </label>
        </div>

        <div class="pair-editor">
          <section class="point-subform" :class="{ active: activeRole === 'aim' }">
            <div class="inline-row" style="justify-content:space-between">
              <strong>瞄点</strong>
              <button class="ghost-button" type="button" @click="setActiveRole('aim')">雷达填这里</button>
            </div>
            <div class="form-grid compact-grid">
              <label>
                名称
                <input v-model="aimDraft.name" class="field" required />
              </label>
              <label>
                Key
                <input v-model="aimDraft.key" class="field" required />
              </label>
              <label>
                X
                <input v-model.number="aimDraft.x" type="number" min="0" max="100" step="1" class="field" @change="normalizeDraftCoordinates(aimDraft)" required />
              </label>
              <label>
                Y
                <input v-model.number="aimDraft.y" type="number" min="0" max="100" step="1" class="field" @change="normalizeDraftCoordinates(aimDraft)" required />
              </label>
              <label>
                阵营
                <select v-model="aimDraft.side" class="select">
                  <option value="T">T</option>
                  <option value="CT">CT</option>
                  <option value="BOTH">BOTH</option>
                </select>
              </label>
              <label class="full">
                标签
                <input v-model="aimDraft.tagsText" class="field" placeholder="逗号分隔" />
              </label>
              <label class="full">
                说明
                <textarea v-model="aimDraft.description" class="textarea" />
              </label>
              <label class="full">
                瞄点图 URL
                <div class="media-url-row">
                  <input v-model="aimDraft.aim_image_url" class="field" />
                  <img v-if="aimDraft.aim_image_url" :src="resolveAssetUrl(aimDraft.aim_image_url)" class="media-preview" />
                </div>
                <div class="media-actions">
                  <label class="ghost-button upload-button">
                    {{ uploadingMedia === 'aim' ? '上传中...' : '上传瞄点图' }}
                    <input type="file" accept="image/*" hidden :disabled="uploadingMedia !== ''" @change="(event) => uploadPointMedia('aim', (event.target as HTMLInputElement).files?.[0])" />
                  </label>
                  <details class="asset-library">
                    <summary class="ghost-button">素材库回填</summary>
                    <AssetPicker compact @select="(url) => { aimDraft.aim_image_url = url; }" />
                  </details>
                </div>
              </label>
            </div>
          </section>

          <section class="point-subform" :class="{ active: activeRole === 'land' }">
            <div class="inline-row" style="justify-content:space-between">
              <strong>落点</strong>
              <button class="ghost-button" type="button" @click="setActiveRole('land')">雷达填这里</button>
            </div>
            <div class="form-grid compact-grid">
              <label>
                名称
                <input v-model="landDraft.name" class="field" required />
              </label>
              <label>
                Key
                <input v-model="landDraft.key" class="field" required />
              </label>
              <label>
                X
                <input v-model.number="landDraft.x" type="number" min="0" max="100" step="1" class="field" @change="normalizeDraftCoordinates(landDraft)" required />
              </label>
              <label>
                Y
                <input v-model.number="landDraft.y" type="number" min="0" max="100" step="1" class="field" @change="normalizeDraftCoordinates(landDraft)" required />
              </label>
              <label>
                阵营
                <select v-model="landDraft.side" class="select">
                  <option value="T">T</option>
                  <option value="CT">CT</option>
                  <option value="BOTH">BOTH</option>
                </select>
              </label>
              <label class="full">
                标签
                <input v-model="landDraft.tagsText" class="field" placeholder="逗号分隔" />
              </label>
              <label class="full">
                说明
                <textarea v-model="landDraft.description" class="textarea" />
              </label>
              <label class="full">
                落点/效果图 URL
                <div class="media-url-row">
                  <input v-model="landDraft.effect_image_url" class="field" />
                  <img v-if="landDraft.effect_image_url" :src="resolveAssetUrl(landDraft.effect_image_url)" class="media-preview" />
                </div>
                <div class="media-actions">
                  <label class="ghost-button upload-button">
                    {{ uploadingMedia === 'land' ? '上传中...' : '上传落点图' }}
                    <input type="file" accept="image/*" hidden :disabled="uploadingMedia !== ''" @change="(event) => uploadPointMedia('land', (event.target as HTMLInputElement).files?.[0])" />
                  </label>
                  <details class="asset-library">
                    <summary class="ghost-button">素材库回填</summary>
                    <AssetPicker compact @select="(url) => { landDraft.effect_image_url = url; }" />
                  </details>
                </div>
              </label>
            </div>
          </section>
        </div>

        <div class="toolbar">
          <button class="button">{{ editingLineupId ? '保存关联' : '创建关联' }}</button>
          <button class="ghost-button" type="button" @click="resetForm">清空</button>
        </div>

        <div v-if="pairLineups.length" class="pair-matches">
          <strong>当前组合线路</strong>
          <button v-for="lineup in pairLineups" :key="lineup.id" class="ghost-button" type="button" @click="editLineup(lineup)">
            {{ lineup.title }} / {{ lineup.utility_type }}
          </button>
        </div>
      </form>

      <section class="panel point-list-panel">
        <div class="inline-row" style="justify-content:space-between">
          <h2>点位和线路</h2>
          <span class="muted">{{ visiblePoints.length }} 个点 / {{ mapLineups.length }} 条线路</span>
        </div>
        <div class="point-type-groups">
          <article class="point-type-group">
            <div class="point-type-heading">
              <span class="type-dot" :style="{ background: roleColor('aim') }" />
              <strong>瞄点</strong>
              <span class="muted">{{ aimPoints.length }} 个</span>
            </div>
            <div class="point-list">
              <button v-for="point in aimPoints" :key="point.id" type="button" class="point-list-item" @click="selectPoint(point)">
                <span>
                  <strong>{{ point.name }}</strong>
                  <small>{{ point.key }} · {{ Math.round(point.x) }} / {{ Math.round(point.y) }}</small>
                </span>
                <span class="chip">关联 {{ refsFor(point.id).aim }}</span>
              </button>
            </div>
          </article>

          <article class="point-type-group">
            <div class="point-type-heading">
              <span class="type-dot" :style="{ background: roleColor('land') }" />
              <strong>落点</strong>
              <span class="muted">{{ landPoints.length }} 个</span>
            </div>
            <div class="point-list">
              <button v-for="point in landPoints" :key="point.id" type="button" class="point-list-item" @click="selectPoint(point)">
                <span>
                  <strong>{{ point.name }}</strong>
                  <small>{{ point.key }} · {{ Math.round(point.x) }} / {{ Math.round(point.y) }}</small>
                </span>
                <span class="chip strong">落点 {{ refsFor(point.id).land }}</span>
              </button>
            </div>
          </article>
        </div>

        <div class="lineup-list">
          <h3>本地图线路</h3>
          <button v-for="lineup in mapLineups" :key="lineup.id" type="button" class="lineup-list-item" @click="editLineup(lineup)">
            <span>
              <strong>{{ lineup.title }}</strong>
              <small>{{ pointName(lineup.start_point_id) }} -> {{ pointName(lineup.land_point_id) }}</small>
            </span>
            <span class="chip">{{ lineup.utility_type }}</span>
          </button>
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
.role-switch {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.role-switch .ghost-button {
  justify-content: flex-start;
}
.role-switch .ghost-button.active,
.point-subform.active {
  border-color: rgba(255,122,24,0.45);
  background: rgba(255,122,24,0.1);
}
.type-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 999px;
}
.point-workspace {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 16px;
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
.radar-svg {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}
.radar-point,
.radar-marker {
  position: absolute;
  transform: translate(-50%, -50%);
  border: 2px solid #fff;
  border-radius: 50%;
  color: #07111f;
  font-weight: 900;
  line-height: 1;
}
.radar-point {
  width: 18px;
  height: 18px;
  cursor: pointer;
  font-size: 10px;
  box-shadow: 0 0 0 6px rgba(255,122,24,0.18);
}
.radar-point:hover,
.radar-point.active {
  box-shadow: 0 0 0 5px rgba(255,122,24,0.32), 0 0 18px rgba(255,122,24,0.5);
  transform: translate(-50%, -50%) scale(1.14);
}
.radar-marker {
  min-width: 24px;
  height: 24px;
  padding: 0 5px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  font-size: 11px;
  pointer-events: none;
}
.aim-marker {
  background: #65d6ce;
}
.land-marker {
  background: #f5d76e;
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
.pair-form h2,
.point-list-panel h2 {
  margin: 0;
}
.error-text {
  margin: 10px 0;
  color: #ff9f96;
}
.pair-editor {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
  margin-top: 14px;
}
.point-subform {
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 8px;
  background: rgba(255,255,255,0.03);
  padding: 12px;
}
.compact-grid {
  margin-top: 10px;
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
.media-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 8px;
}
.upload-button {
  display: inline-flex;
  width: fit-content;
  cursor: pointer;
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
.pair-matches {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
}
.point-type-groups,
.lineup-list {
  display: grid;
  gap: 12px;
  margin-top: 12px;
}
.point-type-heading {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}
.point-list {
  display: grid;
  gap: 8px;
}
.point-list-item,
.lineup-list-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  width: 100%;
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 8px;
  background: rgba(255,255,255,0.03);
  color: inherit;
  text-align: left;
  padding: 10px;
  cursor: pointer;
}
.point-list-item:hover,
.lineup-list-item:hover {
  border-color: rgba(255,122,24,0.45);
  background: rgba(255,122,24,0.08);
}
.point-list-item span,
.lineup-list-item span {
  min-width: 0;
}
.point-list-item small,
.lineup-list-item small {
  display: block;
  margin-top: 2px;
  color: rgba(255,255,255,0.58);
}
.lineup-list h3 {
  margin: 0;
}
@media (max-width: 900px) {
  .point-admin-layout,
  .pair-editor {
    grid-template-columns: 1fr;
  }
  .point-sidebar {
    position: static;
  }
}
</style>

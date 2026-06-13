<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';

import { api, resolveAssetUrl } from '../api';
import AssetPicker from '../components/AssetPicker.vue';
import { useSessionStore } from '../stores/session';
import type { AdminLineup, AdminMap, AdminPoint } from '../types';

type PointRole = 'stand' | 'aim' | 'land';

type PointDraft = {
  name: string;
  key: string;
  x: number;
  y: number;
  side: string;
  tagsText: string;
  description: string;
  aim_image_url: string;
  aim_image_description: string;
  effect_image_url: string;
  effect_image_description: string;
  video_url: string;
};

const session = useSessionStore();
const maps = ref<AdminMap[]>([]);
const points = ref<AdminPoint[]>([]);
const lineups = ref<AdminLineup[]>([]);
const selectedMapId = ref(1);
const activeRole = ref<PointRole>('stand');
const editingLineupId = ref<number | null>(null);
const editingStandPointId = ref<number | null>(null);
const editingAimPointId = ref<number | null>(null);
const editingLandPointId = ref<number | null>(null);
const error = ref('');
const success = ref('');
const uploadingMedia = ref<PointRole | ''>('');

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
  status: 'published',
});

function createDraft(x: number, y: number): PointDraft {
  return {
    name: '',
    key: '',
    x,
    y,
    side: 'BOTH',
    tagsText: '',
    description: '',
    aim_image_url: '',
    aim_image_description: '',
    effect_image_url: '',
    effect_image_description: '',
    video_url: '',
  };
}

const standDraft = reactive<PointDraft>(createDraft(35, 55));
const aimDraft = reactive<PointDraft>(createDraft(50, 45));
const landDraft = reactive<PointDraft>(createDraft(65, 45));

const POINT_ROLE_META: Record<PointRole, { label: string; short: string; color: string; pointType: 'staging' | 'aim' | 'site' }> = {
  stand: { label: '站位瞄点', short: '站', color: '#65d6ce', pointType: 'staging' },
  aim: { label: '道具瞄点', short: '瞄', color: '#ff7a18', pointType: 'aim' },
  land: { label: '落点', short: '落', color: '#f5d76e', pointType: 'site' },
};
const pointRoles: PointRole[] = ['stand', 'aim', 'land'];
const pointEditorItems = [
  { role: 'stand' as const, draft: standDraft },
  { role: 'aim' as const, draft: aimDraft },
  { role: 'land' as const, draft: landDraft },
];

const currentMap = computed(() => maps.value.find((map) => map.id === selectedMapId.value) || null);
const currentRadarUrl = computed(() =>
  currentMap.value ? resolveAssetUrl(`/static/assets/maps/radars/${currentMap.value.slug}-radar.png`) : '',
);
const mapPoints = computed(() => points.value.filter((point) => point.map_id === selectedMapId.value));
const standPoints = computed(() => mapPoints.value.filter((point) => point.point_type === 'staging'));
const aimPoints = computed(() => mapPoints.value.filter((point) => point.point_type === 'aim'));
const landPoints = computed(() => mapPoints.value.filter((point) => point.point_type === 'site'));
const visiblePoints = computed(() => [...standPoints.value, ...aimPoints.value, ...landPoints.value]);
const activeDraft = computed(() => draftForRole(activeRole.value));
const editingLineup = computed(() =>
  editingLineupId.value ? lineups.value.find((lineup) => lineup.id === editingLineupId.value) || null : null,
);
const mapLineups = computed(() => lineups.value.filter((lineup) => lineup.map_id === selectedMapId.value));
const lineupsByLanding = computed(() =>
  landPoints.value.map((point) => ({
    point,
    lineups: mapLineups.value.filter((lineup) => lineup.land_point_id === point.id),
  })).sort((a, b) => b.lineups.length - a.lineups.length || a.point.name.localeCompare(b.point.name)),
);
const selectedComboLineups = computed(() =>
  mapLineups.value.filter((lineup) =>
    lineup.start_point_id === editingStandPointId.value &&
    lineup.aim_point_id === editingAimPointId.value &&
    lineup.land_point_id === editingLandPointId.value,
  ),
);
const visibilityState = computed(() => {
  if (!editingStandPointId.value || !editingAimPointId.value || !editingLandPointId.value) {
    return { visible: false, label: '保存后可见', reason: '三个点位还没有全部保存' };
  }
  if (lineupForm.status !== 'published') {
    return { visible: false, label: '前台不可见', reason: '状态不是 published' };
  }
  return { visible: true, label: '前台可见', reason: '已有关联落点且状态为 published' };
});
const previewPath = computed(() =>
  `M${standDraft.x} ${standDraft.y} L${aimDraft.x} ${aimDraft.y} L${landDraft.x} ${landDraft.y}`,
);

function draftForRole(role: PointRole) {
  if (role === 'stand') return standDraft;
  if (role === 'aim') return aimDraft;
  return landDraft;
}

function setEditingIdForRole(role: PointRole, id: number | null) {
  if (role === 'stand') editingStandPointId.value = id;
  else if (role === 'aim') editingAimPointId.value = id;
  else editingLandPointId.value = id;
}

function roleForPoint(point: AdminPoint): PointRole {
  if (point.point_type === 'site') return 'land';
  if (point.point_type === 'aim') return 'aim';
  return 'stand';
}

function roleColor(role: PointRole) {
  return POINT_ROLE_META[role].color;
}

function roleLabel(role: PointRole) {
  return POINT_ROLE_META[role].label;
}

function pointRoleColor(point: AdminPoint) {
  return roleColor(roleForPoint(point));
}

function pointName(pointId: number) {
  return points.value.find((point) => point.id === pointId)?.name || `#${pointId}`;
}

function refsFor(pointId: number) {
  const asStand = lineups.value.filter((lineup) => lineup.start_point_id === pointId).length;
  const asAim = lineups.value.filter((lineup) => lineup.aim_point_id === pointId).length;
  const asLand = lineups.value.filter((lineup) => lineup.land_point_id === pointId).length;
  return { asStand, asAim, asLand, total: asStand + asAim + asLand };
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
  setEditingIdForRole(role, point.id);
  Object.assign(draftForRole(role), {
    name: point.name,
    key: point.key,
    x: clampCoordinate(point.x),
    y: clampCoordinate(point.y),
    side: point.side,
    tagsText: (point.tags || []).join(', '),
    description: point.description || '',
    aim_image_url: point.aim_image_url || '',
    aim_image_description: point.aim_image_description || '',
    effect_image_url: point.effect_image_url || '',
    effect_image_description: point.effect_image_description || '',
    video_url: point.video_url || '',
  });
}

function selectPoint(point: AdminPoint) {
  applyPointToDraft(point);
}

function setActiveRole(role: PointRole) {
  activeRole.value = role;
}

function setDraftCoords(event: MouseEvent) {
  Object.assign(activeDraft.value, coordsFromRadar(event));
}

function resetDraft(draft: PointDraft, role: PointRole) {
  Object.assign(draft, createDraft(role === 'stand' ? 35 : role === 'aim' ? 50 : 65, role === 'land' ? 45 : 55));
}

function resetForm() {
  editingLineupId.value = null;
  editingStandPointId.value = null;
  editingAimPointId.value = null;
  editingLandPointId.value = null;
  error.value = '';
  success.value = '';
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
    status: 'published',
  });
  resetDraft(standDraft, 'stand');
  resetDraft(aimDraft, 'aim');
  resetDraft(landDraft, 'land');
  activeRole.value = 'stand';
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
  const standPoint = points.value.find((point) => point.id === lineup.start_point_id);
  const aimPoint = points.value.find((point) => point.id === lineup.aim_point_id);
  const landPoint = points.value.find((point) => point.id === lineup.land_point_id);
  if (standPoint) applyPointToDraft(standPoint, 'stand');
  if (aimPoint) applyPointToDraft(aimPoint, 'aim');
  if (landPoint) applyPointToDraft(landPoint, 'land');
  activeRole.value = 'stand';
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function validatePointDraft(role: PointRole, draft: PointDraft, editingId: number | null) {
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

function buildPointPayload(role: PointRole, draft: PointDraft, original?: AdminPoint) {
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
    aim_image_url: role === 'stand' || role === 'aim' ? draft.aim_image_url : original?.aim_image_url || '',
    aim_image_description: role === 'stand' || role === 'aim' ? draft.aim_image_description : original?.aim_image_description || '',
    effect_image_url: role === 'land' ? draft.effect_image_url : original?.effect_image_url || '',
    effect_image_description: role === 'land' ? draft.effect_image_description : original?.effect_image_description || '',
    video_url: draft.video_url,
  };
}

async function savePoint(role: PointRole, draft: PointDraft, editingId: number | null) {
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
  return `${mapName} ${standDraft.name.trim()} -> ${landDraft.name.trim()} ${lineupForm.utility_type}`;
}

async function submitPair() {
  error.value = '';
  success.value = '';
  const standError = validatePointDraft('stand', standDraft, editingStandPointId.value);
  const aimError = validatePointDraft('aim', aimDraft, editingAimPointId.value);
  const landError = validatePointDraft('land', landDraft, editingLandPointId.value);
  if (standError || aimError || landError) {
    error.value = standError || aimError || landError;
    return;
  }

  try {
    const standPointId = await savePoint('stand', standDraft, editingStandPointId.value);
    const aimPointId = await savePoint('aim', aimDraft, editingAimPointId.value);
    const landPointId = await savePoint('land', landDraft, editingLandPointId.value);
    editingStandPointId.value = standPointId;
    editingAimPointId.value = aimPointId;
    editingLandPointId.value = landPointId;

    const payload = {
      map_id: selectedMapId.value,
      title: lineupForm.title.trim() || defaultLineupTitle(),
      slug: lineupForm.slug.trim(),
      side: lineupForm.side,
      utility_type: lineupForm.utility_type,
      start_point_id: standPointId,
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
    success.value = '已保存，道具会按落点在前台地图页聚合显示';
  } catch (err) {
    error.value = err instanceof Error ? err.message : '保存失败，请检查必填字段';
  }
}

async function uploadPointMedia(role: PointRole, file?: File) {
  if (!file) return;
  uploadingMedia.value = role;
  error.value = '';
  try {
    const result = await api.uploadAsset(file, session.token);
    if (role === 'land') landDraft.effect_image_url = result.url;
    else draftForRole(role).aim_image_url = result.url;
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
    <h1>道具点位管理</h1>
    <p class="muted">一次录入站位瞄点、道具瞄点、落点和线路。前台地图页会按落点展示多个道具。</p>
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
        <button
          v-for="role in pointRoles"
          :key="role"
          class="ghost-button"
          :class="{ active: activeRole === role }"
          type="button"
          @click="setActiveRole(role)"
        >
          <span class="type-dot" :style="{ background: roleColor(role) }" />
          {{ roleLabel(role) }}
        </button>
      </div>

      <button class="button" type="button" @click="resetForm">新建道具</button>
    </aside>

    <main class="point-workspace">
      <section class="panel radar-panel">
        <div class="inline-row radar-heading">
          <div>
            <strong>{{ currentMap?.name || '地图雷达' }}</strong>
            <p class="muted">点击空白处会把整数坐标填到当前选中的点位；点击已有点位会回填编辑。</p>
          </div>
          <span class="chip">{{ visiblePoints.length }} 个点</span>
        </div>

        <div v-if="currentRadarUrl" class="radar-stage" @click="setDraftCoords">
          <img :src="currentRadarUrl" :alt="currentMap?.name || 'radar'" />
          <svg class="radar-svg" viewBox="0 0 100 100" preserveAspectRatio="none">
            <path :d="previewPath" stroke="#ff7a18" stroke-width="0.8" fill="none" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
          <button
            v-for="point in visiblePoints"
            :key="point.id"
            type="button"
            class="radar-point"
            :class="{ active: [editingStandPointId, editingAimPointId, editingLandPointId].includes(point.id) }"
            :style="{ left: `${point.x}%`, top: `${point.y}%`, background: pointRoleColor(point) }"
            :title="`${roleLabel(roleForPoint(point))}: ${point.name}`"
            @click.stop="selectPoint(point)"
          >
            {{ roleForPoint(point) === 'land' ? refsFor(point.id).asLand || '' : POINT_ROLE_META[roleForPoint(point)].short }}
          </button>
          <span
            v-for="point in visiblePoints"
            :key="`label-${point.id}`"
            class="radar-point-label"
            :style="{ left: `${point.x}%`, top: `${point.y}%` }"
          >
            {{ point.name }}
          </span>
          <span class="radar-marker stand-marker" :style="{ left: `${standDraft.x}%`, top: `${standDraft.y}%` }">站</span>
          <span class="radar-marker aim-marker" :style="{ left: `${aimDraft.x}%`, top: `${aimDraft.y}%` }">瞄</span>
          <span class="radar-marker land-marker" :style="{ left: `${landDraft.x}%`, top: `${landDraft.y}%` }">落</span>
        </div>
      </section>

      <form class="panel pair-form" @submit.prevent="submitPair">
        <div class="inline-row form-heading">
          <div>
            <h2>{{ editingLineupId ? '编辑道具' : '新建道具' }}</h2>
            <p class="muted">保存时会先保存三个点位，再创建或更新底层线路。</p>
          </div>
          <span class="visibility-chip" :class="{ visible: visibilityState.visible }">
            {{ visibilityState.label }}：{{ visibilityState.reason }}
          </span>
        </div>
        <p v-if="error" class="error-text">{{ error }}</p>
        <p v-if="success" class="success-text">{{ success }}</p>

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
              <option value="published">published（前台可见）</option>
              <option value="draft">draft（草稿）</option>
              <option value="archived">archived（归档）</option>
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
            <input v-model="lineupForm.video_url" class="field" placeholder="B 站、YouTube 或其他视频链接" />
          </label>
        </div>

        <div class="point-editor">
          <section
            v-for="item in pointEditorItems"
            :key="item.role"
            class="point-subform"
            :class="{ active: activeRole === item.role }"
          >
            <div class="inline-row subform-heading">
              <strong>{{ roleLabel(item.role) }}</strong>
              <button class="ghost-button" type="button" @click="setActiveRole(item.role)">雷达填这里</button>
            </div>
            <div class="form-grid compact-grid">
              <label>
                名称
                <input v-model="item.draft.name" class="field" required />
              </label>
              <label>
                Key
                <input v-model="item.draft.key" class="field" required />
              </label>
              <label>
                X
                <input v-model.number="item.draft.x" type="number" min="0" max="100" step="1" class="field" @change="normalizeDraftCoordinates(item.draft)" required />
              </label>
              <label>
                Y
                <input v-model.number="item.draft.y" type="number" min="0" max="100" step="1" class="field" @change="normalizeDraftCoordinates(item.draft)" required />
              </label>
              <label>
                阵营
                <select v-model="item.draft.side" class="select">
                  <option value="T">T</option>
                  <option value="CT">CT</option>
                  <option value="BOTH">BOTH</option>
                </select>
              </label>
              <label class="full">
                标签
                <input v-model="item.draft.tagsText" class="field" placeholder="逗号分隔" />
              </label>
              <label class="full">
                点位说明
                <textarea v-model="item.draft.description" class="textarea" />
              </label>

              <template v-if="item.role !== 'land'">
                <label class="full">
                  {{ roleLabel(item.role) }}图片 URL
                  <div class="media-url-row">
                    <input v-model="item.draft.aim_image_url" class="field" />
                    <img v-if="item.draft.aim_image_url" :src="resolveAssetUrl(item.draft.aim_image_url)" class="media-preview" />
                  </div>
                </label>
                <label class="full">
                  图片描述
                  <input v-model="item.draft.aim_image_description" class="field" placeholder="例如：准星对准窗框右下角" />
                </label>
              </template>

              <template v-else>
                <label class="full">
                  落点效果图 URL
                  <div class="media-url-row">
                    <input v-model="landDraft.effect_image_url" class="field" />
                    <img v-if="landDraft.effect_image_url" :src="resolveAssetUrl(landDraft.effect_image_url)" class="media-preview" />
                  </div>
                </label>
                <label class="full">
                  图片描述
                  <input v-model="landDraft.effect_image_description" class="field" placeholder="例如：烟雾完全封住窗口视野" />
                </label>
              </template>

              <div class="full media-actions">
                <label class="ghost-button upload-button">
                  {{ uploadingMedia === item.role ? '上传中...' : `上传${item.role === 'land' ? '效果图' : '瞄点图'}` }}
                  <input type="file" accept="image/*" hidden :disabled="uploadingMedia !== ''" @change="(event) => uploadPointMedia(item.role, (event.target as HTMLInputElement).files?.[0])" />
                </label>
                <details class="asset-library">
                  <summary class="ghost-button">素材库回填</summary>
                  <AssetPicker
                    compact
                    @select="(url) => {
                      if (item.role === 'land') landDraft.effect_image_url = url;
                      else item.draft.aim_image_url = url;
                    }"
                  />
                </details>
              </div>
            </div>
          </section>
        </div>

        <div class="toolbar">
          <button class="button">{{ editingLineupId ? '保存道具' : '创建道具' }}</button>
          <button class="ghost-button" type="button" @click="resetForm">清空</button>
        </div>

        <div v-if="selectedComboLineups.length" class="pair-matches">
          <strong>当前三点组合已有线路</strong>
          <button v-for="lineup in selectedComboLineups" :key="lineup.id" class="ghost-button" type="button" @click="editLineup(lineup)">
            {{ lineup.title }} / {{ lineup.utility_type }} / {{ lineup.status }}
          </button>
        </div>
      </form>

      <section class="panel point-list-panel">
        <div class="inline-row list-heading">
          <h2>按落点管理道具</h2>
          <span class="muted">{{ landPoints.length }} 个落点 / {{ mapLineups.length }} 条道具</span>
        </div>
        <div class="landing-groups">
          <article v-for="group in lineupsByLanding" :key="group.point.id" class="landing-group-card">
            <div class="landing-group-heading">
              <button type="button" class="landing-title" @click="selectPoint(group.point)">
                <strong>{{ group.point.name }}</strong>
                <span>{{ group.point.key }} · {{ Math.round(group.point.x) }} / {{ Math.round(group.point.y) }}</span>
              </button>
              <span class="chip strong">{{ group.lineups.length }} 个道具</span>
            </div>
            <div v-if="group.lineups.length" class="utility-list">
              <button v-for="lineup in group.lineups" :key="lineup.id" type="button" class="utility-list-item" @click="editLineup(lineup)">
                <span>
                  <strong>{{ lineup.title }}</strong>
                  <small>{{ pointName(lineup.start_point_id) }} -> {{ pointName(lineup.aim_point_id) }} -> {{ group.point.name }}</small>
                </span>
                <span class="chip" :class="{ strong: lineup.status === 'published' }">
                  {{ lineup.utility_type }} / {{ lineup.status === 'published' ? '前台可见' : '不显示' }}
                </span>
              </button>
            </div>
            <p v-else class="muted empty-landing">这个落点还没有道具，保存一条 published 道具后前台才会显示。</p>
          </article>
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
  gap: 16px;
}
.radar-heading,
.form-heading,
.subform-heading,
.list-heading {
  justify-content: space-between;
}
.radar-stage {
  position: relative;
  overflow: hidden;
  margin-top: 12px;
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 8px;
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
  border-radius: 999px;
  color: #07111f;
  font-weight: 900;
  line-height: 1;
}
.radar-point {
  z-index: 3;
  min-width: 20px;
  height: 20px;
  padding: 0 4px;
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
  z-index: 4;
  min-width: 24px;
  height: 24px;
  padding: 0 5px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  pointer-events: none;
}
.stand-marker {
  background: #65d6ce;
}
.aim-marker {
  background: #ff7a18;
}
.land-marker {
  background: #f5d76e;
}
.radar-point-label {
  position: absolute;
  z-index: 2;
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
.pair-form h2,
.point-list-panel h2 {
  margin: 0;
}
.pair-form p {
  margin: 2px 0 0;
}
.visibility-chip {
  display: inline-flex;
  max-width: 380px;
  border: 1px solid rgba(255,255,255,0.12);
  border-radius: 999px;
  background: rgba(255,255,255,0.04);
  color: rgba(255,255,255,0.76);
  padding: 6px 10px;
  font-size: 12px;
  line-height: 1.2;
}
.visibility-chip.visible {
  border-color: rgba(101,214,206,0.45);
  background: rgba(101,214,206,0.12);
  color: #bff7f2;
}
.error-text {
  margin: 10px 0;
  color: #ff9f96;
}
.success-text {
  margin: 10px 0;
  color: #8de8be;
}
.point-editor {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
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
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 6px;
}
.media-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
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
.landing-groups {
  display: grid;
  gap: 12px;
  margin-top: 12px;
}
.landing-group-card {
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 8px;
  background: rgba(255,255,255,0.03);
  padding: 12px;
}
.landing-group-heading,
.utility-list-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.landing-title,
.utility-list-item {
  border: 0;
  background: transparent;
  color: inherit;
  text-align: left;
  cursor: pointer;
}
.landing-title {
  display: grid;
  gap: 3px;
  padding: 0;
}
.landing-title span,
.utility-list-item small {
  color: rgba(255,255,255,0.58);
  font-size: 12px;
}
.utility-list {
  display: grid;
  gap: 8px;
  margin-top: 10px;
}
.utility-list-item {
  width: 100%;
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 8px;
  background: rgba(255,255,255,0.03);
  padding: 10px;
}
.utility-list-item:hover {
  border-color: rgba(255,122,24,0.45);
  background: rgba(255,122,24,0.08);
}
.utility-list-item span {
  min-width: 0;
}
.utility-list-item small {
  display: block;
  margin-top: 2px;
}
.empty-landing {
  margin: 10px 0 0;
}
@media (max-width: 1100px) {
  .point-editor {
    grid-template-columns: 1fr;
  }
}
@media (max-width: 900px) {
  .point-admin-layout {
    grid-template-columns: 1fr;
  }
  .point-sidebar {
    position: static;
  }
}
</style>

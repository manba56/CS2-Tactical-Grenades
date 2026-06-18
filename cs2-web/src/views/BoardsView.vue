<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';

import { api, resolveAssetUrl } from '../api';
import { useHead } from '../composables/useHead';
import { useSessionStore } from '../stores/session';
import type { BoardMarker, BoardMarkerRole, MapSummary, PersonalBoard, RouteData } from '../types';

const router = useRouter();
const session = useSessionStore();

const maps = ref<MapSummary[]>([]);
const boards = ref<PersonalBoard[]>([]);
const activeBoardId = ref<number | null>(null);
const title = ref('Mirage A execute');
const mapId = ref<number | null>(null);
const side = ref<'T' | 'CT'>('T');
const planType = ref<PersonalBoard['plan_type']>('exec');
const summary = ref('Window smoke, connector smoke, then split A from ramp and palace.');
const markerRole = ref<BoardMarkerRole>('player');
const markerLabel = ref('P1');
const markers = ref<BoardMarker[]>([]);
const saveMessage = ref('');
const error = ref('');
const saving = ref(false);
const radarFallback = ref(false);

const markerRoles: Array<{ value: BoardMarkerRole; label: string }> = [
  { value: 'player', label: 'Player' },
  { value: 'smoke', label: 'Smoke' },
  { value: 'flash', label: 'Flash' },
  { value: 'molotov', label: 'Molotov' },
  { value: 'he', label: 'HE' },
  { value: 'note', label: 'Note' },
];

const planTypes: Array<{ value: PersonalBoard['plan_type']; label: string }> = [
  { value: 'exec', label: 'Execute' },
  { value: 'default', label: 'Default' },
  { value: 'retake', label: 'Retake' },
  { value: 'anti-rush', label: 'Anti-rush' },
  { value: 'practice', label: 'Practice' },
];

const activeMap = computed(() => maps.value.find((map) => map.id === mapId.value) || maps.value[0] || null);
const radarUrl = computed(() => {
  const map = activeMap.value;
  if (!map) return '';
  if (radarFallback.value) return resolveAssetUrl(map.layout_url || map.cover_url);
  return resolveAssetUrl(`/static/assets/maps/radars/${map.slug}-radar.png`);
});
const payload = computed(() => ({
  title: title.value.trim(),
  map_id: mapId.value || activeMap.value?.id || 0,
  side: side.value,
  plan_type: planType.value,
  summary: summary.value.trim(),
  markers: markers.value,
  routes: [] as RouteData[],
}));

function resetForm() {
  activeBoardId.value = null;
  title.value = 'Mirage A execute';
  side.value = 'T';
  planType.value = 'exec';
  summary.value = 'Window smoke, connector smoke, then split A from ramp and palace.';
  markers.value = [
    { x: 18, y: 82, label: 'P1', role: 'player', side: 'T' },
    { x: 47, y: 37, label: 'Window', role: 'smoke', side: 'T' },
    { x: 58, y: 49, label: 'Connector', role: 'smoke', side: 'T' },
    { x: 78, y: 41, label: 'A hit', role: 'note', side: 'BOTH' },
  ];
  if (maps.value.length) {
    mapId.value = maps.value.find((map) => map.slug === 'mirage')?.id || maps.value[0].id;
  }
}

function loadBoard(board: PersonalBoard) {
  activeBoardId.value = board.id;
  title.value = board.title;
  mapId.value = board.map_id;
  side.value = board.side;
  planType.value = board.plan_type;
  summary.value = board.summary;
  markers.value = board.markers.map((marker) => ({ ...marker }));
  radarFallback.value = false;
  saveMessage.value = '';
}

function markerColor(marker: BoardMarker) {
  if (marker.role === 'player') return marker.side === 'CT' ? '#65d6ce' : '#ff7a18';
  if (marker.role === 'smoke') return '#aeb8c6';
  if (marker.role === 'flash') return '#ffd54f';
  if (marker.role === 'molotov') return '#ef6c00';
  if (marker.role === 'he') return '#81d4fa';
  return '#f5d76e';
}

function addMarker(event: MouseEvent) {
  const target = event.currentTarget as HTMLElement;
  const rect = target.getBoundingClientRect();
  const x = Number((((event.clientX - rect.left) / rect.width) * 100).toFixed(1));
  const y = Number((((event.clientY - rect.top) / rect.height) * 100).toFixed(1));
  markers.value.push({
    x,
    y,
    label: markerLabel.value.trim() || markerRole.value,
    role: markerRole.value,
    side: markerRole.value === 'player' ? side.value : 'BOTH',
  });
  markerLabel.value = markerRole.value === 'player'
    ? `P${Math.min(markers.value.filter((item) => item.role === 'player').length + 1, 5)}`
    : markerRole.value;
}

function removeMarker(index: number) {
  markers.value = markers.value.filter((_, itemIndex) => itemIndex !== index);
}

async function loadData() {
  error.value = '';
  try {
    const mapList = await api.getMaps();
    maps.value = mapList;
    if (!mapId.value) resetForm();
    boards.value = await api.getPersonalBoards(session.token);
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to load boards.';
  }
}

async function saveBoard() {
  if (!payload.value.title || !payload.value.map_id) {
    error.value = 'Title and map are required.';
    return;
  }
  saving.value = true;
  error.value = '';
  saveMessage.value = '';
  try {
    const wasUpdate = Boolean(activeBoardId.value);
    const saved = activeBoardId.value
      ? await api.updatePersonalBoard(activeBoardId.value, payload.value, session.token)
      : await api.createPersonalBoard(payload.value, session.token);
    activeBoardId.value = saved.id;
    const others = boards.value.filter((board) => board.id !== saved.id);
    boards.value = [saved, ...others];
    saveMessage.value = wasUpdate ? 'Board saved.' : 'Board created.';
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Save failed.';
  } finally {
    saving.value = false;
  }
}

async function deleteBoard(board: PersonalBoard) {
  error.value = '';
  try {
    await api.deletePersonalBoard(board.id, session.token);
    boards.value = boards.value.filter((item) => item.id !== board.id);
    if (activeBoardId.value === board.id) resetForm();
    saveMessage.value = 'Board deleted.';
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Delete failed.';
  }
}

onMounted(async () => {
  useHead('My Tactic Board', 'Create and test personal CS2 tactic boards.');
  if (!session.token) {
    router.push('/login?redirect=/boards');
    return;
  }
  await loadData();
});
</script>

<template>
  <div class="boards-page">
    <section class="section-heading">
      <div>
        <div class="kicker">Personal tactic board</div>
        <h1>我的 CS2 战术板</h1>
      </div>
      <button class="secondary-button" type="button" @click="resetForm">New board</button>
    </section>

    <section v-if="error" class="empty-card danger">{{ error }}</section>

    <section class="boards-layout">
      <aside class="glass-panel board-list-panel">
        <div class="section-heading compact-heading">
          <h2>Saved boards</h2>
          <span class="muted">{{ boards.length }} items</span>
        </div>
        <button
          v-for="board in boards"
          :key="board.id"
          class="board-list-item"
          :class="{ active: activeBoardId === board.id }"
          type="button"
          @click="loadBoard(board)"
        >
          <strong>{{ board.title }}</strong>
          <span>{{ board.map.name }} / {{ board.side }} / {{ board.markers.length }} markers</span>
        </button>
        <p v-if="!boards.length" class="muted small-empty">No boards yet. Create the first one on the radar.</p>
      </aside>

      <main class="board-main">
        <section class="glass-panel board-editor-panel">
          <div class="board-form-grid">
            <label>
              Title
              <input v-model="title" class="field" data-testid="board-title" />
            </label>
            <label>
              Map
              <select v-model.number="mapId" class="field-select" data-testid="board-map" @change="radarFallback = false">
                <option v-for="map in maps" :key="map.id" :value="map.id">{{ map.name }}</option>
              </select>
            </label>
            <label>
              Side
              <select v-model="side" class="field-select" data-testid="board-side">
                <option value="T">T</option>
                <option value="CT">CT</option>
              </select>
            </label>
            <label>
              Type
              <select v-model="planType" class="field-select" data-testid="board-type">
                <option v-for="item in planTypes" :key="item.value" :value="item.value">{{ item.label }}</option>
              </select>
            </label>
          </div>
          <label>
            Summary
            <textarea v-model="summary" class="field-textarea" data-testid="board-summary" />
          </label>
        </section>

        <section class="glass-panel tactic-board-surface">
          <div class="board-toolbar">
            <div class="marker-controls">
              <select v-model="markerRole" class="field-select compact-field" data-testid="marker-role">
                <option v-for="role in markerRoles" :key="role.value" :value="role.value">{{ role.label }}</option>
              </select>
              <input v-model="markerLabel" class="field compact-field" data-testid="marker-label" placeholder="Label" />
            </div>
            <div class="split-actions">
              <button class="primary-button" data-testid="save-board" :disabled="saving" type="button" @click="saveBoard">
                {{ saving ? 'Saving...' : activeBoardId ? 'Save changes' : 'Create board' }}
              </button>
              <span v-if="saveMessage" class="save-message">{{ saveMessage }}</span>
            </div>
          </div>

          <div class="board-radar" data-testid="board-radar" @click="addMarker">
            <img v-if="radarUrl" :src="radarUrl" :alt="activeMap?.name || 'map radar'" @error="radarFallback = true" />
            <button
              v-for="(marker, index) in markers"
              :key="`${marker.label}-${index}`"
              class="board-marker"
              :style="{ left: `${marker.x}%`, top: `${marker.y}%`, background: markerColor(marker) }"
              type="button"
              :title="marker.label"
              @click.stop="removeMarker(index)"
            >
              {{ marker.label }}
            </button>
          </div>
        </section>

        <section class="glass-panel marker-list-panel">
          <div class="section-heading compact-heading">
            <h2>Markers</h2>
            <span class="muted">{{ markers.length }} items</span>
          </div>
          <div v-if="markers.length" class="marker-list">
            <button
              v-for="(marker, index) in markers"
              :key="`${marker.label}-row-${index}`"
              class="marker-row"
              type="button"
              @click="removeMarker(index)"
            >
              <span class="marker-dot" :style="{ background: markerColor(marker) }" />
              <strong>{{ marker.label }}</strong>
              <span>{{ marker.role }} / x {{ marker.x }} / y {{ marker.y }}</span>
            </button>
          </div>
          <p v-else class="muted small-empty">Click the radar to place a marker.</p>
        </section>

        <section v-if="activeBoardId" class="split-actions">
          <button
            v-for="board in boards.filter((item) => item.id === activeBoardId)"
            :key="board.id"
            class="ghost-button danger-button"
            type="button"
            @click="deleteBoard(board)"
          >
            Delete current board
          </button>
        </section>
      </main>
    </section>
  </div>
</template>

<style scoped>
.boards-page {
  display: grid;
  gap: 18px;
}

.boards-layout {
  display: grid;
  grid-template-columns: 260px minmax(0, 1fr);
  gap: 18px;
  align-items: start;
}

.board-list-panel {
  position: sticky;
  top: 74px;
  display: grid;
  gap: 10px;
  max-height: calc(100vh - 96px);
  overflow: auto;
}

.compact-heading {
  margin-bottom: 6px;
  padding-bottom: 10px;
}

.compact-heading h2 {
  font-size: 1rem;
}

.board-list-item,
.marker-row {
  display: grid;
  gap: 3px;
  width: 100%;
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 8px;
  background: rgba(255,255,255,0.03);
  color: #dfe9f6;
  padding: 10px;
  text-align: left;
}

.board-list-item:hover,
.board-list-item.active,
.marker-row:hover {
  border-color: rgba(255,122,24,0.42);
  background: rgba(255,122,24,0.1);
}

.board-list-item span,
.marker-row span {
  color: #91a3ba;
  font-size: 0.75rem;
}

.board-main {
  display: grid;
  gap: 14px;
  min-width: 0;
}

.board-form-grid {
  display: grid;
  grid-template-columns: minmax(180px, 1.2fr) repeat(3, minmax(120px, 0.6fr));
  gap: 12px;
  margin-bottom: 12px;
}

.board-form-grid label,
.board-editor-panel label {
  display: grid;
  gap: 6px;
  color: #a7b4c6;
  font-size: 0.8rem;
}

.board-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.marker-controls {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.compact-field {
  width: 150px;
}

.board-radar {
  position: relative;
  overflow: hidden;
  border-radius: 8px;
  background: rgba(255,255,255,0.025);
  cursor: crosshair;
  aspect-ratio: 1 / 1;
  min-height: 360px;
}

.board-radar img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.board-marker {
  position: absolute;
  min-width: 28px;
  min-height: 28px;
  max-width: 96px;
  overflow: hidden;
  border: 2px solid #fff;
  border-radius: 999px;
  color: #07111f;
  padding: 3px 8px;
  font-size: 0.72rem;
  font-weight: 900;
  line-height: 1.1;
  text-overflow: ellipsis;
  white-space: nowrap;
  transform: translate(-50%, -50%);
  box-shadow: 0 0 0 7px rgba(255,122,24,0.14);
  cursor: pointer;
}

.board-marker:hover {
  transform: translate(-50%, -50%) scale(1.08);
}

.marker-list {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
  gap: 8px;
}

.marker-row {
  grid-template-columns: auto minmax(0, 0.7fr) minmax(0, 1.3fr);
  align-items: center;
}

.marker-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
}

.save-message {
  color: #8de8be;
  font-size: 0.8rem;
}

.danger-button {
  border-color: rgba(255,120,120,0.28);
  color: #ff9f96;
}

.small-empty {
  margin: 0;
  font-size: 0.8rem;
}

@media (max-width: 920px) {
  .boards-layout {
    grid-template-columns: 1fr;
  }

  .board-list-panel {
    position: static;
    max-height: none;
  }

  .board-form-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 560px) {
  .board-form-grid,
  .marker-row {
    grid-template-columns: 1fr;
  }

  .board-toolbar {
    align-items: stretch;
    flex-direction: column;
  }

  .compact-field {
    width: 100%;
  }

  .board-radar {
    min-height: 280px;
  }
}
</style>

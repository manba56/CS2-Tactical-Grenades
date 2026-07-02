<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue';

import { api, resolveAssetUrl } from '../api';
import { useSessionStore } from '../stores/session';
import type { AdminClipJob, AdminLineup, ClipSegment } from '../types';

type FocusDragState = {
  mode: 'move' | 'resize';
  startClientX: number;
  startClientY: number;
  startX: number;
  startY: number;
  startWidth: number;
  startHeight: number;
};

const session = useSessionStore();
const clips = ref<AdminClipJob[]>([]);
const lineups = ref<AdminLineup[]>([]);
const sourceFile = ref<File | null>(null);
const localPreviewUrl = ref('');
const videoRef = ref<HTMLVideoElement | null>(null);
const videoDuration = ref(0);
const videoCurrentTime = ref(0);
const focusDrag = ref<FocusDragState | null>(null);
const activeClipModule = ref<'lineup_tutorial' | 'kill_highlight'>('lineup_tutorial');
const editingId = ref<number | null>(null);
const editingSegmentIndex = ref<number | null>(null);
const error = ref('');
const notice = ref('');
const loading = ref(false);
const uploading = ref(false);
const renderingId = ref<number | null>(null);
let refreshTimer: number | null = null;

const form = reactive({
  title: '',
  lineup_id: null as number | null,
  source_url: '',
  source_filename: '',
  segments: [] as ClipSegment[],
  template_type: 'lineup_tutorial' as const,
});

const segmentDraft = reactive<ClipSegment>({
  title: '',
  note: '',
  start_seconds: 0,
  end_seconds: 8,
  focus_mode: 'auto_center',
  slow_motion: true,
  focus_point_seconds: 2,
  focus_pause_seconds: 1,
  focus_start_seconds: 2,
  focus_end_seconds: 3,
  focus_x: 0.38,
  focus_y: 0.38,
  focus_width: 0.24,
  focus_height: 0.24,
  focus_scale: 1.2,
  focus_position: 'center',
});

const selectedLineup = computed(() =>
  lineups.value.find((lineup) => lineup.id === form.lineup_id) || null,
);
const lineupSubtitleOptions = computed(() => {
  const lineup = selectedLineup.value;
  if (!lineup) return [];
  const options: { label: string; value: string }[] = [];
  if (lineup.summary?.trim()) options.push({ label: '线路摘要', value: lineup.summary.trim() });
  if (lineup.purpose?.trim()) options.push({ label: '用途说明', value: lineup.purpose.trim() });
  (lineup.steps || []).forEach((step, index) => {
    if (step?.trim()) options.push({ label: `步骤 ${index + 1}`, value: step.trim() });
  });
  return options;
});
const sourcePreviewUrl = computed(() => localPreviewUrl.value || (form.source_url ? resolveAssetUrl(form.source_url) : ''));
const canAddSegment = computed(() => segmentDraft.end_seconds > segmentDraft.start_seconds);
const timelineMax = computed(() => {
  const knownDuration = Number.isFinite(videoDuration.value) ? videoDuration.value : 0;
  if (knownDuration > 0) return knownDuration;
  const draftEdge = Math.max(segmentDraft.start_seconds || 0, segmentDraft.end_seconds || 0);
  return Number(Math.max(draftEdge + 1, 60).toFixed(2));
});
const selectedDuration = computed(() => Math.max(0, segmentDraft.end_seconds - segmentDraft.start_seconds));
const startPercent = computed(() => Math.min(100, Math.max(0, (segmentDraft.start_seconds / timelineMax.value) * 100)));
const endPercent = computed(() => Math.min(100, Math.max(0, (segmentDraft.end_seconds / timelineMax.value) * 100)));
const playheadPercent = computed(() => Math.min(100, Math.max(0, (videoCurrentTime.value / timelineMax.value) * 100)));
const timelineRangeStyle = computed(() => ({
  '--range-start': `${startPercent.value}%`,
  '--range-end': `${endPercent.value}%`,
  '--playhead': `${playheadPercent.value}%`,
}));
const timelineTickTimes = computed(() => {
  const max = timelineMax.value;
  return [0, max * 0.25, max * 0.5, max * 0.75, max].map((value) => Number(value.toFixed(1)));
});
const focusDurationMax = computed(() => Math.max(0.1, selectedDuration.value));
const focusBoxStyle = computed(() => ({
  left: `${(segmentDraft.focus_x ?? 0.38) * 100}%`,
  top: `${(segmentDraft.focus_y ?? 0.38) * 100}%`,
  width: `${(segmentDraft.focus_width ?? 0.24) * 100}%`,
  height: `${(segmentDraft.focus_height ?? 0.24) * 100}%`,
}));

function flash(message: string) {
  notice.value = message;
  window.clearTimeout((flash as any)._timer);
  (flash as any)._timer = window.setTimeout(() => {
    if (notice.value === message) notice.value = '';
  }, 1800);
}

function formatTime(seconds: number) {
  const safe = Math.max(0, Number(seconds) || 0);
  const minutes = Math.floor(safe / 60);
  const secs = Math.floor(safe % 60);
  const tenths = Math.floor((safe - Math.floor(safe)) * 10);
  return `${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}.${tenths}`;
}

function parseTime(value: string) {
  const trimmed = value.trim();
  if (!trimmed) return 0;
  if (!trimmed.includes(':')) return Number(trimmed) || 0;
  const parts = trimmed.split(':').map(Number);
  if (parts.length === 2) return (parts[0] || 0) * 60 + (parts[1] || 0);
  if (parts.length === 3) return (parts[0] || 0) * 3600 + (parts[1] || 0) * 60 + (parts[2] || 0);
  return 0;
}

function currentVideoTime() {
  const domTime = videoRef.value?.currentTime;
  if (Number.isFinite(domTime) && Number(domTime) > 0) return Number(domTime);
  return Number(videoCurrentTime.value || 0);
}

function clampTimelineSeconds(value: number) {
  const safe = Number.isFinite(value) ? value : 0;
  return Number(Math.min(Math.max(safe, 0), timelineMax.value).toFixed(2));
}

function seekPreview(seconds: number) {
  if (!videoRef.value) return;
  videoRef.value.currentTime = clampTimelineSeconds(seconds);
  videoCurrentTime.value = videoRef.value.currentTime;
}

function normalizeDraftRange() {
  const minDuration = 0.1;
  const max = timelineMax.value;
  segmentDraft.start_seconds = clampTimelineSeconds(segmentDraft.start_seconds);
  segmentDraft.end_seconds = clampTimelineSeconds(segmentDraft.end_seconds);
  if (segmentDraft.end_seconds <= segmentDraft.start_seconds) {
    segmentDraft.end_seconds = Number(Math.min(max, segmentDraft.start_seconds + minDuration).toFixed(2));
  }
  if (segmentDraft.end_seconds <= segmentDraft.start_seconds) {
    segmentDraft.start_seconds = Number(Math.max(0, segmentDraft.end_seconds - minDuration).toFixed(2));
  }
  normalizeDraftFocus();
}

function clampNumber(value: number | null | undefined, min: number, max: number, fallback: number) {
  const safe = Number.isFinite(value) ? Number(value) : fallback;
  return Number(Math.min(Math.max(safe, min), max).toFixed(3));
}

function defaultFocusStart(duration = selectedDuration.value) {
  return Number(Math.min(Math.max(0.8, duration * 0.25), Math.max(0, duration - 0.1)).toFixed(2));
}

function defaultFocusEnd(duration = selectedDuration.value) {
  const start = defaultFocusStart(duration);
  return Number(Math.min(duration, Math.max(start + 0.8, duration * 0.78)).toFixed(2));
}

function normalizeDraftFocus(forceDefaults = false) {
  const duration = focusDurationMax.value;
  if (forceDefaults || segmentDraft.focus_point_seconds === undefined || segmentDraft.focus_point_seconds === null) {
    segmentDraft.focus_point_seconds = defaultFocusStart(duration);
  }
  segmentDraft.focus_pause_seconds = clampNumber(segmentDraft.focus_pause_seconds, 0.2, 5, 1);
  segmentDraft.focus_point_seconds = clampNumber(segmentDraft.focus_point_seconds, 0, duration, defaultFocusStart(duration));
  segmentDraft.focus_start_seconds = segmentDraft.focus_point_seconds;
  segmentDraft.focus_end_seconds = Number((segmentDraft.focus_point_seconds + segmentDraft.focus_pause_seconds).toFixed(2));

  const width = clampNumber(segmentDraft.focus_width, 0.08, 1, 0.24);
  const height = clampNumber(segmentDraft.focus_height, 0.08, 1, 0.24);
  segmentDraft.focus_width = width;
  segmentDraft.focus_height = height;
  segmentDraft.focus_x = clampNumber(segmentDraft.focus_x, 0, Math.max(0, 1 - width), 0.38);
  segmentDraft.focus_y = clampNumber(segmentDraft.focus_y, 0, Math.max(0, 1 - height), 0.38);
  segmentDraft.focus_scale = clampNumber(segmentDraft.focus_scale, 0.8, 2.4, 1.2);
  segmentDraft.focus_position = segmentDraft.focus_position || 'center';
}

function withFocusDefaults(segment: ClipSegment): ClipSegment {
  const duration = Math.max(0.1, segment.end_seconds - segment.start_seconds);
  const fallbackStart = defaultFocusStart(duration);
  const point = clampNumber(segment.focus_point_seconds ?? segment.focus_start_seconds, 0, duration, fallbackStart);
  const pause = clampNumber(segment.focus_pause_seconds, 0.2, 5, 1);
  const width = clampNumber(segment.focus_width, 0.08, 1, 0.24);
  const height = clampNumber(segment.focus_height, 0.08, 1, 0.24);
  return {
    ...segment,
    focus_mode: segment.focus_mode || 'auto_center',
    slow_motion: segment.slow_motion !== false,
    focus_point_seconds: point,
    focus_pause_seconds: pause,
    focus_start_seconds: point,
    focus_end_seconds: Number((point + pause).toFixed(2)),
    focus_x: clampNumber(segment.focus_x, 0, Math.max(0, 1 - width), 0.38),
    focus_y: clampNumber(segment.focus_y, 0, Math.max(0, 1 - height), 0.38),
    focus_width: width,
    focus_height: height,
    focus_scale: clampNumber(segment.focus_scale, 0.8, 2.4, 1.2),
    focus_position: segment.focus_position || 'center',
  };
}

function defaultSegmentTitle() {
  const index = form.segments.length + 1;
  if (index === 1) return '站位与瞄点';
  if (index === 2) return '投掷动作';
  if (index === 3) return '落点效果';
  return `教学片段 ${index}`;
}

function fillLineupDefaults() {
  if (!selectedLineup.value) return;
  if (!form.title.trim()) {
    form.title = `${selectedLineup.value.title} 教学剪辑`;
  }
  if (!segmentDraft.note.trim()) {
    segmentDraft.note = selectedLineup.value.summary || selectedLineup.value.purpose || '';
  }
}

function useLineupSubtitle(event: Event) {
  const value = (event.target as HTMLSelectElement).value;
  if (value) {
    segmentDraft.note = value;
  }
}

function resetSegmentDraft(start = 0) {
  Object.assign(segmentDraft, {
    title: defaultSegmentTitle(),
    note: selectedLineup.value?.summary || '',
    start_seconds: Number(start.toFixed(2)),
    end_seconds: Number((start + 8).toFixed(2)),
    focus_mode: 'auto_center',
    slow_motion: true,
    focus_point_seconds: 2,
    focus_pause_seconds: 1,
    focus_start_seconds: 2,
    focus_end_seconds: 3,
    focus_x: 0.38,
    focus_y: 0.38,
    focus_width: 0.24,
    focus_height: 0.24,
    focus_scale: 1.2,
    focus_position: 'center',
  });
  normalizeDraftFocus(true);
}

function setDraftStart() {
  const now = Number(currentVideoTime().toFixed(2));
  segmentDraft.start_seconds = now;
  if (segmentDraft.end_seconds <= now) {
    segmentDraft.end_seconds = Number((now + 8).toFixed(2));
  }
  normalizeDraftRange();
  if (!segmentDraft.title.trim()) segmentDraft.title = defaultSegmentTitle();
  flash(`已记录开始点：${formatTime(now)}`);
}

function setDraftEnd() {
  const now = Number(currentVideoTime().toFixed(2));
  segmentDraft.end_seconds = now;
  normalizeDraftRange();
  flash(`已记录结束点：${formatTime(now)}`);
}

function setEndAndAdd() {
  setDraftEnd();
  addSegment();
}

function setStartFromText(event: Event) {
  segmentDraft.start_seconds = parseTime((event.target as HTMLInputElement).value);
  normalizeDraftRange();
  seekPreview(segmentDraft.start_seconds);
}

function setEndFromText(event: Event) {
  segmentDraft.end_seconds = parseTime((event.target as HTMLInputElement).value);
  normalizeDraftRange();
  seekPreview(segmentDraft.end_seconds);
}

function setStartFromTimeline(event: Event) {
  const raw = Number((event.target as HTMLInputElement).value);
  const minDuration = 0.1;
  segmentDraft.start_seconds = Number(Math.min(clampTimelineSeconds(raw), segmentDraft.end_seconds - minDuration).toFixed(2));
  normalizeDraftRange();
  if (!segmentDraft.title.trim()) segmentDraft.title = defaultSegmentTitle();
  seekPreview(segmentDraft.start_seconds);
}

function setEndFromTimeline(event: Event) {
  const raw = Number((event.target as HTMLInputElement).value);
  const minDuration = 0.1;
  segmentDraft.end_seconds = Number(Math.max(clampTimelineSeconds(raw), segmentDraft.start_seconds + minDuration).toFixed(2));
  normalizeDraftRange();
  if (!segmentDraft.title.trim()) segmentDraft.title = defaultSegmentTitle();
  seekPreview(segmentDraft.end_seconds);
}

function setFocusPointFromTimeline(event: Event) {
  const raw = Number((event.target as HTMLInputElement).value);
  segmentDraft.focus_point_seconds = Number(raw.toFixed(2));
  normalizeDraftFocus();
  seekPreview(segmentDraft.start_seconds + (segmentDraft.focus_point_seconds || 0));
}

function setFocusPointAtTime(seconds: number, quiet = false) {
  const now = clampTimelineSeconds(seconds);
  if (now < segmentDraft.start_seconds) {
    segmentDraft.start_seconds = now;
  }
  if (now > segmentDraft.end_seconds) {
    segmentDraft.end_seconds = now;
  }
  normalizeDraftRange();
  segmentDraft.focus_point_seconds = Number(Math.max(0, now - segmentDraft.start_seconds).toFixed(2));
  normalizeDraftFocus();
  videoCurrentTime.value = now;
  if (!quiet) flash(`Focus point set at ${formatTime(now)}`);
}

function setFocusPointToCurrent() {
  setFocusPointAtTime(currentVideoTime());
}

function syncFocusPointToCurrentFrame() {
  if (!sourcePreviewUrl.value || segmentDraft.focus_mode === 'none') return;
  setFocusPointAtTime(currentVideoTime(), true);
}

function startFocusDrag(event: PointerEvent, mode: 'move' | 'resize') {
  if (!videoRef.value || segmentDraft.focus_mode === 'none') return;
  event.preventDefault();
  focusDrag.value = {
    mode,
    startClientX: event.clientX,
    startClientY: event.clientY,
    startX: segmentDraft.focus_x ?? 0.38,
    startY: segmentDraft.focus_y ?? 0.38,
    startWidth: segmentDraft.focus_width ?? 0.24,
    startHeight: segmentDraft.focus_height ?? 0.24,
  };
  window.addEventListener('pointermove', onFocusDrag);
  window.addEventListener('pointerup', stopFocusDrag, { once: true });
}

function onFocusDrag(event: PointerEvent) {
  if (!focusDrag.value || !videoRef.value) return;
  const bounds = videoRef.value.getBoundingClientRect();
  if (!bounds.width || !bounds.height) return;
  const deltaX = (event.clientX - focusDrag.value.startClientX) / bounds.width;
  const deltaY = (event.clientY - focusDrag.value.startClientY) / bounds.height;
  if (focusDrag.value.mode === 'move') {
    const width = segmentDraft.focus_width ?? 0.24;
    const height = segmentDraft.focus_height ?? 0.24;
    segmentDraft.focus_x = clampNumber(focusDrag.value.startX + deltaX, 0, 1 - width, 0.38);
    segmentDraft.focus_y = clampNumber(focusDrag.value.startY + deltaY, 0, 1 - height, 0.38);
  } else {
    const nextSize = clampNumber(
      focusDrag.value.startWidth + Math.max(deltaX, deltaY),
      0.08,
      Math.min(1 - focusDrag.value.startX, 1 - focusDrag.value.startY),
      0.24,
    );
    segmentDraft.focus_width = nextSize;
    segmentDraft.focus_height = nextSize;
  }
  normalizeDraftFocus();
}

function stopFocusDrag() {
  focusDrag.value = null;
  window.removeEventListener('pointermove', onFocusDrag);
}

function buildSegmentFromDraft(): ClipSegment {
  normalizeDraftFocus();
  return {
    title: segmentDraft.title.trim() || defaultSegmentTitle(),
    note: segmentDraft.note.trim(),
    start_seconds: Number(segmentDraft.start_seconds.toFixed(2)),
    end_seconds: Number(segmentDraft.end_seconds.toFixed(2)),
    focus_mode: segmentDraft.focus_mode || 'auto_center',
    slow_motion: segmentDraft.slow_motion !== false,
    focus_point_seconds: Number((segmentDraft.focus_point_seconds ?? defaultFocusStart()).toFixed(2)),
    focus_pause_seconds: Number((segmentDraft.focus_pause_seconds ?? 1).toFixed(2)),
    focus_start_seconds: Number((segmentDraft.focus_start_seconds ?? segmentDraft.focus_point_seconds ?? defaultFocusStart()).toFixed(2)),
    focus_end_seconds: Number((segmentDraft.focus_end_seconds ?? ((segmentDraft.focus_point_seconds ?? defaultFocusStart()) + (segmentDraft.focus_pause_seconds ?? 1))).toFixed(2)),
    focus_x: Number((segmentDraft.focus_x ?? 0.38).toFixed(3)),
    focus_y: Number((segmentDraft.focus_y ?? 0.38).toFixed(3)),
    focus_width: Number((segmentDraft.focus_width ?? 0.24).toFixed(3)),
    focus_height: Number((segmentDraft.focus_height ?? 0.24).toFixed(3)),
    focus_scale: Number((segmentDraft.focus_scale ?? 1.2).toFixed(2)),
    focus_position: segmentDraft.focus_position || 'center',
  };
}

function addSegment() {
  error.value = '';
  normalizeDraftFocus();
  if (!canAddSegment.value) {
    error.value = '片段结束时间必须大于开始时间。先播放到结束位置，再点“设为结束并加入片段”。';
    return;
  }
  form.segments.push({
    title: segmentDraft.title.trim() || defaultSegmentTitle(),
    note: segmentDraft.note.trim(),
    start_seconds: Number(segmentDraft.start_seconds.toFixed(2)),
    end_seconds: Number(segmentDraft.end_seconds.toFixed(2)),
    focus_mode: segmentDraft.focus_mode || 'auto_center',
    slow_motion: segmentDraft.slow_motion !== false,
    focus_point_seconds: Number((segmentDraft.focus_point_seconds ?? defaultFocusStart()).toFixed(2)),
    focus_pause_seconds: Number((segmentDraft.focus_pause_seconds ?? 1).toFixed(2)),
    focus_start_seconds: Number((segmentDraft.focus_start_seconds ?? segmentDraft.focus_point_seconds ?? defaultFocusStart()).toFixed(2)),
    focus_end_seconds: Number((segmentDraft.focus_end_seconds ?? ((segmentDraft.focus_point_seconds ?? defaultFocusStart()) + (segmentDraft.focus_pause_seconds ?? 1))).toFixed(2)),
    focus_x: Number((segmentDraft.focus_x ?? 0.38).toFixed(3)),
    focus_y: Number((segmentDraft.focus_y ?? 0.38).toFixed(3)),
    focus_width: Number((segmentDraft.focus_width ?? 0.24).toFixed(3)),
    focus_height: Number((segmentDraft.focus_height ?? 0.24).toFixed(3)),
    focus_scale: Number((segmentDraft.focus_scale ?? 1.2).toFixed(2)),
    focus_position: segmentDraft.focus_position || 'center',
  });
  const nextStart = segmentDraft.end_seconds;
  resetSegmentDraft(nextStart);
  flash(`已加入片段 ${form.segments.length}`);
}

function editSegment(index: number) {
  const segment = form.segments[index];
  if (!segment) return;
  editingSegmentIndex.value = index;
  Object.assign(segmentDraft, withFocusDefaults({ ...segment }));
  normalizeDraftRange();
  seekPreview(segmentDraft.start_seconds);
  flash(`Editing segment ${index + 1}`);
}

function applySegmentEdit() {
  error.value = '';
  if (editingSegmentIndex.value === null) return;
  if (!canAddSegment.value) {
    error.value = 'Segment end time must be greater than start time.';
    return;
  }
  const index = editingSegmentIndex.value;
  const nextSegment = buildSegmentFromDraft();
  form.segments.splice(index, 1, nextSegment);
  editingSegmentIndex.value = null;
  resetSegmentDraft(nextSegment.end_seconds);
  flash(`Updated segment ${index + 1}`);
}

function createSegmentAfter(index: number) {
  const baseSegment = form.segments[index];
  if (!baseSegment) return;
  const insertIndex = index + 1;
  resetSegmentDraft(baseSegment.end_seconds);
  const nextSegment = buildSegmentFromDraft();
  form.segments.splice(insertIndex, 0, nextSegment);
  editingSegmentIndex.value = insertIndex;
  Object.assign(segmentDraft, withFocusDefaults({ ...nextSegment }));
  normalizeDraftRange();
  seekPreview(nextSegment.start_seconds);
  flash(`Added segment ${insertIndex + 1}`);
}

function saveAndCreateNextSegment() {
  error.value = '';
  if (editingSegmentIndex.value === null) return;
  if (!canAddSegment.value) {
    error.value = 'Segment end time must be greater than start time.';
    return;
  }
  const index = editingSegmentIndex.value;
  const updatedSegment = buildSegmentFromDraft();
  form.segments.splice(index, 1, updatedSegment);
  createSegmentAfter(index);
}

function cancelSegmentEdit() {
  editingSegmentIndex.value = null;
  resetSegmentDraft(segmentDraft.end_seconds);
  flash('Canceled segment edit');
}
function removeSegment(index: number) {
  form.segments.splice(index, 1);
  if (editingSegmentIndex.value === null) return;
  if (editingSegmentIndex.value === index) {
    editingSegmentIndex.value = null;
    resetSegmentDraft();
    return;
  }
  if (editingSegmentIndex.value > index) {
    editingSegmentIndex.value -= 1;
  }
}

function moveSegment(index: number, direction: -1 | 1) {
  const next = index + direction;
  if (next < 0 || next >= form.segments.length) return;
  const [item] = form.segments.splice(index, 1);
  form.segments.splice(next, 0, item);
  if (editingSegmentIndex.value === index) {
    editingSegmentIndex.value = next;
  } else if (editingSegmentIndex.value === next) {
    editingSegmentIndex.value = index;
  }
}

function seekTo(seconds: number) {
  if (!videoRef.value) return;
  videoRef.value.currentTime = seconds;
  videoRef.value.play().catch(() => {});
}

function onVideoLoadedMetadata() {
  const duration = videoRef.value?.duration || 0;
  videoDuration.value = Number.isFinite(duration) ? Number(duration.toFixed(2)) : 0;
  normalizeDraftRange();
}

function onVideoTimeUpdate() {
  videoCurrentTime.value = currentVideoTime();
}

function onFileChange(event: Event) {
  const target = event.target as HTMLInputElement | null;
  const nextFile = target?.files?.[0] || null;
  if (localPreviewUrl.value) {
    URL.revokeObjectURL(localPreviewUrl.value);
    localPreviewUrl.value = '';
  }
  sourceFile.value = nextFile;
  form.source_url = '';
  videoDuration.value = 0;
  videoCurrentTime.value = 0;
  if (!nextFile) return;
  localPreviewUrl.value = URL.createObjectURL(nextFile);
  form.source_filename = nextFile.name;
  if (!form.title.trim()) {
    form.title = nextFile.name.replace(/\.[^.]+$/, '');
  }
  resetSegmentDraft(0);
  flash('已选择视频，可以直接预览和打点；保存时会自动上传');
}

async function uploadSource() {
  if (form.source_url) return true;
  if (!sourceFile.value) return false;
  uploading.value = true;
  error.value = '';
  notice.value = '';
  try {
    const uploaded = await api.uploadClipSource(sourceFile.value, session.token);
    form.source_url = uploaded.url;
    form.source_filename = uploaded.original_name || uploaded.filename;
    if (!form.title.trim()) {
      form.title = (uploaded.original_name || uploaded.filename).replace(/\.[^.]+$/, '');
    }
    resetSegmentDraft(0);
    flash('视频上传完成，可以开始打点');
    return true;
  } catch (err) {
    error.value = err instanceof Error ? err.message : '视频上传失败';
    return false;
  } finally {
    uploading.value = false;
  }
}

function buildPayload() {
  return {
    title: form.title.trim(),
    lineup_id: form.lineup_id,
    source_url: form.source_url,
    source_filename: form.source_filename,
    segments: form.segments,
    template_type: form.template_type,
  };
}

async function saveClip(renderAfterSave = false) {
  error.value = '';
  notice.value = renderAfterSave ? '正在保存并渲染...' : '正在保存...';
  if (!form.source_url) {
    error.value = '请先上传录屏视频';
    notice.value = '';
    return;
  }
  if (!form.title.trim()) {
    error.value = '请填写剪辑标题';
    notice.value = '';
    return;
  }
  if (!form.segments.length) {
    error.value = '至少添加一个剪辑片段。推荐流程：播放到开始位置 -> 设为开始 -> 播放到结束位置 -> 设为结束并加入片段。';
    notice.value = '';
    return;
  }
  loading.value = true;
  try {
    if (!form.source_url) {
      notice.value = '正在上传视频...';
      const uploaded = await uploadSource();
      if (!uploaded) {
        notice.value = '';
        loading.value = false;
        return;
      }
    }
    const saved = editingId.value
      ? await api.updateClip(editingId.value, buildPayload(), session.token)
      : await api.createClip(buildPayload(), session.token);
    editingId.value = saved.id;
    await load();
    if (renderAfterSave) {
      await renderClip(saved);
    } else {
      flash('剪辑任务已保存');
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : '保存剪辑任务失败';
    notice.value = '';
  } finally {
    loading.value = false;
  }
}

async function renderClip(item: AdminClipJob) {
  renderingId.value = item.id;
  error.value = '';
  notice.value = '已提交渲染，右侧任务状态会自动刷新...';
  try {
    await api.renderClip(item.id, session.token);
    await load();
    startAutoRefresh(item.id);
  } catch (err) {
    error.value = err instanceof Error ? err.message : '视频渲染失败';
    notice.value = '';
    await load();
    renderingId.value = null;
  }
}

function startAutoRefresh(clipId: number) {
  if (refreshTimer !== null) {
    window.clearInterval(refreshTimer);
  }
  refreshTimer = window.setInterval(async () => {
    await load();
    const current = clips.value.find((clip) => clip.id === clipId);
    if (!current) return;
    if (current.status === 'ready') {
      if (refreshTimer !== null) window.clearInterval(refreshTimer);
      refreshTimer = null;
      renderingId.value = null;
      flash('视频渲染完成，右侧任务卡片可以预览或下载');
    }
    if (current.status === 'failed') {
      if (refreshTimer !== null) window.clearInterval(refreshTimer);
      refreshTimer = null;
      renderingId.value = null;
      error.value = current.error || '渲染失败，请查看任务错误';
      notice.value = '';
    }
  }, 1500);
}

function editClip(item: AdminClipJob) {
  editingId.value = item.id;
  editingSegmentIndex.value = null;
  Object.assign(form, {
    title: item.title,
    lineup_id: item.lineup_id,
    source_url: item.source_url,
    source_filename: item.source_filename,
    segments: (item.segments || []).map((segment) => withFocusDefaults({ ...segment })),
    template_type: item.template_type,
  });
  resetSegmentDraft();
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

async function removeClip(item: AdminClipJob) {
  if (!confirm(`删除剪辑任务 "${item.title}"?`)) return;
  try {
    await api.deleteClip(item.id, session.token);
    if (editingId.value === item.id) resetForm();
    await load();
    flash('剪辑任务已删除');
  } catch (err) {
    error.value = err instanceof Error ? err.message : '删除剪辑任务失败';
  }
}

function resetForm() {
  editingId.value = null;
  editingSegmentIndex.value = null;
  sourceFile.value = null;
  if (localPreviewUrl.value) {
    URL.revokeObjectURL(localPreviewUrl.value);
    localPreviewUrl.value = '';
  }
  Object.assign(form, {
    title: '',
    lineup_id: lineups.value[0]?.id || null,
    source_url: '',
    source_filename: '',
    segments: [],
    template_type: 'lineup_tutorial',
  });
  resetSegmentDraft();
}

async function load() {
  loading.value = true;
  try {
    const [clipItems, lineupItems] = await Promise.all([
      api.clips(session.token),
      api.lineups(session.token),
    ]);
    clips.value = clipItems;
    lineups.value = lineupItems;
    if (!form.lineup_id && lineupItems[0]) {
      form.lineup_id = lineupItems[0].id;
      fillLineupDefaults();
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : '加载剪辑中心失败';
  } finally {
    loading.value = false;
  }
}

onMounted(async () => {
  await load();
  resetSegmentDraft();
});

onUnmounted(() => {
  if (refreshTimer !== null) {
    window.clearInterval(refreshTimer);
  }
  window.removeEventListener('pointermove', onFocusDrag);
  if (localPreviewUrl.value) {
    URL.revokeObjectURL(localPreviewUrl.value);
  }
});
</script>

<template>
  <section class="clip-page">
    <div class="page-header">
      <h1>剪辑中心</h1>
      <p class="muted">上传道具教学录屏，在播放器里打点，自动拼接成教学视频。</p>
    </div>

    <p v-if="error" class="danger-message">{{ error }}</p>
    <p v-if="notice" class="success-message">{{ notice }}</p>

    <div class="module-tabs">
      <button
        type="button"
        class="module-tab"
        :class="{ active: activeClipModule === 'lineup_tutorial' }"
        @click="activeClipModule = 'lineup_tutorial'"
      >
        道具教学
      </button>
      <button
        type="button"
        class="module-tab"
        :class="{ active: activeClipModule === 'kill_highlight' }"
        @click="activeClipModule = 'kill_highlight'"
      >
        击杀集锦
      </button>
    </div>

    <div v-if="activeClipModule === 'lineup_tutorial'" class="clip-workspace">
      <section class="panel editor-panel">
        <div class="inline-row editor-title">
          <h2>{{ editingId ? '编辑剪辑任务' : '新建道具教学剪辑' }}</h2>
          <span class="chip">{{ form.segments.length }} 个片段</span>
        </div>

        <div class="form-grid">
          <label>
            剪辑标题
            <input v-model="form.title" class="field" placeholder="Mirage VIP 烟教学剪辑" />
          </label>
          <label>
            关联道具线路
            <select v-model.number="form.lineup_id" class="select" @change="fillLineupDefaults">
              <option :value="null">不关联线路</option>
              <option v-for="lineup in lineups" :key="lineup.id" :value="lineup.id">
                {{ lineup.map?.name || '#' + lineup.map_id }} / {{ lineup.title }}
              </option>
            </select>
          </label>
          <label class="full">
            上传录屏视频
            <div class="upload-row">
              <input type="file" class="field" accept="video/mp4,video/quicktime,video/x-matroska,video/webm,video/*" @change="onFileChange" />
              <button type="button" class="button" :disabled="(!sourceFile && !form.source_url) || uploading || !!form.source_url" @click="uploadSource">
                {{ uploading ? '上传中...' : (form.source_url ? '已上传' : '上传到服务器') }}
              </button>
            </div>
          </label>
        </div>

        <div v-if="selectedLineup" class="lineup-summary">
          <strong>{{ selectedLineup.title }}</strong>
          <span class="chip">{{ selectedLineup.utility_type }}</span>
          <span class="chip">{{ selectedLineup.side }}</span>
          <span class="muted">
            {{ selectedLineup.start_point?.name || '站位' }} ->
            {{ selectedLineup.aim_point?.name || '瞄点' }} ->
            {{ selectedLineup.land_point?.name || '落点' }}
          </span>
        </div>

        <div class="draft-bar">
          <strong>当前片段草稿</strong>
          <span>{{ formatTime(segmentDraft.start_seconds) }} - {{ formatTime(segmentDraft.end_seconds) }}</span>
          <span class="muted">时长 {{ Math.max(0, segmentDraft.end_seconds - segmentDraft.start_seconds).toFixed(1) }} 秒</span>
        </div>

        <div class="tuning-layout">
          <div class="preview-column">
        <div class="video-stage">
          <div v-if="sourcePreviewUrl" class="video-focus-wrap">
            <video
            ref="videoRef"
            :src="sourcePreviewUrl"
            controls
            preload="metadata"
            @loadedmetadata="onVideoLoadedMetadata"
            @timeupdate="onVideoTimeUpdate"
            @seeked="syncFocusPointToCurrentFrame"
            @pause="syncFocusPointToCurrentFrame"
          />
            <div v-if="segmentDraft.focus_mode !== 'none'" class="focus-overlay">
              <div class="focus-box" :style="focusBoxStyle" @pointerdown="startFocusDrag($event, 'move')">
                <span class="focus-label">AIM ZOOM</span>
                <span class="focus-resize" @pointerdown.stop="startFocusDrag($event, 'resize')"></span>
              </div>
            </div>
          </div>
          <div v-else class="video-empty">选择视频后即可预览和打点</div>
        </div>

        <div v-if="sourcePreviewUrl" class="range-panel" :style="timelineRangeStyle">
          <div class="range-header">
            <strong>拖动选择片段范围</strong>
            <span class="muted">
              当前 {{ formatTime(videoCurrentTime) }} / {{ formatTime(timelineMax) }}
            </span>
          </div>
          <div class="range-shell">
            <div class="range-track" aria-hidden="true">
              <span class="range-selection"></span>
              <span class="range-playhead"></span>
            </div>
            <input
              class="range-input range-input-start"
              type="range"
              min="0"
              :max="timelineMax"
              step="0.1"
              :value="segmentDraft.start_seconds"
              aria-label="选择片段开始时间"
              @input="setStartFromTimeline"
            />
            <input
              class="range-input range-input-end"
              type="range"
              min="0"
              :max="timelineMax"
              step="0.1"
              :value="segmentDraft.end_seconds"
              aria-label="选择片段结束时间"
              @input="setEndFromTimeline"
            />
          </div>
          <div class="range-ticks">
            <span v-for="tick in timelineTickTimes" :key="tick">{{ formatTime(tick) }}</span>
          </div>
          <div class="range-footer">
            <span>开始 {{ formatTime(segmentDraft.start_seconds) }}</span>
            <span>结束 {{ formatTime(segmentDraft.end_seconds) }}</span>
            <span>选中 {{ selectedDuration.toFixed(1) }} 秒</span>
          </div>
        </div>

        <div class="quick-actions">
          <button type="button" class="button" :disabled="!sourcePreviewUrl" @click="setDraftStart">1. 设为开始</button>
          <button type="button" class="button" :disabled="!sourcePreviewUrl" @click="setEndAndAdd">2. 设为结束并加入片段</button>
          <button type="button" class="ghost-button" :disabled="!sourcePreviewUrl" @click="setDraftEnd">只设为结束</button>
        </div>

          </div>

        <div class="segment-editor">
          <div class="segment-time-grid">
            <label>
              开始时间
              <input class="field" :value="formatTime(segmentDraft.start_seconds)" @change="setStartFromText" />
            </label>
            <label>
              结束时间
              <input class="field" :value="formatTime(segmentDraft.end_seconds)" @change="setEndFromText" />
            </label>
          </div>
          <div class="form-grid">
            <label>
              片段标题
              <input v-model="segmentDraft.title" class="field" />
            </label>
            <label>
              字幕说明
              <input v-model="segmentDraft.note" class="field" />
            </label>
            <label v-if="lineupSubtitleOptions.length">
              字幕来源
              <select class="select" :value="segmentDraft.note" @change="useLineupSubtitle">
                <option value="">从关联道具线路里选择</option>
                <option v-for="option in lineupSubtitleOptions" :key="option.label + option.value" :value="option.value">
                  {{ option.label }}
                </option>
              </select>
            </label>
            <label>
              教学特写
              <select v-model="segmentDraft.focus_mode" class="select">
                <option value="auto_center">自动放大画面中心瞄点</option>
                <option value="none">不放大</option>
              </select>
            </label>
            <label class="checkbox-row">
              <input v-model="segmentDraft.slow_motion" type="checkbox" />
              显示慢放教学提示
            </label>
          </div>
          <div v-if="segmentDraft.focus_mode !== 'none'" class="focus-panel">
            <div class="focus-panel-header">
              <strong>瞄点放大</strong>
              <span class="muted">
                {{ formatTime(segmentDraft.start_seconds + (segmentDraft.focus_point_seconds || 0)) }}
                /
                停 {{ (segmentDraft.focus_pause_seconds || 1).toFixed(1) }} 秒
              </span>
            </div>
            <div class="focus-time-grid">
              <label>
                放大时间点
                <input
                  type="range"
                  min="0"
                  :max="focusDurationMax"
                  step="0.1"
                  :value="segmentDraft.focus_point_seconds || 0"
                  @input="setFocusPointFromTimeline"
                />
              </label>
              <label>
                停顿时间 {{ (segmentDraft.focus_pause_seconds || 1).toFixed(1) }} 秒
                <input
                  type="range"
                  step="0.1"
                  v-model.number="segmentDraft.focus_pause_seconds"
                  min="0.2"
                  max="5"
                  @input="normalizeDraftFocus()"
                />
              </label>
            </div>
            <div class="toolbar compact-toolbar">
              <button type="button" class="ghost-button" :disabled="!sourcePreviewUrl" @click="setFocusPointToCurrent">当前帧作为放大点</button>
            </div>
            <div class="form-grid">
              <label>
                小窗位置
                <select v-model="segmentDraft.focus_position" class="select">
                  <option value="top_right">右上</option>
                  <option value="top_left">左上</option>
                  <option value="bottom_right">右下</option>
                  <option value="bottom_left">左下</option>
                  <option value="center">居中</option>
                </select>
              </label>
              <label>
                小窗大小 {{ ((segmentDraft.focus_scale || 1) * 100).toFixed(0) }}%
                <input
                  v-model.number="segmentDraft.focus_scale"
                  type="range"
                  min="0.8"
                  max="2.4"
                  step="0.05"
                  @input="normalizeDraftFocus()"
                />
              </label>
            </div>
          </div>
          <div class="toolbar">
            <button v-if="editingSegmentIndex === null" type="button" class="button" :disabled="!canAddSegment" @click="addSegment">手动加入片段</button>
            <button v-else type="button" class="button" :disabled="!canAddSegment" @click="applySegmentEdit">应用修改</button>
            <button v-if="editingSegmentIndex !== null" type="button" class="button" :disabled="!canAddSegment" @click="saveAndCreateNextSegment">保存并新增下一段</button>
            <button v-if="editingSegmentIndex !== null" type="button" class="ghost-button" @click="cancelSegmentEdit">取消编辑</button>
            <button type="button" class="ghost-button" @click="resetSegmentDraft()">重置片段</button>
          </div>
        </div>

        </div>

        <div class="timeline-list">
          <article v-for="(segment, index) in form.segments" :key="index" class="timeline-item" :class="{ editing: editingSegmentIndex === index }">
            <button type="button" class="timecode" @click="seekTo(segment.start_seconds)">
              {{ formatTime(segment.start_seconds) }} - {{ formatTime(segment.end_seconds) }}
            </button>
            <div>
              <strong>{{ index + 1 }}. {{ segment.title }}</strong>
              <p class="muted">{{ segment.note || '无字幕说明' }}</p>
            </div>
            <div class="timeline-actions">
              <button type="button" class="ghost-button" @click="editSegment(index)">编辑</button>
              <button type="button" class="ghost-button" @click="createSegmentAfter(index)">新增下段</button>
              <button type="button" class="ghost-button" :disabled="index === 0" @click="moveSegment(index, -1)">上移</button>
              <button type="button" class="ghost-button" :disabled="index === form.segments.length - 1" @click="moveSegment(index, 1)">下移</button>
              <button type="button" class="ghost-button danger" @click="removeSegment(index)">删除</button>
            </div>
          </article>
          <div v-if="!form.segments.length" class="empty-card">
            还没有片段。推荐流程：播放到开始位置 -> 设为开始 -> 播放到结束位置 -> 设为结束并加入片段。
          </div>
        </div>

        <div class="form-actions">
          <button type="button" class="button" :disabled="loading" @click="saveClip(false)">
            {{ editingId ? '保存修改' : '保存任务' }}
          </button>
          <button type="button" class="button" :disabled="loading || renderingId !== null" @click="saveClip(true)">
            {{ renderingId !== null ? '渲染中...' : '保存并渲染' }}
          </button>
          <button type="button" class="secondary-button" @click="resetForm">新建空白任务</button>
        </div>
      </section>

      <aside class="panel job-panel">
        <div class="inline-row editor-title">
          <h2>剪辑任务</h2>
          <button class="ghost-button" type="button" @click="load">刷新</button>
        </div>
        <article v-for="clip in clips" :key="clip.id" class="clip-job-card">
          <div class="inline-row">
            <strong>{{ clip.title }}</strong>
            <span class="chip" :class="clip.status">{{ clip.status }}</span>
          </div>
          <p class="muted">{{ clip.lineup?.title || clip.source_filename || clip.source_url }}</p>
          <p v-if="clip.error" class="danger-text">{{ clip.error }}</p>
          <video v-if="clip.output_url" class="output-preview" :src="resolveAssetUrl(clip.output_url)" controls preload="metadata" />
          <div class="toolbar">
            <button type="button" class="ghost-button" @click="editClip(clip)">编辑</button>
            <button type="button" class="ghost-button" :disabled="renderingId === clip.id" @click="renderClip(clip)">
              {{ renderingId === clip.id ? '渲染中...' : '渲染' }}
            </button>
            <a v-if="clip.output_url" class="ghost-button" :href="resolveAssetUrl(clip.output_url)" download>下载</a>
            <button type="button" class="ghost-button danger" @click="removeClip(clip)">删除</button>
          </div>
        </article>
        <div v-if="!clips.length" class="empty-card">暂无剪辑任务</div>
      </aside>
    </div>

    <section v-else class="panel coming-panel">
      <div>
        <h2>击杀集锦</h2>
        <p class="muted">这里后续单独做击杀高光流程，不和道具教学片段混在一起。</p>
      </div>
      <div class="empty-card">
        计划方向：上传整局录屏，按击杀时间点打点，自动生成击杀前后片段、慢放、击杀字幕和片尾合集。
      </div>
    </section>
  </section>
</template>

<style scoped>
.clip-workspace {
  display: grid;
  grid-template-columns: 1fr;
  gap: 18px;
  align-items: start;
}

.module-tabs {
  display: inline-flex;
  gap: 6px;
  padding: 6px;
  margin-bottom: 18px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.035);
}

.module-tab {
  min-width: 112px;
  padding: 9px 14px;
  border: 0;
  border-radius: 8px;
  color: #aebbd0;
  background: transparent;
  cursor: pointer;
}

.module-tab.active {
  color: #10151f;
  background: #65d6ce;
}

.coming-panel {
  display: grid;
  gap: 16px;
}

.tuning-layout {
  display: grid;
  grid-template-columns: minmax(480px, 1.15fr) minmax(360px, 0.85fr);
  gap: 16px;
  align-items: start;
}

.preview-column {
  position: sticky;
  top: 14px;
  display: grid;
  gap: 12px;
  align-self: start;
}

.editor-title {
  justify-content: space-between;
  margin-bottom: 16px;
}

.upload-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 10px;
}

.lineup-summary,
.draft-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
  margin: 16px 0;
  padding: 12px 14px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.draft-bar {
  border-color: rgba(255, 122, 24, 0.28);
  background: rgba(255, 122, 24, 0.08);
}

.video-stage {
  margin: 0;
  aspect-ratio: 16 / 9;
  border-radius: 18px;
  overflow: hidden;
  background: #05080d;
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.video-stage video,
.output-preview {
  width: 100%;
  display: block;
  background: #05080d;
}

.video-focus-wrap {
  position: relative;
  width: 100%;
  height: 100%;
}

.video-stage video {
  height: 100%;
}

.focus-overlay {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.focus-box {
  position: absolute;
  min-width: 56px;
  min-height: 56px;
  cursor: move;
  pointer-events: auto;
  border: 2px solid rgba(255, 255, 255, 0.92);
  background: rgba(255, 122, 24, 0.1);
  box-shadow: 0 0 0 9999px rgba(5, 8, 13, 0.16), 0 0 18px rgba(255, 122, 24, 0.35);
}

.focus-label {
  position: absolute;
  left: 8px;
  top: 8px;
  padding: 4px 7px;
  border-radius: 6px;
  background: rgba(5, 8, 13, 0.72);
  color: #fff;
  font-size: 12px;
  letter-spacing: 0;
}

.focus-resize {
  position: absolute;
  right: -8px;
  bottom: -8px;
  width: 18px;
  height: 18px;
  cursor: nwse-resize;
  border-radius: 50%;
  border: 2px solid #05080d;
  background: #65d6ce;
  box-shadow: 0 0 0 3px rgba(101, 214, 206, 0.24);
}

.video-empty {
  height: 100%;
  display: grid;
  place-items: center;
  color: #97a7bb;
}

.range-panel {
  display: grid;
  gap: 10px;
  margin: 0;
  padding: 14px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.035);
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.range-header,
.range-footer,
.range-ticks {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.range-shell {
  position: relative;
  height: 42px;
}

.range-track {
  position: absolute;
  left: 0;
  right: 0;
  top: 17px;
  height: 8px;
  overflow: hidden;
  border-radius: 999px;
  background: rgba(151, 167, 187, 0.24);
}

.range-selection {
  position: absolute;
  top: 0;
  bottom: 0;
  left: var(--range-start);
  right: calc(100% - var(--range-end));
  border-radius: inherit;
  background: linear-gradient(90deg, #ff7a18, #65d6ce);
}

.range-playhead {
  position: absolute;
  top: -5px;
  bottom: -5px;
  left: var(--playhead);
  width: 2px;
  border-radius: 2px;
  background: #ffffff;
  box-shadow: 0 0 0 1px rgba(5, 8, 13, 0.45);
}

.range-input {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 42px;
  margin: 0;
  appearance: none;
  pointer-events: none;
  background: transparent;
}

.range-input::-webkit-slider-runnable-track {
  height: 42px;
  background: transparent;
}

.range-input::-webkit-slider-thumb {
  width: 18px;
  height: 18px;
  margin-top: 12px;
  appearance: none;
  pointer-events: auto;
  cursor: ew-resize;
  border-radius: 50%;
  border: 2px solid #05080d;
  background: #ff7a18;
  box-shadow: 0 0 0 3px rgba(255, 122, 24, 0.25);
}

.range-input::-moz-range-track {
  height: 42px;
  background: transparent;
}

.range-input::-moz-range-thumb {
  width: 18px;
  height: 18px;
  pointer-events: auto;
  cursor: ew-resize;
  border-radius: 50%;
  border: 2px solid #05080d;
  background: #ff7a18;
  box-shadow: 0 0 0 3px rgba(255, 122, 24, 0.25);
}

.range-input-end::-webkit-slider-thumb {
  background: #65d6ce;
  box-shadow: 0 0 0 3px rgba(101, 214, 206, 0.22);
}

.range-input-end::-moz-range-thumb {
  background: #65d6ce;
  box-shadow: 0 0 0 3px rgba(101, 214, 206, 0.22);
}

.range-ticks,
.range-footer {
  color: #97a7bb;
  font-size: 12px;
}

.quick-actions,
.timeline-actions,
.form-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.quick-actions {
  margin-bottom: 0;
}

.segment-editor {
  display: grid;
  gap: 14px;
  padding: 16px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.035);
  border: 1px solid rgba(255, 255, 255, 0.07);
}

.focus-panel {
  display: grid;
  gap: 12px;
  padding: 14px;
  border-radius: 14px;
  background: rgba(101, 214, 206, 0.055);
  border: 1px solid rgba(101, 214, 206, 0.16);
}

.focus-panel-header,
.focus-time-grid {
  display: grid;
  gap: 10px;
}

.focus-panel-header {
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
}

.focus-time-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.focus-time-grid label {
  display: grid;
  gap: 8px;
  color: #dbe7f4;
}

.focus-time-grid input,
.focus-panel input[type='range'] {
  width: 100%;
  accent-color: #65d6ce;
}

.compact-toolbar {
  gap: 6px;
}

.segment-time-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.segment-time-grid label {
  display: grid;
  gap: 6px;
}

.checkbox-row {
  display: flex !important;
  align-items: center;
  gap: 10px;
  min-height: 46px;
}

.checkbox-row input {
  width: 18px;
  height: 18px;
}

.timeline-list,
.job-panel {
  display: grid;
  gap: 12px;
}

.timeline-list {
  margin-top: 16px;
}

.timeline-item,
.clip-job-card {
  padding: 14px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.07);
}

.timeline-item {
  display: grid;
  grid-template-columns: 150px minmax(0, 1fr) auto;
  gap: 12px;
  align-items: center;
}

.timeline-item.editing {
  border-color: rgba(101, 214, 206, 0.55);
  background: rgba(101, 214, 206, 0.1);
  box-shadow: 0 0 0 1px rgba(101, 214, 206, 0.16) inset;
}

.timeline-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 6px;
}

.timecode {
  padding: 10px;
  border-radius: 12px;
  border: 1px solid rgba(255, 122, 24, 0.3);
  background: rgba(255, 122, 24, 0.12);
  color: #ffe0bf;
  cursor: pointer;
}

.timeline-item p,
.clip-job-card p {
  margin: 6px 0 0;
}

.form-actions {
  margin-top: 16px;
}

.danger-message,
.success-message,
.danger-text {
  padding: 10px 12px;
  border-radius: 12px;
}

.danger-message,
.danger-text {
  color: #ffc9c9;
  background: rgba(255, 75, 75, 0.12);
}

.success-message {
  color: #d8ffd6;
  background: rgba(73, 190, 96, 0.14);
}

.output-preview {
  margin-top: 10px;
  border-radius: 12px;
}

.chip.ready {
  background: rgba(73, 190, 96, 0.18);
  color: #d8ffd6;
}

.chip.failed {
  background: rgba(255, 75, 75, 0.14);
  color: #ffc9c9;
}

.chip.rendering {
  background: rgba(101, 214, 206, 0.16);
  color: #d6fffb;
}

@media (max-width: 1100px) {
  .clip-workspace,
  .tuning-layout,
  .timeline-item {
    grid-template-columns: 1fr;
  }

  .preview-column {
    position: static;
  }

  .upload-row,
  .segment-time-grid,
  .focus-time-grid,
  .focus-panel-header {
    grid-template-columns: 1fr;
  }
}
</style>

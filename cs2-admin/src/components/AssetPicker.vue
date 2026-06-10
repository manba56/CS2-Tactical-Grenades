<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';

import { api, resolveAssetUrl } from '../api';
import { useSessionStore } from '../stores/session';
import type { AdminAsset } from '../types';

const props = defineProps<{
  compact?: boolean;
}>();

const emit = defineEmits<{
  select: [url: string];
}>();

const session = useSessionStore();
const assets = ref<AdminAsset[]>([]);
const search = ref('');
const loading = ref(false);
const error = ref('');
const copiedUrl = ref('');

const visibleAssets = computed(() => assets.value.slice(0, props.compact ? 8 : 40));

async function load() {
  loading.value = true;
  error.value = '';
  try {
    assets.value = await api.assets(session.token, { q: search.value, media_type: 'image/' });
  } catch (err) {
    error.value = err instanceof Error ? err.message : '加载素材失败';
  } finally {
    loading.value = false;
  }
}

async function copyUrl(url: string) {
  await navigator.clipboard.writeText(url);
  copiedUrl.value = url;
  window.setTimeout(() => {
    if (copiedUrl.value === url) copiedUrl.value = '';
  }, 1200);
}

watch(search, () => {
  window.clearTimeout((load as any)._timer);
  (load as any)._timer = window.setTimeout(load, 250);
});

onMounted(load);
</script>

<template>
  <div class="asset-picker">
    <div class="asset-picker-toolbar">
      <input v-model="search" class="field" placeholder="搜索素材名称或 URL" />
      <button type="button" class="ghost-button" @click="load">刷新</button>
    </div>
    <p v-if="error" class="muted">{{ error }}</p>
    <p v-else-if="loading" class="muted">加载中...</p>
    <div v-else-if="visibleAssets.length" class="asset-picker-grid">
      <article v-for="asset in visibleAssets" :key="asset.id" class="asset-picker-card">
        <img :src="resolveAssetUrl(asset.url)" :alt="asset.original_name" />
        <div class="asset-picker-meta">
          <strong>{{ asset.original_name || asset.filename }}</strong>
          <span class="muted">{{ asset.url }}</span>
        </div>
        <div class="asset-picker-actions">
          <button type="button" class="ghost-button" @click="emit('select', asset.url)">回填</button>
          <button type="button" class="ghost-button" @click="copyUrl(asset.url)">
            {{ copiedUrl === asset.url ? '已复制' : '复制 URL' }}
          </button>
        </div>
      </article>
    </div>
    <p v-else class="muted">暂无素材</p>
  </div>
</template>

<style scoped>
.asset-picker {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.asset-picker-toolbar {
  display: flex;
  gap: 8px;
  align-items: center;
}
.asset-picker-toolbar .field {
  flex: 1;
}
.asset-picker-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 10px;
  max-height: 360px;
  overflow: auto;
}
.asset-picker-card {
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 8px;
  background: rgba(255,255,255,0.03);
  overflow: hidden;
}
.asset-picker-card img {
  display: block;
  width: 100%;
  aspect-ratio: 16 / 10;
  object-fit: cover;
  background: #111827;
}
.asset-picker-meta {
  padding: 8px;
  min-width: 0;
}
.asset-picker-meta strong,
.asset-picker-meta span {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.asset-picker-meta strong {
  font-size: 12px;
}
.asset-picker-meta span {
  font-size: 11px;
}
.asset-picker-actions {
  display: flex;
  gap: 6px;
  padding: 0 8px 8px;
}
.asset-picker-actions button {
  flex: 1;
  padding-inline: 8px;
}
</style>

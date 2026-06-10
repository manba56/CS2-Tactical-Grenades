<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';

import { api, resolveAssetUrl } from '../api';
import { useSessionStore } from '../stores/session';
import type { AdminAsset } from '../types';

const session = useSessionStore();
const assets = ref<AdminAsset[]>([]);
const file = ref<File | null>(null);
const error = ref('');
const search = ref('');
const copiedUrl = ref('');
const loading = ref(false);

const imageAssets = computed(() => assets.value.filter((asset) => asset.type.startsWith('image/')));

function onFileChange(event: Event) {
  const target = event.target as HTMLInputElement | null;
  file.value = target?.files?.[0] || null;
}

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

async function upload() {
  if (!file.value) return;
  try {
    await api.uploadAsset(file.value, session.token);
    file.value = null;
    await load();
  } catch (err) {
    error.value = err instanceof Error ? err.message : '上传失败';
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
  <div class="page-header">
    <h1>媒体资源</h1>
    <p class="muted">查看历史上传图片，复制 URL，或上传新素材后回填到表单。</p>
  </div>
  <div class="content-grid">
    <section class="panel">
      <h2>上传资源</h2>
      <div class="form-grid">
        <label class="full">
          选择图片
          <input type="file" class="field" accept="image/*" @change="onFileChange" />
        </label>
      </div>
      <p v-if="error" class="muted">{{ error }}</p>
      <button class="button" @click="upload" :disabled="!file">上传并加入素材库</button>
    </section>

    <section class="panel list-stack">
      <div class="inline-row" style="justify-content:space-between">
        <h2>历史素材</h2>
        <span class="chip">{{ imageAssets.length }} 个</span>
      </div>
      <div class="toolbar">
        <input v-model="search" class="field" placeholder="搜索素材名称或 URL" />
        <button class="ghost-button" @click="load">刷新</button>
      </div>
      <p v-if="loading" class="muted">加载中...</p>
      <article v-for="asset in imageAssets" :key="asset.id" class="list-item">
        <div class="inline-row">
          <strong>{{ asset.original_name || asset.filename }}</strong>
          <span class="chip">{{ asset.type }}</span>
        </div>
        <div class="muted">{{ asset.url }}</div>
        <img
          :src="resolveAssetUrl(asset.url)"
          :alt="asset.original_name || asset.filename"
          class="asset-preview"
        />
        <div class="toolbar">
          <button class="ghost-button" @click="copyUrl(asset.url)">
            {{ copiedUrl === asset.url ? '已复制' : '复制 URL' }}
          </button>
        </div>
      </article>
      <p v-if="!loading && imageAssets.length === 0" class="muted">暂无素材</p>
    </section>
  </div>
</template>

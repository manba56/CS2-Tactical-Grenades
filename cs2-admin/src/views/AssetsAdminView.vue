<script setup lang="ts">
import { ref } from 'vue';

import { api, resolveAssetUrl } from '../api';
import { useSessionStore } from '../stores/session';

const session = useSessionStore();
const uploaded = ref<Array<{ id: number; url: string; original_name: string; type: string }>>([]);
const file = ref<File | null>(null);
const error = ref('');

function onFileChange(event: Event) {
  const target = event.target as HTMLInputElement | null;
  file.value = target?.files?.[0] || null;
}

async function upload() {
  if (!file.value) return;
  try {
    const result = await api.uploadAsset(file.value, session.token);
    uploaded.value.unshift(result);
    file.value = null;
  } catch (err) {
    error.value = err instanceof Error ? err.message : '上传失败';
  }
}
</script>

<template>
  <div class="page-header">
    <h1>媒体资源</h1>
    <p class="muted">先提供最核心的图片上传能力，返回 URL 后可直接回填到表单。</p>
  </div>
  <div class="content-grid">
    <section class="panel">
      <h2>上传资源</h2>
      <div class="form-grid">
        <label class="full">
          选择图片
          <input type="file" class="field" @change="onFileChange" />
        </label>
      </div>
      <p v-if="error" class="muted">{{ error }}</p>
      <button class="button" @click="upload">上传并返回 URL</button>
    </section>

    <section class="panel list-stack">
      <article v-for="asset in uploaded" :key="asset.id" class="list-item">
        <div class="inline-row">
          <strong>{{ asset.original_name }}</strong>
          <span class="chip">{{ asset.type }}</span>
        </div>
        <div class="muted">{{ asset.url }}</div>
        <img
          v-if="asset.type.startsWith('image/')"
          :src="resolveAssetUrl(asset.url)"
          :alt="asset.original_name"
          class="asset-preview"
        />
      </article>
    </section>
  </div>
</template>

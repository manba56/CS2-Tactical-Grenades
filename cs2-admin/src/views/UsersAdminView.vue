<script setup lang="ts">
import { onMounted, ref } from 'vue';

import { api } from '../api';
import { useSessionStore } from '../stores/session';

const session = useSessionStore();
const users = ref<Array<{ id: number; username: string; email: string; favorites: number; recent: number }>>([]);

onMounted(async () => {
  users.value = await api.users(session.token);
});
</script>

<template>
  <div class="page-header">
    <h1>前台用户</h1>
    <p class="muted">查看注册用户的收藏与最近浏览活跃度。</p>
  </div>
  <section class="panel list-stack">
    <article v-for="user in users" :key="user.id" class="list-item">
      <div class="inline-row">
        <strong>{{ user.username }}</strong>
        <span class="chip">{{ user.email }}</span>
      </div>
      <div class="inline-row">
        <span class="chip">收藏 {{ user.favorites }}</span>
        <span class="chip">最近浏览 {{ user.recent }}</span>
      </div>
    </article>
  </section>
</template>

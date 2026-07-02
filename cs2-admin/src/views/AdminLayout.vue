<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';

import { api, API_BASE } from '../api';
import { useSessionStore } from '../stores/session';
import type { DashboardSummary } from '../types';

const session = useSessionStore();
const router = useRouter();
const apiBase = API_BASE;
const summary = ref<DashboardSummary | null>(null);

async function loadSummary() {
  summary.value = await api.dashboard(session.token);
}

function logout() {
  session.clearSession();
  router.push('/login');
}

onMounted(loadSummary);
</script>

<template>
  <div class="admin-shell">
    <aside class="admin-sidebar">
      <div class="admin-brand">
        <small>CS2 Tactics Admin</small>
        <strong>内容运营后台</strong>
        <span class="muted">当前账号：{{ session.user?.username }}</span>
      </div>

      <nav class="admin-nav">
        <router-link to="/maps">地图管理</router-link>
        <router-link to="/points">道具点位管理</router-link>
        <router-link to="/tactics">战术管理</router-link>
        <router-link to="/assets">媒体资源</router-link>
        <router-link to="/users">前台用户</router-link>
        <router-link to="/collections">战术合集</router-link>
        <router-link to="/clips">剪辑中心</router-link>
        <a :href="apiBase + '/api/admin/db/download'" download>数据库备份</a>
      </nav>

      <div v-if="summary" class="stat-grid">
        <div class="card"><strong>{{ summary.maps }}</strong><div class="muted">地图</div></div>
        <div class="card"><strong>{{ summary.tactics }}</strong><div class="muted">战术</div></div>
        <div class="card"><strong>{{ summary.lineups }}</strong><div class="muted">道具</div></div>
        <div class="card"><strong>{{ summary.users }}</strong><div class="muted">玩家</div></div>
      </div>

      <div style="margin-top: 18px">
        <button class="ghost-button" @click="logout">退出后台</button>
      </div>
    </aside>

    <main class="admin-main">
      <router-view />
    </main>
  </div>
</template>

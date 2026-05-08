<script setup lang="ts">
import { computed } from 'vue';
import { useRouter } from 'vue-router';

import { useSessionStore } from '../stores/session';

const router = useRouter();
const session = useSessionStore();

const navItems = computed(() => [
  { label: '首页', to: '/' },
  { label: '地图库', to: '/maps' },
  { label: '收藏夹', to: '/favorites' },
]);

function logout() {
  session.clearSession();
  router.push('/');
}
</script>

<template>
  <header class="top-nav">
    <router-link class="brand" to="/">
      <span class="brand-kicker">CSGO / CS2</span>
      <strong>Tactics Lab</strong>
    </router-link>

    <nav class="top-nav-links">
      <router-link v-for="item in navItems" :key="item.to" :to="item.to">
        {{ item.label }}
      </router-link>
    </nav>

    <div class="top-nav-user">
      <template v-if="session.user">
        <div class="user-chip">
          <span class="user-chip-label">已登录</span>
          <strong>{{ session.user.username }}</strong>
        </div>
        <button class="ghost-button" @click="logout">退出</button>
      </template>
      <router-link v-else class="primary-button small" to="/login">登录 / 注册</router-link>
    </div>
  </header>
</template>

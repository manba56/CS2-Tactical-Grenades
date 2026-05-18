<script setup lang="ts">
import { useRoute } from 'vue-router';
import { useSessionStore } from '../stores/session';

const route = useRoute();
const session = useSessionStore();

const tabs = [
  { label: '首页', to: '/', icon: 'home' },
  { label: '地图库', to: '/maps', icon: 'maps' },
  { label: '收藏夹', to: '/favorites', icon: 'fav' },
  { label: session.user ? '我的' : '登录', to: session.user ? '/favorites' : '/login', icon: 'user' },
];

function isActive(to: string) {
  if (to === '/') return route.path === '/';
  return route.path.startsWith(to);
}
</script>

<template>
  <nav class="bottom-nav">
    <router-link
      v-for="tab in tabs"
      :key="tab.to"
      :to="tab.to"
      class="bottom-tab"
      :class="{ active: isActive(tab.to) }"
    >
      <svg class="tab-icon" viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
        <template v-if="tab.icon === 'home'">
          <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
          <polyline points="9 22 9 12 15 12 15 22"/>
        </template>
        <template v-else-if="tab.icon === 'maps'">
          <polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6"/>
          <line x1="8" y1="2" x2="8" y2="18"/><line x1="16" y1="6" x2="16" y2="22"/>
        </template>
        <template v-else-if="tab.icon === 'fav'">
          <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>
        </template>
        <template v-else>
          <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>
        </template>
      </svg>
      <span>{{ tab.label }}</span>
    </router-link>
  </nav>
</template>

<style scoped>
.bottom-nav {
  display: none;
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: 30;
  background: rgba(7, 12, 19, 0.95);
  backdrop-filter: blur(20px);
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  padding: 6px 0 env(safe-area-inset-bottom, 8px);
  justify-content: space-around;
  align-items: flex-start;
}

.bottom-tab {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 3px;
  padding: 6px 12px;
  color: #666;
  text-decoration: none;
  font-size: 10px;
  font-weight: 500;
  transition: color 0.15s;
  -webkit-tap-highlight-color: transparent;
}

.bottom-tab.active {
  color: #ff7a18;
}

.tab-icon {
  transition: stroke 0.15s;
}

@media (max-width: 640px) {
  .bottom-nav {
    display: flex;
  }

  /* Push main content up so bottom nav doesn't overlap */
  :deep(.page-shell) {
    padding-bottom: 80px;
  }
}
</style>

<script setup lang="ts">
import { computed, ref } from 'vue';
import { useRouter } from 'vue-router';

import { useSessionStore } from '../stores/session';

const router = useRouter();
const session = useSessionStore();
const menuOpen = ref(false);

const navItems = computed(() => [
  { label: '首页', to: '/' },
  { label: '地图库', to: '/maps' },
  { label: '收藏夹', to: '/favorites' },
]);

function closeMenu() {
  menuOpen.value = false;
}

function logout() {
  session.clearSession();
  router.push('/');
  closeMenu();
}
</script>

<template>
  <header class="top-nav">
    <router-link class="brand" to="/" @click="closeMenu">
      <span class="brand-kicker">CSGO / CS2</span>
      <strong>Tactics Lab</strong>
    </router-link>

    <button
      class="hamburger"
      :class="{ open: menuOpen }"
      aria-label="菜单"
      @click="menuOpen = !menuOpen"
    >
      <span />
      <span />
      <span />
    </button>

    <div class="nav-menu" :class="{ open: menuOpen }">
      <nav class="top-nav-links">
        <router-link
          v-for="item in navItems"
          :key="item.to"
          :to="item.to"
          @click="closeMenu"
        >
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
        <router-link v-else class="primary-button small" to="/login" @click="closeMenu">
          登录 / 注册
        </router-link>
      </div>
    </div>
  </header>
</template>

<style scoped>
.hamburger {
  display: none;
  flex-direction: column;
  justify-content: center;
  gap: 5px;
  background: none;
  border: none;
  cursor: pointer;
  padding: 8px;
  z-index: 30;
}
.hamburger span {
  display: block;
  width: 22px;
  height: 2px;
  background: #f3f6fb;
  border-radius: 2px;
  transition: transform 0.2s, opacity 0.2s;
}
.hamburger.open span:nth-child(1) {
  transform: translateY(7px) rotate(45deg);
}
.hamburger.open span:nth-child(2) {
  opacity: 0;
}
.hamburger.open span:nth-child(3) {
  transform: translateY(-7px) rotate(-45deg);
}

.nav-menu {
  display: flex;
  align-items: center;
  gap: 16px;
}

@media (max-width: 640px) {
  .hamburger {
    display: flex;
  }

  .nav-menu {
    display: none;
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    flex-direction: column;
    justify-content: center;
    gap: 32px;
    background: rgba(7, 12, 19, 0.97);
    backdrop-filter: blur(24px);
    z-index: 25;
  }

  .nav-menu.open {
    display: flex;
  }

  .top-nav-links {
    flex-direction: column;
    align-items: center;
    gap: 20px;
  }

  .top-nav-links a {
    font-size: 1.4rem;
    padding: 10px 24px;
  }

  .top-nav-user {
    flex-direction: column;
    align-items: center;
    gap: 12px;
  }
}
</style>

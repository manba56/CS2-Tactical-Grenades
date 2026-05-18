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

    <!-- Desktop nav -->
    <div class="nav-menu desktop-only">
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
    </div>

    <!-- Hamburger -->
    <button
      class="hamburger"
      :class="{ open: menuOpen }"
      aria-label="菜单"
      @click="menuOpen = !menuOpen"
    >
      <span /><span /><span />
    </button>
  </header>

  <!-- Mobile overlay menu (teleported to avoid backdrop-filter clipping) -->
  <Teleport to="body">
    <div v-if="menuOpen" class="mobile-overlay" @click.self="closeMenu">
      <div class="mobile-menu">
        <nav class="mobile-nav-links">
          <router-link
            v-for="item in navItems" :key="item.to" :to="item.to"
            @click="closeMenu"
          >{{ item.label }}</router-link>
        </nav>
        <div class="mobile-nav-user">
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
    </div>
  </Teleport>
</template>

<style scoped>
/* Desktop nav */
.desktop-only {
  display: flex;
  align-items: center;
  gap: 16px;
}

/* Hamburger */
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
.hamburger.open span:nth-child(1) { transform: translateY(7px) rotate(45deg); }
.hamburger.open span:nth-child(2) { opacity: 0; }
.hamburger.open span:nth-child(3) { transform: translateY(-7px) rotate(-45deg); }

/* Mobile overlay (teleported to body) */
.mobile-overlay {
  display: none;
}

@media (max-width: 640px) {
  .desktop-only {
    display: none;
  }

  .hamburger {
    display: flex;
  }

  .mobile-overlay {
    display: flex;
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    z-index: 100;
    background: rgba(7, 12, 19, 0.97);
    backdrop-filter: blur(24px);
    -webkit-backdrop-filter: blur(24px);
    flex-direction: column;
    justify-content: center;
    align-items: center;
    gap: 32px;
    padding-top: env(safe-area-inset-top);
    padding-bottom: env(safe-area-inset-bottom);
  }

  .mobile-menu {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 32px;
  }

  .mobile-nav-links {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 20px;
  }

  .mobile-nav-links a {
    font-size: 1.4rem;
    padding: 10px 24px;
    color: #f3f6fb;
    text-decoration: none;
  }

  .mobile-nav-user {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 12px;
  }
}
</style>

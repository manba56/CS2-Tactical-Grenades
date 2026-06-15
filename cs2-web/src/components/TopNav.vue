<script setup lang="ts">
import { computed, ref } from 'vue';
import { useRouter } from 'vue-router';

import { useI18n } from '../composables/useI18n';
import { useSessionStore } from '../stores/session';

const router = useRouter();
const session = useSessionStore();
const menuOpen = ref(false);
const { nextLanguageLabel, t, toggleLanguage } = useI18n();

const navItems = computed(() => [
  { label: t('home'), to: '/' },
  { label: t('maps'), to: '/maps' },
  { label: t('favorites'), to: '/favorites' },
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
      <span class="brand-kicker">{{ t('brandKicker') }}</span>
      <strong>{{ t('brandName') }}</strong>
    </router-link>

    <!-- Desktop nav -->
    <div class="nav-menu desktop-only">
      <nav class="top-nav-links">
        <router-link v-for="item in navItems" :key="item.to" :to="item.to">
          {{ item.label }}
        </router-link>
      </nav>
      <div class="top-nav-user">
        <button
          class="language-button"
          type="button"
          :aria-label="t('languageToggle')"
          @click="toggleLanguage"
        >
          {{ nextLanguageLabel }}
        </button>
        <template v-if="session.user">
          <div class="user-chip">
            <span class="user-chip-label">{{ t('loggedIn') }}</span>
            <strong>{{ session.user.username }}</strong>
          </div>
          <button class="ghost-button" @click="logout">{{ t('logout') }}</button>
        </template>
        <router-link v-else class="primary-button small" to="/login">{{ t('loginRegister') }}</router-link>
      </div>
    </div>

    <!-- Hamburger -->
    <button
      class="hamburger"
      :class="{ open: menuOpen }"
      :aria-label="t('menu')"
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
          <button
            class="language-button"
            type="button"
            :aria-label="t('languageToggle')"
            @click="toggleLanguage"
          >
            {{ nextLanguageLabel }}
          </button>
          <template v-if="session.user">
            <div class="user-chip">
              <span class="user-chip-label">{{ t('loggedIn') }}</span>
              <strong>{{ session.user.username }}</strong>
            </div>
            <button class="ghost-button" @click="logout">{{ t('logout') }}</button>
          </template>
          <router-link v-else class="primary-button small" to="/login" @click="closeMenu">
            {{ t('loginRegister') }}
          </router-link>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.desktop-only { display: flex; align-items: center; gap: 16px; }

.language-button {
  min-width: 44px;
  min-height: 30px;
  border: 1px solid rgba(255,255,255,0.12);
  border-radius: 999px;
  background: rgba(255,255,255,0.04);
  color: #f4f7fb;
  font-size: 0.74rem;
  font-weight: 800;
  cursor: pointer;
  transition: border-color 0.15s, color 0.15s, background 0.15s;
}

.language-button:hover {
  border-color: rgba(255,122,24,0.45);
  background: rgba(255,122,24,0.12);
  color: #ffbd82;
}

.hamburger { display: none; flex-direction: column; justify-content: center; gap: 5px; background: none; border: none; cursor: pointer; padding: 8px; z-index: 30; }
.hamburger span { display: block; width: 22px; height: 2px; background: #f3f6fb; border-radius: 2px; transition: transform 0.2s, opacity 0.2s; }
.hamburger.open span:nth-child(1) { transform: translateY(7px) rotate(45deg); }
.hamburger.open span:nth-child(2) { opacity: 0; }
.hamburger.open span:nth-child(3) { transform: translateY(-7px) rotate(-45deg); }

.mobile-overlay { display: none; }

@media (max-width: 640px) {
  .desktop-only { display: none; }
  .hamburger { display: flex; }
  .mobile-overlay {
    display: flex; position: fixed; top: 0; left: 0; right: 0; bottom: 0; z-index: 100;
    background: rgba(7,12,19,0.97); backdrop-filter: blur(24px); -webkit-backdrop-filter: blur(24px);
    flex-direction: column; justify-content: center; align-items: center; gap: 32px;
    padding-top: env(safe-area-inset-top); padding-bottom: env(safe-area-inset-bottom);
  }
  .mobile-menu { display: flex; flex-direction: column; align-items: center; gap: 32px; }
  .mobile-nav-links { display: flex; flex-direction: column; align-items: center; gap: 20px; }
  .mobile-nav-links a { font-size: 1.4rem; padding: 10px 24px; color: #f3f6fb; text-decoration: none; }
  .mobile-nav-user { display: flex; flex-direction: column; align-items: center; gap: 12px; }
  .language-button { min-width: 58px; min-height: 34px; }
}
</style>

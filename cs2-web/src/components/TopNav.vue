<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue';
import { useRouter } from 'vue-router';

import { useI18n } from '../composables/useI18n';
import type { Language } from '../composables/useI18n';
import { useSessionStore } from '../stores/session';

const router = useRouter();
const session = useSessionStore();
const menuOpen = ref(false);
const languageMenuOpen = ref(false);
const {
  currentLanguageLabel,
  language,
  languageOptions,
  selectLanguage,
  t,
} = useI18n();

const navItems = computed(() => [
  { label: t('home'), to: '/' },
  { label: t('maps'), to: '/maps' },
  { label: t('favorites'), to: '/favorites' },
]);

function closeMenu() {
  menuOpen.value = false;
  languageMenuOpen.value = false;
}

function toggleMobileMenu() {
  menuOpen.value = !menuOpen.value;
  languageMenuOpen.value = false;
}

function logout() {
  session.clearSession();
  router.push('/');
  closeMenu();
}

function toggleLanguageMenu() {
  languageMenuOpen.value = !languageMenuOpen.value;
}

function chooseLanguage(nextLanguage: Language) {
  selectLanguage(nextLanguage);
  languageMenuOpen.value = false;
}

function closeLanguageMenuOnOutsideClick(event: MouseEvent) {
  const target = event.target;
  if (!(target instanceof Element)) return;
  if (!target.closest('.language-picker')) {
    languageMenuOpen.value = false;
  }
}

function closeLanguageMenuOnEscape(event: KeyboardEvent) {
  if (event.key === 'Escape') {
    languageMenuOpen.value = false;
  }
}

onMounted(() => {
  document.addEventListener('click', closeLanguageMenuOnOutsideClick);
  document.addEventListener('keydown', closeLanguageMenuOnEscape);
});

onUnmounted(() => {
  document.removeEventListener('click', closeLanguageMenuOnOutsideClick);
  document.removeEventListener('keydown', closeLanguageMenuOnEscape);
});
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
        <div class="language-picker">
          <button
            class="language-button"
            type="button"
            :aria-label="t('languageToggle')"
            :title="t('languageToggle')"
            :aria-expanded="languageMenuOpen"
            aria-haspopup="menu"
            @click="toggleLanguageMenu"
          >
            <svg class="language-icon" viewBox="0 0 24 24" aria-hidden="true">
              <circle cx="12" cy="12" r="9" />
              <path d="M3 12h18" />
              <path d="M12 3c2.4 2.5 3.6 5.5 3.6 9s-1.2 6.5-3.6 9" />
              <path d="M12 3c-2.4 2.5-3.6 5.5-3.6 9s1.2 6.5 3.6 9" />
            </svg>
            <span>{{ currentLanguageLabel }}</span>
          </button>
          <div v-if="languageMenuOpen" class="language-menu" role="menu">
            <button
              v-for="option in languageOptions"
              :key="option.value"
              type="button"
              class="language-option"
              :class="{ active: language === option.value }"
              role="menuitemradio"
              :aria-checked="language === option.value"
              @click="chooseLanguage(option.value)"
            >
              <span>{{ option.label }}</span>
              <span v-if="language === option.value" class="language-check">✓</span>
            </button>
          </div>
        </div>
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
      @click="toggleMobileMenu"
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
          <div class="language-picker mobile-language-picker">
            <button
              class="language-button"
              type="button"
              :aria-label="t('languageToggle')"
              :title="t('languageToggle')"
              :aria-expanded="languageMenuOpen"
              aria-haspopup="menu"
              @click="toggleLanguageMenu"
            >
              <svg class="language-icon" viewBox="0 0 24 24" aria-hidden="true">
                <circle cx="12" cy="12" r="9" />
                <path d="M3 12h18" />
                <path d="M12 3c2.4 2.5 3.6 5.5 3.6 9s-1.2 6.5-3.6 9" />
                <path d="M12 3c-2.4 2.5-3.6 5.5-3.6 9s1.2 6.5 3.6 9" />
              </svg>
              <span>{{ currentLanguageLabel }}</span>
            </button>
            <div v-if="languageMenuOpen" class="language-menu mobile-language-menu" role="menu">
              <button
                v-for="option in languageOptions"
                :key="option.value"
                type="button"
                class="language-option"
                :class="{ active: language === option.value }"
                role="menuitemradio"
                :aria-checked="language === option.value"
                @click="chooseLanguage(option.value)"
              >
                <span>{{ option.label }}</span>
                <span v-if="language === option.value" class="language-check">✓</span>
              </button>
            </div>
          </div>
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

.language-picker {
  position: relative;
  flex: 0 0 auto;
}

.language-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  min-width: 68px;
  min-height: 32px;
  border: 1px solid rgba(255,255,255,0.12);
  border-radius: 999px;
  background: rgba(255,255,255,0.04);
  color: #f4f7fb;
  padding: 0 10px;
  font-size: 0.75rem;
  font-weight: 800;
  cursor: pointer;
  transition: border-color 0.15s, color 0.15s, background 0.15s;
}

.language-button:hover {
  border-color: rgba(255,122,24,0.45);
  background: rgba(255,122,24,0.12);
  color: #ffbd82;
}

.language-icon {
  width: 15px;
  height: 15px;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.8;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.language-menu {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  z-index: 80;
  display: grid;
  min-width: 132px;
  overflow: hidden;
  border: 1px solid rgba(255,255,255,0.12);
  border-radius: 8px;
  background: rgba(8,14,23,0.96);
  box-shadow: 0 18px 42px rgba(0,0,0,0.34);
  backdrop-filter: blur(18px);
  -webkit-backdrop-filter: blur(18px);
}

.language-option {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-height: 36px;
  border: 0;
  background: transparent;
  color: #dce6f4;
  padding: 0 12px;
  font-size: 0.8rem;
  text-align: left;
  cursor: pointer;
}

.language-option:hover,
.language-option.active {
  background: rgba(255,122,24,0.12);
  color: #ffbd82;
}

.language-check {
  color: #8de8be;
  font-weight: 900;
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
  .mobile-language-picker { display: grid; justify-items: center; }
  .language-button { min-width: 86px; min-height: 36px; }
  .mobile-language-menu {
    position: static;
    margin-top: 10px;
    min-width: 150px;
  }
}
</style>

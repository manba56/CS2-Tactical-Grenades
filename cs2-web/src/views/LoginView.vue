<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import { api } from '../api';
import { useHead } from '../composables/useHead';
import { useI18n } from '../composables/useI18n';
import { useSessionStore } from '../stores/session';
import { syncLocalPersonalData } from '../utils/personalPlaybook';

const route = useRoute();
const router = useRouter();
const { t } = useI18n();

onMounted(() => {
  useHead(t('loginRegister'), t('loginHeroTitle'));
});
const session = useSessionStore();

const mode = ref<'login' | 'register'>('login');
const usernameOrEmail = ref('demo');
const username = ref('');
const email = ref('');
const password = ref('demo123');
const error = ref('');
const loading = ref(false);

async function submit() {
  loading.value = true;
  error.value = '';
  try {
    const result =
      mode.value === 'login'
        ? await api.login(usernameOrEmail.value, password.value)
        : await api.register(username.value, email.value, password.value);
    session.setSession(result.token, result.user);
    await syncLocalPersonalData(result.token);
    router.push((route.query.redirect as string) || '/favorites');
  } catch (err) {
    error.value = err instanceof Error ? err.message : t('submitFailed');
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <section class="two-column">
    <div class="hero-card">
      <div class="kicker">{{ t('accessTacticShelf') }}</div>
      <h1 class="hero-title">{{ t('loginHeroTitle') }}</h1>
      <p class="hero-subtitle">
        {{ t('loginHeroSubtitle') }}
        <span class="accent">demo / demo123</span>。
      </p>
    </div>

    <form class="form-card" @submit.prevent="submit">
      <div class="section-heading">
        <h2>{{ mode === 'login' ? t('playerLogin') : t('createAccount') }}</h2>
        <button class="ghost-button" type="button" @click="mode = mode === 'login' ? 'register' : 'login'">
          {{ mode === 'login' ? t('switchRegister') : t('switchLogin') }}
        </button>
      </div>

      <div class="filter-grid">
        <label v-if="mode === 'login'">
          {{ t('usernameOrEmail') }}
          <input v-model="usernameOrEmail" class="field" placeholder="demo" />
        </label>
        <label v-else>
          {{ t('username') }}
          <input v-model="username" class="field" :placeholder="t('usernamePlaceholder')" />
        </label>
        <label v-if="mode === 'register'">
          {{ t('email') }}
          <input v-model="email" class="field" placeholder="name@example.com" />
        </label>
        <label>
          {{ t('password') }}
          <input v-model="password" type="password" class="field" :placeholder="t('passwordPlaceholder')" />
        </label>
      </div>

      <p v-if="error" class="danger">{{ error }}</p>
      <button class="primary-button" data-testid="login-submit" :disabled="loading">
        {{ loading ? t('submitting') : mode === 'login' ? t('login') : t('registerAndEnter') }}
      </button>
    </form>
  </section>
</template>

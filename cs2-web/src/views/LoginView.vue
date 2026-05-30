<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import { api } from '../api';
import { useHead } from '../composables/useHead';
import { useSessionStore } from '../stores/session';

const route = useRoute();
const router = useRouter();

onMounted(() => {
  useHead('登录/注册', '登录或注册CS2 Tactics Lab账号');
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
    router.push((route.query.redirect as string) || '/favorites');
  } catch (err) {
    error.value = err instanceof Error ? err.message : '提交失败';
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <section class="two-column">
    <div class="hero-card">
      <div class="kicker">Access Tactic Shelf</div>
      <h1 class="hero-title">登录后保存你的战术手册。</h1>
      <p class="hero-subtitle">
        首版账号系统只做最必要的能力：登录、收藏、最近浏览。默认演示账号是
        <span class="accent">demo / demo123</span>。
      </p>
    </div>

    <form class="form-card" @submit.prevent="submit">
      <div class="section-heading">
        <h2>{{ mode === 'login' ? '玩家登录' : '创建账号' }}</h2>
        <button class="ghost-button" type="button" @click="mode = mode === 'login' ? 'register' : 'login'">
          {{ mode === 'login' ? '切换注册' : '切换登录' }}
        </button>
      </div>

      <div class="filter-grid">
        <label v-if="mode === 'login'">
          用户名或邮箱
          <input v-model="usernameOrEmail" class="field" placeholder="demo" />
        </label>
        <label v-else>
          用户名
          <input v-model="username" class="field" placeholder="输入用户名" />
        </label>
        <label v-if="mode === 'register'">
          邮箱
          <input v-model="email" class="field" placeholder="name@example.com" />
        </label>
        <label>
          密码
          <input v-model="password" type="password" class="field" placeholder="至少 6 位" />
        </label>
      </div>

      <p v-if="error" class="danger">{{ error }}</p>
      <button class="primary-button" :disabled="loading">
        {{ loading ? '提交中...' : mode === 'login' ? '登录' : '注册并进入' }}
      </button>
    </form>
  </section>
</template>

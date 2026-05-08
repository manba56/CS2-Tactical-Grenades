<script setup lang="ts">
import { ref } from 'vue';
import { useRouter } from 'vue-router';

import { api } from '../api';
import { useSessionStore } from '../stores/session';

const router = useRouter();
const session = useSessionStore();
const username = ref('admin');
const password = ref('admin123');
const error = ref('');
const loading = ref(false);

async function submit() {
  loading.value = true;
  error.value = '';
  try {
    const result = await api.login(username.value, password.value);
    session.setSession(result.token, result.user);
    router.push('/admin/maps');
  } catch (err) {
    error.value = err instanceof Error ? err.message : '登录失败';
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <div class="login-shell">
    <form class="login-card" @submit.prevent="submit">
      <div class="page-header">
        <span class="muted">Demo 后台账号：admin / admin123</span>
        <h1>CS2 Tactics Admin</h1>
      </div>
      <div class="form-grid">
        <label class="full">
          账号
          <input v-model="username" class="field" />
        </label>
        <label class="full">
          密码
          <input v-model="password" type="password" class="field" />
        </label>
      </div>
      <p v-if="error" class="muted">{{ error }}</p>
      <button class="button" :disabled="loading">{{ loading ? '登录中...' : '进入后台' }}</button>
    </form>
  </div>
</template>

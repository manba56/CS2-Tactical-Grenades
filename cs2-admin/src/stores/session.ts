import { defineStore } from 'pinia';
import { computed, ref } from 'vue';

import type { AdminSessionUser } from '../types';

const TOKEN_KEY = 'cs2-admin-token';
const USER_KEY = 'cs2-admin-user';

export const useSessionStore = defineStore('adminSession', () => {
  const token = ref(localStorage.getItem(TOKEN_KEY) || '');
  const user = ref<AdminSessionUser | null>(
    (() => {
      const raw = localStorage.getItem(USER_KEY);
      return raw ? (JSON.parse(raw) as AdminSessionUser) : null;
    })(),
  );

  const isAuthenticated = computed(() => Boolean(token.value));

  function setSession(nextToken: string, nextUser: AdminSessionUser) {
    token.value = nextToken;
    user.value = nextUser;
    localStorage.setItem(TOKEN_KEY, nextToken);
    localStorage.setItem(USER_KEY, JSON.stringify(nextUser));
  }

  function clearSession() {
    token.value = '';
    user.value = null;
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  }

  return {
    token,
    user,
    isAuthenticated,
    setSession,
    clearSession,
  };
});

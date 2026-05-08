import { defineStore } from 'pinia';
import { computed, ref } from 'vue';

import type { SessionUser } from '../types';

const TOKEN_KEY = 'cs2-web-token';
const USER_KEY = 'cs2-web-user';

export const useSessionStore = defineStore('session', () => {
  const token = ref<string>(localStorage.getItem(TOKEN_KEY) || '');
  const user = ref<SessionUser | null>(
    (() => {
      const raw = localStorage.getItem(USER_KEY);
      return raw ? (JSON.parse(raw) as SessionUser) : null;
    })(),
  );

  const isAuthenticated = computed(() => Boolean(token.value));

  function setSession(nextToken: string, nextUser: SessionUser) {
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

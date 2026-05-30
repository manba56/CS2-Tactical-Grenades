import { createRouter, createWebHistory } from 'vue-router';

import { useSessionStore } from './stores/session';

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: () => import('./views/HomeView.vue') },
    { path: '/maps', component: () => import('./views/MapsView.vue') },
    { path: '/maps/:mapSlug', component: () => import('./views/MapDetailView.vue') },
    { path: '/tactics/:tacticSlug', component: () => import('./views/TacticDetailView.vue') },
    { path: '/favorites', component: () => import('./views/FavoritesView.vue'), meta: { requiresAuth: true } },
    { path: '/collections/:slug', component: () => import('./views/CollectionDetailView.vue') },
    { path: '/login', component: () => import('./views/LoginView.vue') },
    { path: '/:pathMatch(.*)*', component: () => import('./views/NotFoundView.vue') },
  ],
  scrollBehavior() {
    return { top: 0 };
  },
});

router.beforeEach((to) => {
  const session = useSessionStore();
  if (to.meta.requiresAuth && !session.isAuthenticated) {
    return `/login?redirect=${encodeURIComponent(to.fullPath)}`;
  }
  return true;
});

export default router;

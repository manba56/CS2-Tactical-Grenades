import { createRouter, createWebHistory } from 'vue-router';

import { useSessionStore } from './stores/session';

const router = createRouter({
  history: createWebHistory('/admin/'),
  routes: [
    { path: '/login', component: () => import('./views/LoginView.vue') },
    {
      path: '/',
      component: () => import('./views/AdminLayout.vue'),
      meta: { requiresAuth: true },
      children: [
        { path: '', redirect: '/maps' },
        { path: '/maps', component: () => import('./views/MapsAdminView.vue') },
        { path: '/points', component: () => import('./views/PointsAdminView.vue') },
        { path: '/lineups', component: () => import('./views/LineupsAdminView.vue') },
        { path: '/tactics', component: () => import('./views/TacticsAdminView.vue') },
        { path: '/assets', component: () => import('./views/AssetsAdminView.vue') },
        { path: '/users', component: () => import('./views/UsersAdminView.vue') },
      ],
    },
  ],
});

router.beforeEach((to) => {
  const session = useSessionStore();
  if (to.meta.requiresAuth && !session.isAuthenticated) {
    return '/login';
  }
  return true;
});

export default router;

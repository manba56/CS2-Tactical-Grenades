import { createRouter, createWebHistory } from 'vue-router';

import { useSessionStore } from './stores/session';

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', component: () => import('./views/LoginView.vue') },
    {
      path: '/',
      component: () => import('./views/AdminLayout.vue'),
      meta: { requiresAuth: true },
      children: [
        { path: '', redirect: '/admin/maps' },
        { path: '/admin/maps', component: () => import('./views/MapsAdminView.vue') },
        { path: '/admin/points', component: () => import('./views/PointsAdminView.vue') },
        { path: '/admin/lineups', component: () => import('./views/LineupsAdminView.vue') },
        { path: '/admin/tactics', component: () => import('./views/TacticsAdminView.vue') },
        { path: '/admin/assets', component: () => import('./views/AssetsAdminView.vue') },
        { path: '/admin/users', component: () => import('./views/UsersAdminView.vue') },
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

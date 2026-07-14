import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'Login',
      component: () => import('@/views/LoginView.vue'),
      meta: { guest: true },
    },
    {
      path: '/register',
      name: 'Register',
      component: () => import('@/views/RegisterView.vue'),
      meta: { guest: true },
    },
    {
      path: '/',
      component: () => import('@/components/layout/MainLayout.vue'),
      meta: { requiresAuth: true },
      children: [
        { path: '', name: 'Home', component: () => import('@/views/HomeView.vue') },
        { path: 'category/:id?', name: 'Category', component: () => import('@/views/CategoryView.vue') },
        { path: 'document/:id', name: 'Document', component: () => import('@/views/DocumentView.vue') },
        { path: 'search', name: 'Search', component: () => import('@/views/SearchView.vue') },
        { path: 'personal', name: 'Personal', component: () => import('@/views/PersonalView.vue') },
      ],
    },
    {
      path: '/admin',
      component: () => import('@/views/admin/AdminLayout.vue'),
      meta: { requiresAuth: true, roles: ['super_admin', 'dept_admin'] },
      children: [
        { path: '', redirect: '/admin/documents' },
        { path: 'documents', name: 'AdminDocuments', component: () => import('@/views/admin/DocumentManage.vue') },
        { path: 'categories', name: 'AdminCategories', component: () => import('@/views/admin/CategoryManage.vue') },
        { path: 'users', name: 'AdminUsers', component: () => import('@/views/admin/UserManage.vue') },
        { path: 'settings', name: 'AdminSettings', component: () => import('@/views/admin/SystemSettings.vue') },
      ],
    },
    { path: '/:pathMatch(.*)*', name: 'NotFound', component: () => import('@/views/NotFoundView.vue') },
  ],
})

router.beforeEach((to, _from, next) => {
  const auth = useAuthStore()

  // Redirect unauthenticated users to login
  if (to.meta.requiresAuth && !auth.isLoggedIn) return next('/login')

  // Redirect already logged-in users away from guest-only pages
  if (to.meta.guest && auth.isLoggedIn) return next('/')

  // Check role-based access for admin routes
  const allowedRoles = to.meta.roles as string[] | undefined
  if (allowedRoles && allowedRoles.length > 0) {
    const userRole = auth.user?.role
    if (!userRole || !allowedRoles.includes(userRole)) {
      return next('/')
    }
  }

  next()
})

export default router

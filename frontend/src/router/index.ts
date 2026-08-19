import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

import { ref } from 'vue'
const meLoaded = ref(false)

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
      path: '/',
      component: () => import('@/components/layout/MainLayout.vue'),
      meta: { requiresAuth: true },
      children: [
        { path: '', name: 'Home', component: () => import('@/views/HomeView.vue') },
        { path: 'category/:id?', name: 'Category', component: () => import('@/views/CategoryView.vue') },
        { path: 'document/:id', name: 'Document', component: () => import('@/views/DocumentView.vue') },
        { path: 'search', name: 'Search', component: () => import('@/views/SearchView.vue') },
        { path: 'personal', name: 'Personal', component: () => import('@/views/PersonalView.vue') },
        { path: 'contact/:id?', name: 'Contact', component: () => import('@/views/ContactView.vue') },
        { path: 'cosmetics/ingredients', name: 'IngredientSearch', component: () => import('@/views/cosmetics/IngredientSearchView.vue') },
        { path: 'cosmetics/knowledge-graph', name: 'KnowledgeGraph', component: () => import('@/views/cosmetics/KnowledgeGraphView.vue') },
        { path: 'device/knowledge-graph', name: 'DeviceKnowledgeGraph', component: () => import('@/views/device/DeviceKnowledgeGraphView.vue') },
        { path: 'files', name: 'FileStorage', component: () => import('@/views/FileStorageView.vue') },
        { path: 'files/preview/:id', name: 'FilePreview', component: () => import('@/views/FilePreviewView.vue') },
        { path: 'oa', name: 'OA', component: () => import('@/views/OAView.vue') },
      ],
    },
    {
      path: '/admin',
      component: () => import('@/views/admin/AdminLayout.vue'),
      meta: { requiresAuth: true, roles: ['super_admin', 'dept_admin'] },
      children: [
        { path: '', name: 'AdminDashboard', component: () => import('@/views/admin/DashboardView.vue') },
        { path: 'documents', name: 'AdminDocuments', component: () => import('@/views/admin/DocumentManage.vue') },
        { path: 'categories', name: 'AdminCategories', component: () => import('@/views/admin/CategoryManage.vue') },
        { path: 'users', name: 'AdminUsers', component: () => import('@/views/admin/UserManage.vue') },
        { path: 'settings', name: 'AdminSettings', component: () => import('@/views/admin/SystemSettings.vue') },
        { path: 'activity', name: 'AdminActivity', component: () => import('@/views/admin/ActivityView.vue') },
        { path: 'ops', name: 'AdminOpsTasks', component: () => import('@/views/admin/OpsTasksView.vue'), meta: { roles: ['super_admin'] } },
        { path: 'ai', name: 'AdminAIKnowledge', component: () => import('@/views/admin/AIKnowledgeView.vue'), meta: { roles: ['super_admin'] } },
      ],
    },
    { path: '/:pathMatch(.*)*', name: 'NotFound', component: () => import('@/views/NotFoundView.vue') },
  ],
})

router.beforeEach(async (to, _from, next) => {
  const auth = useAuthStore()

  // Redirect unauthenticated users to login
  if (to.meta.requiresAuth && !auth.isLoggedIn) return next('/login')

  // Redirect already logged-in users away from guest-only pages
  if (to.meta.guest && auth.isLoggedIn) return next('/')

  // Check role-based access for admin routes
  const allowedRoles = to.meta.roles as string[] | undefined
  if (allowedRoles && allowedRoles.length > 0) {
    // Fetch user profile if not loaded (e.g. direct URL navigation)
    if (!auth.user) {
      try { await auth.fetchMe() } catch {}
    }
    const userRole = auth.user?.role
    if (!userRole || !allowedRoles.includes(userRole)) {
      return next('/')
    }
  }

  next()
})

export default router

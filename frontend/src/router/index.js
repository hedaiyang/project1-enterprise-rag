import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/login', component: () => import('../views/Login.vue'), meta: { title: '登录', public: true } },
  { path: '/', redirect: '/dashboard' },
  { path: '/dashboard', component: () => import('../views/Dashboard.vue'), meta: { title: '系统概览', icon: 'DataAnalysis' } },
  { path: '/chat', component: () => import('../views/Chat.vue'), meta: { title: '智能问答', icon: 'ChatDotRound' } },
  { path: '/documents', component: () => import('../views/Documents.vue'), meta: { title: '文档管理', icon: 'UploadFilled' } },
]

const router = createRouter({ history: createWebHistory(), routes })

// 路由守卫：没登录跳登录页（登录页除外）
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')
  if (to.meta.public) {
    next()
  } else if (!token) {
    next('/login')
  } else {
    next()
  }
})

export default router

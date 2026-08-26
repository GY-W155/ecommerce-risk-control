import { createRouter, createWebHistory } from 'vue-router'
import Layout from '../components/Layout.vue'

const routes = [
  {
    path: '/',
    component: Layout,
    redirect: '/dashboard',
    children: [
      { path: 'dashboard', name: 'dashboard', component: () => import('../views/Dashboard.vue'), meta: { title: '运营看板' } },
      { path: 'check', name: 'check', component: () => import('../views/Check.vue'), meta: { title: '风险检查' } },
      { path: 'rules', name: 'rules', component: () => import('../views/Rules.vue'), meta: { title: '规则管理' } },
      { path: 'cases', name: 'cases', component: () => import('../views/Cases.vue'), meta: { title: '案件管理' } },
      { path: 'cases/:id', name: 'caseDetail', component: () => import('../views/CaseDetail.vue'), meta: { title: '案件详情' } },
      { path: 'blacklists', name: 'blacklists', component: () => import('../views/Blacklists.vue'), meta: { title: '黑名单' } },
      { path: 'profile', name: 'profile', component: () => import('../views/Profile.vue'), meta: { title: '用户画像' } },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.afterEach((to) => {
  document.title = to.meta?.title ? `${to.meta.title} - 电商风控中心` : '电商风控中心'
})

export default router

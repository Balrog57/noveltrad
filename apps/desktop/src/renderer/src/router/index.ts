import { createRouter, createWebHashHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'

const routes = [
  { path: '/', name: 'home', component: HomeView },
  {
    path: '/project/:id',
    name: 'project',
    component: () => import('../views/ProjectView.vue')
  },
  {
    path: '/project/:id/chapters',
    name: 'chapters',
    component: () => import('../views/ChaptersView.vue')
  },
  { path: '/settings', name: 'settings', component: () => import('../views/SettingsView.vue') }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes
})

export default router

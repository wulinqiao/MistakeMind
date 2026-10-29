import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import PracticeView from '../views/PracticeView.vue'
import DiagnoseView from '../views/DiagnoseView.vue'
import HistoryView from '../views/HistoryView.vue'
import ProfileView from '../views/ProfileView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'home', component: HomeView },
    { path: '/practice', name: 'practice', component: PracticeView },
    { path: '/diagnose', name: 'diagnose', component: DiagnoseView },
    { path: '/history', name: 'history', component: HistoryView },
    { path: '/profile', name: 'profile', component: ProfileView },
  ],
})

export default router

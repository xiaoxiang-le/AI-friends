import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/user.js'
import HomepageIndex from "@/views/homepage/HomepageIndex.vue"
import FriendIndex from "@/views/friend/FriendIndex.vue"
import CreateIndex from "@/views/create/CreateIndex.vue"
import LoginIndex from "@/views/user/account/LoginIndex.vue"
import RegisterIndex from "@/views/user/account/RegisterIndex.vue"
import SpaceIndex from "@/views/user/space/SpaceIndex.vue"
import ProfileIndex from "@/views/user/profile/ProfileIndex.vue"
import NotFoundIndex from "@/views/error/NotFoundIndex.vue"
import UpdateCharacter from "@/views/create/character/UpdateCharacter.vue";

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', component: HomepageIndex, name: 'homepage-index', meta: { needLogin: false } },
    { path: '/friend/', component: FriendIndex, name: 'friend-index', meta: { needLogin: true } },
    { path: '/create/', component: CreateIndex, name: 'create-index', meta: { needLogin: true } },
    { path: '/create/character/update/:character_id/', component: UpdateCharacter, name: 'update-character', meta: { needLogin: true } },
    { path: '/login/', component: LoginIndex, name: 'user-account-login-index', meta: { needLogin: false } },
    { path: '/register/', component: RegisterIndex, name: 'user-account-register-index', meta: { needLogin: false } },
    { path: '/user/space/:user_id/', component: SpaceIndex, name: 'user-space-index', meta: { needLogin: true } },
    { path: '/user/profile/', component: ProfileIndex, name: 'user-profile-index', meta: { needLogin: true } },
    { path: '/:pathMatch(.*)*', component: NotFoundIndex, name: 'not-found' },
  ],
})

router.beforeEach((to, from, next) => {
  const user = useUserStore()

  const needLogin = to.meta.needLogin

  // 刷新页面时，先等 App.vue 里 get_user_info / 刷新 token 的流程跑完
  // 只有在已经确认拉取过用户信息之后，才根据 isLogin 做跳转判断
  if (!user.hasPulledUserInfo) {
    return next()
  }

  // 需要登录的页面且当前未登录，跳转到登录页，并记录原目标地址
  if (needLogin && !user.isLogin()) {
    return next({
      name: 'user-account-login-index',
      query: { redirect: to.fullPath },
    })
  }

  // 已登录用户访问登录/注册页面时，直接跳到首页
  if (user.isLogin() && (to.name === 'user-account-login-index' || to.name === 'user-account-register-index')) {
    return next({ name: 'homepage-index' })
  }

  return next()
})

export default router

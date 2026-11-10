<template>
  <el-container v-if="$route.path !== '/login'" style="height: 100vh">
    <!-- 侧边栏 -->
    <el-aside width="220px" style="background:#1f2937">
      <div style="padding:20px;text-align:center;color:#fff;font-size:16px;font-weight:bold;border-bottom:1px solid #374151">
        🤖 企业级 RAG 系统
      </div>
      <el-menu
        :default-active="$route.path"
        background-color="#1f2937"
        text-color="#9ca3af"
        active-text-color="#fff"
        router
      >
        <el-menu-item v-for="r in routes" :key="r.path" :index="r.path">
          <el-icon><component :is="r.meta.icon" /></el-icon>
          <span>{{ r.meta.title }}</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <!-- 主内容区 -->
    <el-container>
      <el-header style="background:#fff;border-bottom:1px solid #e5e7eb;display:flex;align-items:center;justify-content:space-between">
        <span style="font-size:18px;font-weight:600">{{ $route.meta.title }}</span>
        <div style="display:flex;align-items:center;gap:12px">
          <el-tag :type="healthOk ? 'success' : 'danger'" effect="dark">
            {{ healthOk ? '后端在线' : '后端离线' }}
          </el-tag>
          <el-tag type="info">{{ role }}</el-tag>
          <el-button size="small" @click="logout">退出</el-button>
        </div>
      </el-header>
      <el-main style="background:#f3f4f6;padding:24px">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
  <router-view v-else />
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { getHealth } from './api'
import { ElMessage } from 'element-plus'

const router = useRouter()
const routes = [
  { path: '/dashboard', meta: { icon: 'DataAnalysis', title: '系统概览' } },
  { path: '/chat', meta: { icon: 'ChatDotRound', title: '智能问答' } },
  { path: '/documents', meta: { icon: 'UploadFilled', title: '文档管理' } },
]

const role = computed(() => localStorage.getItem('role') || '未登录')
const healthOk = ref(false)
let timer = null

const checkHealth = async () => {
  try { await getHealth(); healthOk.value = true }
  catch { healthOk.value = false }
}

const logout = () => {
  localStorage.removeItem('token')
  localStorage.removeItem('role')
  ElMessage.success('已退出登录')
  router.push('/login')
}

onMounted(() => { checkHealth(); timer = setInterval(checkHealth, 10000) })
onUnmounted(() => { clearInterval(timer) })
</script>

<style>
html, body, #app { margin: 0; padding: 0; height: 100%; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }
</style>

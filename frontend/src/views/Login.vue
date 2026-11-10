<template>
  <div style="max-width:400px;margin:120px auto">
    <el-card>
      <h2 style="text-align:center;margin-bottom:24px">🔐 系统登录</h2>
      <el-form @submit.prevent="onLogin">
        <el-form-item>
          <el-input v-model="username" placeholder="用户名（admin / worker）" size="large" />
        </el-form-item>
        <el-form-item>
          <el-input v-model="password" type="password" placeholder="密码（123）" size="large" show-password />
        </el-form-item>
        <el-button type="primary" size="large" style="width:100%" :loading="loading" @click="onLogin">登录</el-button>
      </el-form>
      <p style="color:#909399;font-size:13px;text-align:center;margin-top:16px">
        admin → 管理员（可看 V1+V2）<br>
        其他用户名 → 普通工人（只看 V1）
      </p>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { login } from '../api'
import { ElMessage } from 'element-plus'

const router = useRouter()
const username = ref('admin')
const password = ref('123')
const loading = ref(false)

const onLogin = async () => {
  if (!username.value || !password.value) return
  loading.value = true
  try {
    const res = await login(username.value, password.value)
    localStorage.setItem('token', res.data.token)
    localStorage.setItem('role', res.data.role)
    ElMessage.success('登录成功')
    router.push('/chat')
  } catch (e) {
    ElMessage.error('登录失败：' + (e.response?.data?.detail || e.message))
  } finally {
    loading.value = false
  }
}
</script>

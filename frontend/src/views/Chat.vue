<template>
  <div style="max-width:900px;margin:0 auto">
    <!-- 顶部工具条 -->
    <el-card shadow="never" style="margin-bottom:16px">
      <div style="display:flex;gap:16px;align-items:center">
        <label style="font-weight:500">设备型号过滤：</label>
        <el-select v-model="device" placeholder="不限（通用）" style="width:200px" clearable>
          <el-option label="通用（不过滤）" value="" />
          <el-option label="CK6132 普通车床" value="CK6132" />
          <el-option label="CK6140 普通车床" value="CK6140" />
          <el-option label="VMC850 加工中心" value="VMC850" />
        </el-select>
        <el-checkbox v-model="useStream">SSE 流式输出</el-checkbox>
      </div>
    </el-card>

    <!-- 聊天区 -->
    <el-card shadow="never" style="margin-bottom:16px;min-height:400px">
      <div v-if="messages.length === 0" style="text-align:center;color:#909399;padding:60px 0">
        <el-icon :size="48"><ChatLineSquare /></el-icon>
        <p style="margin-top:12px">输入一个故障问题，试试混合检索 RAG 的效果吧！</p>
        <div style="margin-top:12px">
          <el-button v-for="q in quickQs" :key="q" size="small" @click="ask(q)">{{ q }}</el-button>
        </div>
      </div>

      <div v-for="(msg, idx) in messages" :key="idx" style="margin-bottom:20px">
        <!-- 用户消息 -->
        <div v-if="msg.role === 'user'" style="display:flex;justify-content:flex-end">
          <div style="background:#409EFF;color:#fff;padding:10px 16px;border-radius:12px;max-width:70%;white-space:pre-wrap">{{ msg.content }}</div>
        </div>
        <!-- AI 消息 -->
        <div v-else>
          <div style="display:flex;gap:10px">
            <el-icon :size="20" style="color:#409EFF"><Cpu /></el-icon>
            <div style="flex:1">
              <div style="background:#f5f7fa;padding:12px 16px;border-radius:12px;white-space:pre-wrap;border:1px solid #e4e7ed">{{ msg.content }}<span v-if="msg.loading" style="color:#409EFF">▊</span></div>
              <!-- 来源折叠 -->
              <el-collapse v-if="msg.sources && msg.sources.length" style="margin-top:8px">
                <el-collapse-item title="📎 参考来源（点击展开）">
                  <div v-for="(s, i) in msg.sources" :key="i" style="margin-bottom:8px;padding:8px;background:#fafafa;border-radius:6px;font-size:13px">
                    <div style="color:#67C23A;font-weight:600;margin-bottom:4px">
                      [{{ i + 1 }}] {{ s.metadata?.source || '未知来源' }}
                      <el-tag v-if="s.metadata?.security_level" size="small"
                        :type="s.metadata.security_level === 'V2' ? 'danger' : 'info'" style="margin-left:8px">
                        {{ s.metadata.security_level === 'V2' ? '🔒 V2 机密' : 'V1 普通' }}
                      </el-tag>
                      <el-tag v-if="s.metadata?.device" size="small" type="success" style="margin-left:6px">{{ s.metadata.device }}</el-tag>
                      <el-tag v-if="s.rerank_score" size="small" type="warning" style="margin-left:6px">Rerank: {{ s.rerank_score.toFixed(3) }}</el-tag>
                    </div>
                    <div style="color:#606266">{{ s.content }}</div>
                  </div>
                </el-collapse-item>
              </el-collapse>
            </div>
          </div>
        </div>
      </div>
    </el-card>

    <!-- 输入框 -->
    <div style="display:flex;gap:12px">
      <el-input v-model="input" type="textarea" :rows="3" placeholder="输入故障问题，回车发送，Shift+回车换行" @keydown.enter.exact.prevent="submit" />
      <el-button type="primary" :loading="loading" @click="submit" style="height:auto;width:100px">发送</el-button>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { query, queryStream } from '../api'

const messages = ref([])
const input = ref('')
const device = ref('')
const loading = ref(false)
const useStream = ref(true)

const quickQs = [
  'CK6132 主轴异响怎么排查？',
  'VMC850 Z轴抖动是什么原因？',
  'CK6140 刀架转不到位怎么办？',
]

const ask = (text) => { input.value = text; submit() }

const submit = async () => {
  const q = input.value.trim()
  if (!q || loading.value) return
  messages.value.push({ role: 'user', content: q })
  messages.value.push({ role: 'ai', content: '', loading: true, sources: [] })
  input.value = ''
  loading.value = true

  if (useStream.value) {
    // SSE 流式：token 边收边渲染，末尾直接带来源，无需二次请求
    queryStream(q, device.value, {
      onChunk: (chunk) => { messages.value[messages.value.length - 1].content += chunk },
      onSources: (srcs) => { messages.value[messages.value.length - 1].sources = srcs },
      onDone: () => {
        messages.value[messages.value.length - 1].loading = false
        loading.value = false
      },
      onError: (e) => {
        messages.value[messages.value.length - 1].content = '❌ 请求失败：' + e.message
        messages.value[messages.value.length - 1].loading = false
        loading.value = false
      },
    })
  } else {
    // 同步
    try {
      const res = await query(q, device.value)
      messages.value[messages.value.length - 1].content = res.data.answer
      messages.value[messages.value.length - 1].sources = res.data.sources
    } catch (e) {
      messages.value[messages.value.length - 1].content = '❌ 请求失败：' + e.message
    }
    messages.value[messages.value.length - 1].loading = false
    loading.value = false
  }
}
</script>

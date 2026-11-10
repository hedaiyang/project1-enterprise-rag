<template>
  <div>
    <!-- 统计卡片 -->
    <el-row :gutter="16" style="margin-bottom:20px">
      <el-col :span="6">
        <el-card shadow="hover">
          <div style="display:flex;align-items:center;gap:12px">
            <el-icon :size="36" color="#409EFF"><FolderOpened /></el-icon>
            <div>
              <div style="font-size:24px;font-weight:bold">{{ health.total_chunks }}</div>
              <div style="color:#909399;font-size:13px">向量碎片总数</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div style="display:flex;align-items:center;gap:12px">
            <el-icon :size="36" color="#67C23A"><Files /></el-icon>
            <div>
              <div style="font-size:24px;font-weight:bold">{{ sources.length }}</div>
              <div style="color:#909399;font-size:13px">源文档数量</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div style="display:flex;align-items:center;gap:12px">
            <el-icon :size="36" color="#E6A23C"><Cpu /></el-icon>
            <div>
              <div style="font-size:24px;font-weight:bold">混合检索</div>
              <div style="color:#909399;font-size:13px">向量 + BM25 + Rerank</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div style="display:flex;align-items:center;gap:12px">
            <el-icon :size="36" color="#F56C6C"><Odometer /></el-icon>
            <div>
              <div style="font-size:24px;font-weight:bold">SSE</div>
              <div style="color:#909399;font-size:13px">流式问答输出</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 检索配置 -->
    <el-card shadow="never">
      <template #header><span style="font-weight:600">🔧 当前检索配置</span></template>
      <el-descriptions :column="2" border>
        <el-descriptions-item label="向量库集合名">{{ health.collection }}</el-descriptions-item>
        <el-descriptions-item label="Embedding 模型">Ollama / bge-m3 (1024维)</el-descriptions-item>
        <el-descriptions-item label="LLM 生成模型">Ollama / qwen2.5:3b</el-descriptions-item>
        <el-descriptions-item label="Rerank 模型">bge-reranker-v2-m3</el-descriptions-item>
        <el-descriptions-item label="分块大小">500 字符 + 50 重叠</el-descriptions-item>
        <el-descriptions-item label="检索策略">Top5 向量 → RRF 融合 → Rerank Top3</el-descriptions-item>
        <el-descriptions-item label="当前角色">
          <el-tag :type="role === 'admin' ? 'danger' : 'info'" size="small">{{ role }}</el-tag>
          <span style="margin-left:8px;color:#606266">可见密级：{{ role === 'admin' ? 'V1 + V2（全部）' : 'V1（普通）' }}</span>
        </el-descriptions-item>
      </el-descriptions>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getHealth, getSources } from '../api'

const health = ref({ total_chunks: 0, collection: 'enterprise_knowledge' })
const sources = ref([])
const role = ref(localStorage.getItem('role') || '未登录')

onMounted(async () => {
  try {
    const [h, s] = await Promise.all([getHealth(), getSources()])
    health.value = h.data
    sources.value = s.data.sources || []
  } catch {}
})
</script>

<template>
  <el-row :gutter="20">
    <!-- 左：上传区 -->
    <el-col :span="12">
      <el-card shadow="never">
        <template #header><span style="font-weight:600">📤 上传新文档</span></template>
        <el-upload
          drag
          :auto-upload="false"
          :on-change="handleFileChange"
          :limit="1"
          accept=".md,.txt,.docx,.pdf"
        >
          <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
          <div class="el-upload__text">拖拽文件到这里，或 <em>点击选择文件</em></div>
          <template #tip>
            <div class="el-upload__tip">支持 .md / .txt / .docx / .pdf，自动分块 + 向量化入库</div>
          </template>
        </el-upload>

        <div style="margin-top:16px">
          <label style="font-weight:500;margin-right:8px">设备型号（可选 metadata）：</label>
          <el-select v-model="device" placeholder="不填则不加 metadata" style="width:220px" clearable>
            <el-option label="CK6132 普通车床" value="CK6132" />
            <el-option label="CK6140 普通车床" value="CK6140" />
            <el-option label="VMC850 加工中心" value="VMC850" />
          </el-select>
        </div>

        <div style="margin-top:12px">
          <label style="font-weight:500;margin-right:8px">文档密级：</label>
          <el-radio-group v-model="securityLevel">
            <el-radio label="V1">V1 普通（所有人可见）</el-radio>
            <el-radio label="V2">V2 机密（仅管理员）</el-radio>
          </el-radio-group>
        </div>

        <el-button type="primary" :loading="uploading" :disabled="!file" @click="doUpload" style="margin-top:16px">
          开始入库
        </el-button>
      </el-card>
    </el-col>

    <!-- 右：已入库文档 -->
    <el-col :span="12">
      <el-card shadow="never">
        <template #header>
          <span style="font-weight:600">📚 已入库源文档 ({{ sources.length }})</span>
          <el-button size="small" style="float:right" @click="refresh">刷新</el-button>
        </template>
        <div v-if="sources.length === 0" style="text-align:center;color:#909399;padding:40px 0">
          <el-icon :size="36"><Warning /></el-icon>
          <p style="margin-top:8px">还没有任何文档入库，请先上传</p>
        </div>
        <el-table v-else :data="sources.map((s, i) => ({ index: i + 1, name: s }))" stripe>
          <el-table-column prop="index" label="#" width="50" />
          <el-table-column prop="name" label="文档名称" />
          <el-table-column label="操作" width="100">
            <template #default="{ row }">
              <el-button size="small" type="danger" link @click="deleteDoc(row.name)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </el-col>
  </el-row>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { uploadFile, getSources, deleteSource } from '../api'

const file = ref(null)
const device = ref('')
const securityLevel = ref('V1')
const uploading = ref(false)
const sources = ref([])

const handleFileChange = (f) => { file.value = f.raw }

const doUpload = async () => {
  if (!file.value) return
  uploading.value = true
  try {
    const res = await uploadFile(file.value, device.value, securityLevel.value)
    ElMessage.success(`入库成功！新增 ${res.data.chunks_added} 个碎片，密级 ${res.data.security_level}，当前共 ${res.data.total_in_collection} 个`)
    file.value = null
    await refresh()
  } catch (e) {
    ElMessage.error('入库失败：' + (e.response?.data?.detail || e.message))
  }
  uploading.value = false
}

const refresh = async () => {
  try {
    const res = await getSources()
    sources.value = res.data.sources || []
  } catch {}
}

const deleteDoc = async (name) => {
  try {
    await ElMessageBox.confirm(`确定要删除「${name}」的所有向量碎片吗？此操作不可恢复。`, '确认删除', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch {
    return  // 用户点取消
  }
  try {
    const res = await deleteSource(name)
    ElMessage.success(`已删除 ${res.data.deleted} 个碎片，剩余 ${res.data.total_chunks} 个`)
    await refresh()
  } catch (e) {
    ElMessage.error('删除失败：' + (e.response?.data?.detail || e.message))
  }
}

onMounted(refresh)
</script>

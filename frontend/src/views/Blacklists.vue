<template>
  <div>
    <h2 class="page-title">黑名单管理</h2>
    <el-card class="card">
      <div style="margin-bottom: 12px; display: flex; gap: 8px">
        <el-select v-model="type" placeholder="全部类型" clearable style="width: 160px" @change="load">
          <el-option v-for="(v, k) in typeLabels" :key="k" :label="v" :value="k" />
        </el-select>
        <el-button type="primary" @click="openAdd">新增</el-button>
        <el-button @click="importVisible = true">批量导入</el-button>
        <el-button type="danger" :disabled="!selected.length" @click="removeSelected">删除所选</el-button>
      </div>
      <el-table :data="items" border @selection-change="(s) => (selected = s)">
        <el-table-column type="selection" width="50" />
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column label="类型" width="120">
          <template #default="{ row }">{{ typeLabels[row.blacklist_type] || row.blacklist_type }}</template>
        </el-table-column>
        <el-table-column prop="blacklist_value" label="命中值" min-width="200" />
        <el-table-column prop="remark" label="备注" min-width="160" />
        <el-table-column prop="status" label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.status === 1 ? 'danger' : 'info'">{{ row.status === 1 ? '生效' : '失效' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="addVisible" title="新增黑名单" width="480px">
      <el-form label-width="90px">
        <el-form-item label="类型" required>
          <el-select v-model="addForm.blacklist_type" style="width: 100%">
            <el-option v-for="(v, k) in typeLabels" :key="k" :label="v" :value="k" />
          </el-select>
        </el-form-item>
        <el-form-item label="命中值" required><el-input v-model="addForm.blacklist_value" /></el-form-item>
        <el-form-item label="备注"><el-input v-model="addForm.remark" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="importVisible" title="批量导入黑名单" width="560px">
      <el-form label-width="90px">
        <el-form-item label="类型" required>
          <el-select v-model="importForm.blacklist_type" style="width: 100%">
            <el-option v-for="(v, k) in typeLabels" :key="k" :label="v" :value="k" />
          </el-select>
        </el-form-item>
        <el-form-item label="内容" required>
          <el-input v-model="importForm.text" type="textarea" :rows="8" placeholder="每行一个值，或逗号分隔，例如：&#10;13800009999&#10;13800008888" />
        </el-form-item>
        <el-form-item label="备注"><el-input v-model="importForm.remark" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="importVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="doImport">导入</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { reactive, ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { listBlacklists, createBlacklist, deleteBlacklists, importBlacklists } from '../api'

const items = ref([])
const type = ref('')
const selected = ref([])
const addVisible = ref(false)
const importVisible = ref(false)
const saving = ref(false)

const typeLabels = { user: '用户', order: '订单', address: '地址', phone: '手机号', ip: 'IP' }
const addForm = reactive({ blacklist_type: 'user', blacklist_value: '', remark: '' })
const importForm = reactive({ blacklist_type: 'address', text: '', remark: '' })

function formatTime(t) { return t ? t.replace('T', ' ').slice(0, 19) : '—' }

async function load() {
  const params = {}
  if (type.value) params.blacklist_type = type.value
  items.value = await listBlacklists(params)
}
function openAdd() {
  Object.assign(addForm, { blacklist_type: 'user', blacklist_value: '', remark: '' })
  addVisible.value = true
}
async function save() {
  saving.value = true
  try {
    await createBlacklist(addForm)
    ElMessage.success('已新增')
    addVisible.value = false
    await load()
  } finally { saving.value = false }
}
async function doImport() {
  saving.value = true
  try {
    const res = await importBlacklists(importForm)
    ElMessage.success(`导入完成：新增 ${res.added}，跳过 ${res.skipped}`)
    importVisible.value = false
    await load()
  } finally { saving.value = false }
}
async function removeSelected() {
  await ElMessageBox.confirm(`确认删除所选 ${selected.value.length} 条黑名单？`, '提示', { type: 'warning' })
  const ids = selected.value.map((s) => s.id)
  await deleteBlacklists(ids)
  ElMessage.success('已删除')
  await load()
}
onMounted(load)
</script>

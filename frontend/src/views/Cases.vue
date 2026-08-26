<template>
  <div>
    <h2 class="page-title">案件管理</h2>
    <el-card class="card">
      <div style="margin-bottom: 12px; display: flex; gap: 8px; align-items: center">
        <el-select v-model="status" placeholder="全部状态" clearable style="width: 180px" @change="onFilter">
          <el-option v-for="(v, k) in statusLabels" :key="k" :label="v" :value="k" />
        </el-select>
        <el-button @click="onFilter">刷新</el-button>
      </div>
      <el-table :data="items" border>
        <el-table-column prop="id" label="案件编号" width="90">
          <template #default="{ row }">
            <el-link type="primary" @click="goDetail(row.id)">CASE-{{ row.id }}</el-link>
          </template>
        </el-table-column>
        <el-table-column prop="case_status" label="状态" width="110">
          <template #default="{ row }">
            <el-tag :type="statusType(row.case_status)">{{ statusLabels[row.case_status] || row.case_status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="risk_level" label="风险等级" width="100">
          <template #default="{ row }">{{ levelText(row.risk_level) }}</template>
        </el-table-column>
        <el-table-column prop="user_id" label="关联用户" width="120" />
        <el-table-column prop="order_id" label="关联订单" width="160" />
        <el-table-column prop="reviewer_id" label="审核人" width="120" />
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="goDetail(row.id)">查看</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination
        style="margin-top: 12px; justify-content: flex-end"
        layout="total, prev, pager, next"
        :total="total"
        :page-size="size"
        :current-page="page"
        @current-change="onPage"
      />
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { listCases } from '../api'

const router = useRouter()
const items = ref([])
const total = ref(0)
const page = ref(1)
const size = ref(10)
const status = ref('')

const statusLabels = {
  pending: '待处理', reviewing: '处理中', approved: '已通过', rejected: '已拒绝', resolved: '已解决',
}
const statusType = { pending: 'warning', reviewing: 'primary', approved: 'success', rejected: 'danger', resolved: 'info' }

function levelText(l) { return { low: '低', medium: '中', high: '高' }[l] || l }
function formatTime(t) { return t ? t.replace('T', ' ').slice(0, 19) : '—' }

async function load() {
  const params = { page: page.value, size: size.value }
  if (status.value) params.status = status.value
  const res = await listCases(params)
  items.value = res.items || []
  total.value = res.total || 0
}
function onFilter() { page.value = 1; load() }
function onPage(p) { page.value = p; load() }
function goDetail(id) { router.push(`/cases/${id}`) }
onMounted(load)
</script>

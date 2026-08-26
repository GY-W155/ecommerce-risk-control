<template>
  <div>
    <h2 class="page-title">用户画像</h2>
    <el-card class="card">
      <div style="display: flex; gap: 8px">
        <el-input v-model="userId" placeholder="输入用户编号，如 U1001 / U2002 / U3003" style="max-width: 360px" @keyup.enter="load" />
        <el-button type="primary" :loading="loading" @click="load">查询</el-button>
      </div>
    </el-card>

    <el-card v-if="profile" class="card">
      <template #header>用户概览（{{ profile.user_id }}）</template>
      <el-row :gutter="12">
        <el-col :span="4" v-for="s in stats" :key="s.label">
          <div class="stat-box">
            <div class="stat-label">{{ s.label }}</div>
            <div class="stat-value" :style="{ color: s.warn ? '#f56c6c' : '' }">{{ s.value }}</div>
          </div>
        </el-col>
      </el-row>
    </el-card>

    <template v-if="profile">
      <el-card class="card">
        <template #header>历史订单（{{ profile.orders.length }}）</template>
        <el-table :data="profile.orders" border size="small">
          <el-table-column prop="order_id" label="订单号" />
          <el-table-column prop="amount" label="金额" width="120" />
          <el-table-column prop="status" label="状态" width="100" />
          <el-table-column prop="created_at" label="下单时间">
            <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
          </el-table-column>
        </el-table>
      </el-card>

      <el-card class="card">
        <template #header>最近风险事件（{{ profile.recent_risk_events.length }}）</template>
        <el-table :data="profile.recent_risk_events" border size="small">
          <el-table-column prop="id" label="事件ID" width="90" />
          <el-table-column prop="event_type" label="事件类型" width="160" />
          <el-table-column prop="order_id" label="关联订单" />
          <el-table-column prop="created_at" label="发生时间">
            <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
          </el-table-column>
        </el-table>
      </el-card>

      <el-card class="card">
        <template #header>关联案件（{{ profile.related_cases.length }}）</template>
        <el-table :data="profile.related_cases" border size="small">
          <el-table-column prop="id" label="案件编号" width="110">
            <template #default="{ row }">
              <el-link type="primary" @click="goCase(row.id)">CASE-{{ row.id }}</el-link>
            </template>
          </el-table-column>
          <el-table-column prop="risk_level" label="风险等级" width="100">
            <template #default="{ row }">{{ levelText(row.risk_level) }}</template>
          </el-table-column>
          <el-table-column prop="case_status" label="状态" width="100" />
          <el-table-column prop="reviewer_id" label="审核人" width="120" />
          <el-table-column prop="created_at" label="创建时间">
            <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
          </el-table-column>
        </el-table>
      </el-card>
    </template>
    <el-empty v-else-if="searched" description="未查询到数据" :image-size="80" />
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { getUserProfile } from '../api'

const router = useRouter()
const userId = ref('U1001')
const profile = ref(null)
const loading = ref(false)
const searched = ref(false)

const levelText = (l) => ({ low: '低', medium: '中', high: '高' }[l] || l)
const formatTime = (t) => (t ? t.replace('T', ' ').slice(0, 19) : '—')

const stats = computed(() => {
  if (!profile.value) return []
  return [
    { label: '订单数', value: profile.value.order_count },
    { label: '退款次数', value: profile.value.refund_count, warn: profile.value.refund_count > 3 },
    { label: '投诉次数', value: profile.value.complaint_count, warn: profile.value.complaint_count > 1 },
    { label: '地址数', value: profile.value.address_count },
    { label: '黑名单命中', value: profile.value.blacklist_hit, warn: profile.value.blacklist_hit > 0 },
  ]
})

async function load() {
  loading.value = true
  try {
    profile.value = await getUserProfile(userId.value)
    searched.value = true
  } finally { loading.value = false }
}
function goCase(id) { router.push(`/cases/${id}`) }
</script>

<style scoped>
.stat-box { text-align: center; padding: 8px; border-right: 1px solid #f0f0f0; }
.stat-label { color: #909399; font-size: 13px; }
.stat-value { font-size: 24px; font-weight: 700; margin-top: 4px; }
</style>

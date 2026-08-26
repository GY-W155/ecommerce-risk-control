<template>
  <div>
    <h2 class="page-title">风险检查</h2>
    <el-card class="card">
      <template #header>发起风险检查</template>
      <el-form label-width="100px" :model="form" style="max-width: 620px">
        <el-form-item label="事件类型" required>
          <el-select v-model="form.event_type" placeholder="选择事件类型">
            <el-option v-for="t in eventTypes" :key="t" :label="eventLabels[t]" :value="t" />
          </el-select>
        </el-form-item>
        <el-form-item label="来源标识" required>
          <el-input v-model="form.source_id" placeholder="例：订单中心 / 支付中心" />
        </el-form-item>
        <el-form-item label="用户编号" required>
          <el-input v-model="form.user_id" placeholder="例：U1001 / U2002 / U3003" />
        </el-form-item>
        <el-form-item label="订单编号">
          <el-input v-model="form.order_id" placeholder="例：U2002-O2001" />
        </el-form-item>
        <el-form-item label="事件金额">
          <el-input-number v-model="form.amount" :min="0" :step="100" controls-position="right" />
          <span style="margin-left: 8px; color:#909399">元，供订单维度特征使用</span>
        </el-form-item>
        <el-form-item label="收货距离">
          <el-input-number v-model="form.address_distance_km" :min="0" :step="10" controls-position="right" />
          <span style="margin-left: 8px; color:#909399">km，触发远程地址规则</span>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" @click="check">开始检查</el-button>
          <el-button @click="reset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card v-if="result" class="card">
      <template #header>检查结果</template>
      <div class="flex" style="align-items: center; margin-bottom: 12px">
        <div style="flex:1">
          <div>评分：<b>{{ result.risk_score }}</b></div>
          <el-progress :percentage="result.risk_score" :status="scoreStatus" :stroke-width="18" style="max-width: 420px; margin-top: 6px" />
        </div>
        <div style="text-align:center; min-width: 120px">
          <div style="color:#909399; font-size:12px">风险等级</div>
          <el-tag :type="levelType(result.risk_level)" size="large">{{ levelText(result.risk_level) }}</el-tag>
        </div>
        <div style="text-align:center; min-width: 120px">
          <div style="color:#909399; font-size:12px">处理建议</div>
          <el-tag :type="decisionType(result.decision)" size="large">{{ decisionText(result.decision) }}</el-tag>
        </div>
      </div>

      <el-alert
        v-if="result.case_id"
        title="该结果已自动创建案件，可直接进入审核"
        type="warning"
        :closable="false"
        style="margin-bottom: 12px"
      >
        <template #default>
          <el-button link type="primary" @click="goCase(result.case_id)">查看案件 #{{ result.case_id }}</el-button>
        </template>
      </el-alert>

      <el-divider></el-divider>
      <h4 class="section-title">命中规则（{{ result.rule_hits.length }} 条）</h4>
      <el-table :data="result.rule_hits" border size="small" style="margin-bottom: 16px">
        <el-table-column prop="rule_code" label="规则编码" width="120" />
        <el-table-column prop="rule_name" label="规则名称" />
        <el-table-column prop="hit_score" label="分值" width="80">
          <template #default="{ row }"><el-tag size="small" type="danger">{{ row.hit_score }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="hit_message" label="命中原因" />
      </el-table>

      <h4 class="section-title">特征快照</h4>
      <FeatureSnapshot :data="result.feature_snapshot" />
    </el-card>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { riskCheck } from '../api'
import FeatureSnapshot from '../components/FeatureSnapshot.vue'

const router = useRouter()
const eventTypes = ['order_create', 'order_pay', 'after_sale_apply', 'logistics_complaint']
const eventLabels = {
  order_create: '下单创建',
  order_pay: '订单支付',
  after_sale_apply: '售后申请',
  logistics_complaint: '物流投诉',
}
const form = reactive({
  event_type: 'order_create',
  source_id: '演示-下单中心',
  user_id: 'U1001',
  order_id: '',
  amount: 259,
  address_distance_km: 0,
})
const result = ref(null)
const loading = ref(false)

function levelText(l) { return { low: '低', medium: '中', high: '高' }[l] || l }
function levelType(l) { return { low: 'success', medium: 'warning', high: 'danger' }[l] || 'info' }
function decisionText(d) {
  return { pass: '放行', manual_review: '人工审核', reject: '拒绝' }[d] || d
}
function decisionType(d) {
  return { pass: 'success', manual_review: 'warning', reject: 'danger' }[d] || 'info'
}
function scoreStatus() {
  if (result.value?.decision === 'reject') return 'exception'
  if (result.value?.risk_score < 40) return 'success'
  return 'warning'
}

async function check() {
  loading.value = true
  try {
    const payload = { amount: form.amount, address_distance_km: form.address_distance_km }
    result.value = await riskCheck({
      event_type: form.event_type,
      source_id: form.source_id,
      user_id: form.user_id,
      order_id: form.order_id || null,
      event_payload: payload,
    })
  } finally {
    loading.value = false
  }
}
function reset() {
  form.event_type = 'order_create'
  form.user_id = 'U1001'
  form.order_id = ''
  form.amount = 259
  form.address_distance_km = 0
  result.value = null
}
function goCase(id) { router.push(`/cases/${id}`) }
</script>

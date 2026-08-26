<template>
  <div v-if="detail">
    <h2 class="page-title">案件详情 <el-tag :type="statusType(detail.case.case_status)">{{ statusLabels[detail.case.case_status] }}</el-tag></h2>

    <el-card class="card">
      <template #header>案件信息</template>
      <el-descriptions :column="3" border>
        <el-descriptions-item label="案件编号">CASE-{{ detail.case.id }}</el-descriptions-item>
        <el-descriptions-item label="风险等级">{{ levelText(detail.case.risk_level) }}</el-descriptions-item>
        <el-descriptions-item label="关联用户">{{ detail.case.user_id }}</el-descriptions-item>
        <el-descriptions-item label="关联订单">{{ detail.case.order_id || '—' }}</el-descriptions-item>
        <el-descriptions-item label="审核人">{{ detail.case.reviewer_id || '待审核' }}</el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ formatTime(detail.case.created_at) }}</el-descriptions-item>
      </el-descriptions>
    </el-card>

    <el-card v-if="detail.assessment" class="card">
      <template #header>风险结果</template>
      <div class="flex">
        <div style="flex:1">
          <div style="margin-bottom: 6px">综合评分：<b>{{ detail.assessment.risk_score }}</b></div>
          <el-progress :percentage="detail.assessment.risk_score" :status="scoreStatus" :stroke-width="16" style="max-width: 380px" />
        </div>
        <div style="text-align:center; min-width:100px">
          <div style="color:#909399; font-size:12px">等级</div>
          <el-tag :type="levelType(detail.assessment.risk_level)" size="large">{{ levelText(detail.assessment.risk_level) }}</el-tag>
        </div>
        <div style="text-align:center; min-width:100px">
          <div style="color:#909399; font-size:12px">建议</div>
          <el-tag :type="decisionType(detail.assessment.decision)" size="large">{{ decisionText(detail.assessment.decision) }}</el-tag>
        </div>
      </div>

      <el-divider></el-divider>
      <h4 class="section-title">命中规则</h4>
      <el-table :data="detail.assessment.rule_hits" border size="small">
        <el-table-column prop="rule_code" label="编码" width="110" />
        <el-table-column prop="rule_name" label="规则名称" />
        <el-table-column prop="hit_score" label="分值" width="80" />
        <el-table-column prop="hit_message" label="命中原因" />
      </el-table>

      <h4 class="section-title">特征快照</h4>
      <FeatureSnapshot :data="detail.assessment.feature_snapshot" />
    </el-card>

    <el-card class="card">
      <template #header>审核处理</template>
      <el-form label-width="90px" style="max-width: 520px">
        <el-form-item label="审核结论" required>
          <el-select v-model="review.form.review_result" placeholder="选择结论">
            <el-option label="通过 (approved)" value="approved" />
            <el-option label="拒绝 (rejected)" value="rejected" />
            <el-option label="解决 (resolved)" value="resolved" />
            <el-option label="处理中 (reviewing)" value="reviewing" />
          </el-select>
        </el-form-item>
        <el-form-item label="审核备注">
          <el-input v-model="review.form.review_remark" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="操作人">
          <el-input v-model="review.form.operator_id" placeholder="auditor_001" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="review.loading" @click="submitReview">提交审核</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card class="card">
      <template #header>审核日志</template>
      <el-timeline v-if="detail.review_logs.length" style="padding-left: 6px">
        <el-timeline-item v-for="log in detail.review_logs" :key="log.id" :timestamp="formatTime(log.created_at)">
          <b>{{ log.action_type === 'auto_create' ? '系统自动建案' : '人工审核' }}</b>
          <el-tag size="small" style="margin-left: 6px">{{ log.operator_id }}</el-tag>
          <div style="margin-top: 4px">{{ log.action_remark }}</div>
        </el-timeline-item>
      </el-timeline>
      <el-empty v-else description="暂无审核日志" :image-size="60" />
    </el-card>
  </div>
  <el-empty v-else description="加载中" />
</template>

<script setup>
import { reactive, ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getCaseDetail, reviewCase } from '../api'
import FeatureSnapshot from '../components/FeatureSnapshot.vue'

const route = useRoute()
const detail = ref(null)
const review = reactive({
  loading: false,
  form: { case_id: null, review_result: 'approved', review_remark: '', operator_id: 'auditor_001' },
})

const statusLabels = { pending: '待处理', reviewing: '处理中', approved: '已通过', rejected: '已拒绝', resolved: '已解决' }
const statusType = { pending: 'warning', reviewing: 'primary', approved: 'success', rejected: 'danger', resolved: 'info' }

function levelText(l) { return { low: '低', medium: '中', high: '高' }[l] || l }
function levelType(l) { return { low: 'success', medium: 'warning', high: 'danger' }[l] || 'info' }
function decisionText(d) { return { pass: '放行', manual_review: '人工审核', reject: '拒绝' }[d] || d }
function decisionType(d) { return { pass: 'success', manual_review: 'warning', reject: 'danger' }[d] || 'info' }
function formatTime(t) { return t ? t.replace('T', ' ').slice(0, 19) : '—' }
const scoreStatus = computed(() => {
  if (detail.value?.assessment?.decision === 'reject') return 'exception'
  return detail.value?.assessment?.risk_score < 40 ? 'success' : 'warning'
})

async function load() {
  detail.value = await getCaseDetail(route.params.id)
  review.form.case_id = detail.value.case.id
}
async function submitReview() {
  review.loading = true
  try {
    await reviewCase(review.form)
    ElMessage.success('审核完成')
    await load()
  } finally {
    review.loading = false
  }
}
onMounted(load)
</script>

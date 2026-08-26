<template>
  <div>
    <h2 class="page-title">规则管理</h2>
    <el-card class="card">
      <div style="margin-bottom: 12px">
        <el-button type="primary" @click="openCreate">新增规则</el-button>
        <span style="margin-left: 12px; color:#909399; font-size:12px">共 {{ rules.length }} 条规则</span>
      </div>
      <el-table :data="rules" border>
        <el-table-column prop="rule_code" label="编码" width="100" />
        <el-table-column prop="rule_name" label="规则名称" min-width="160" />
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-switch :model-value="row.rule_status === 1" @change="(v) => toggleStatus(row, v)" />
          </template>
        </el-table-column>
        <el-table-column prop="priority" label="优先级" width="90" sortable />
        <el-table-column prop="score" label="分值" width="80" sortable />
        <el-table-column prop="hit_count" label="命中次数" width="90" sortable />
        <el-table-column prop="description" label="描述" min-width="180" show-overflow-tooltip />
        <el-table-column prop="updated_at" label="更新时间" width="180">
          <template #default="{ row }">{{ formatTime(row.updated_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="130" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button link type="danger" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑规则' : '新增规则'" width="720px">
      <el-form label-width="90px" :model="form">
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="规则编码" required>
              <el-input v-model="form.rule_code" placeholder="如 SCR030" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="规则名称" required>
              <el-input v-model="form.rule_name" placeholder="规则名称" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="优先级">
              <el-input-number v-model="form.priority" :min="0" :max="999" controls-position="right" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="命中分值">
              <el-input-number v-model="form.score" :min="0" :max="100" controls-position="right" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="状态">
              <el-switch v-model="form.rule_status" :active-value="1" :inactive-value="0" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="命中描述">
          <el-input v-model="form.description" />
        </el-form-item>

        <el-form-item label="条件结构">
          <el-radio-group v-model="condMode" size="small">
            <el-radio-button value="builder">可视化构建</el-radio-button>
            <el-radio-button value="json">JSON 高级</el-radio-button>
          </el-radio-group>
        </el-form-item>

        <!-- 可视化条件构建器（单层 AND/OR + 若干条件行） -->
        <div v-if="condMode === 'builder'" style="border: 1px solid #eee; padding: 12px; border-radius: 6px">
          <div style="margin-bottom: 8px">
            <span style="margin-right: 8px">组合方式</span>
            <el-radio-group v-model="builder.operator" size="small">
              <el-radio-button value="AND">与(AND)</el-radio-button>
              <el-radio-button value="OR">或(OR)</el-radio-button>
            </el-radio-group>
          </div>
          <div v-for="(c, idx) in builder.conditions" :key="idx" style="display: flex; gap: 6px; margin-bottom: 8px; align-items: center">
            <el-select v-model="c.feature" filterable allow-create default-first-option placeholder="特征" style="width: 180px">
              <el-option v-for="f in features" :key="f" :value="f" />
            </el-select>
            <el-select v-model="c.op" style="width: 110px">
              <el-option v-for="o in ['>', '<', '>=', '<=', '=', '!=', 'contains']" :key="o" :value="o" />
            </el-select>
            <el-input v-model="c.value" placeholder="值" style="width: 140px" />
            <el-button link type="danger" @click="builder.conditions.splice(idx, 1)">移除</el-button>
          </div>
          <el-button size="small" @click="addCondition">+ 添加条件</el-button>
        </div>

        <!-- JSON 高级模式 -->
        <el-form-item v-if="condMode === 'json'" label="条件 JSON">
          <el-input v-model="rawJson" type="textarea" :rows="8" placeholder='{"operator":"AND","conditions":[{"feature":"user_refund_count_30d","op":">","value":3}]}' />
          <div style="font-size:12px; color:#909399">支持嵌套 AND / OR，操作符：>、<、>=、<=、=、!=、contains</div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { reactive, ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { listRules, createRule, updateRule, changeRuleStatus, deleteRule } from '../api'

const rules = ref([])
const dialogVisible = ref(false)
const isEdit = ref(false)
const saving = ref(false)
const condMode = ref('builder')
const rawJson = ref('')

const features = [
  'user_blacklist_hit', 'user_new_flag', 'user_refund_count_30d', 'user_complaint_count_30d',
  'user_history_high_risk_events', 'user_device_count', 'user_mobile_changed_7d',
  'user_order_freq_7d', 'user_order_count_30d', 'user_order_count_total', 'user_address_count',
  'user_avg_order_amount', 'user_last_refund_days', 'user_risk_region',
  'order_amount', 'order_item_count', 'order_discount_ratio', 'order_night_flag',
  'order_has_coupon', 'order_sensitive_goods', 'order_pay_timeout', 'order_amount_vs_avg',
  'order_high_value', 'order_blacklist_hit',
  'address_blacklist_hit', 'address_region_risk', 'address_used_count', 'address_distance_km',
  'address_mismatch', 'address_area_changed_7d', 'address_province_risk_score',
]

const form = reactive({
  id: null, rule_code: '', rule_name: '', rule_status: 1, priority: 0, score: 0, description: '', condition_json: {},
})
const builder = reactive({ operator: 'AND', conditions: [{ feature: '', op: '>', value: '' }] })

function formatTime(t) { return t ? t.replace('T', ' ').slice(0, 19) : '—' }
function addCondition() { builder.conditions.push({ feature: '', op: '>', value: '' }) }

function openCreate() {
  isEdit.value = false
  condMode.value = 'builder'
  Object.assign(form, { id: null, rule_code: '', rule_name: '', rule_status: 1, priority: 0, score: 0, description: '', condition_json: {} })
  builder.operator = 'AND'
  builder.conditions = [{ feature: '', op: '>', value: '' }]
  dialogVisible.value = true
}

function openEdit(row) {
  isEdit.value = true
  Object.assign(form, {
    id: row.id, rule_code: row.rule_code, rule_name: row.rule_name, rule_status: row.rule_status,
    priority: row.priority, score: row.score, description: row.description, condition_json: row.condition_json,
  })
  // 若能解析为单层结构则可视化；否则显示 JSON
  const cj = row.condition_json || {}
  if (cj.conditions && cj.conditions.every((x) => x.feature)) {
    condMode.value = 'builder'
    builder.operator = cj.operator || 'AND'
    builder.conditions = cj.conditions.map((x) => ({ feature: x.feature, op: x.op, value: String(x.value ?? '') }))
  } else {
    condMode.value = 'json'
    rawJson.value = JSON.stringify(cj, null, 2)
  }
  dialogVisible.value = true
}

function buildCondition() {
  if (condMode.value === 'json') {
    try { return JSON.parse(rawJson.value) } catch { throw new Error('JSON 格式错误') }
  }
  const conds = builder.conditions
    .filter((c) => c.feature && c.op && c.value !== '')
    .map((c) => ({ feature: c.feature, op: c.op, value: toNum(c.value) }))
  if (!conds.length) throw new Error('至少填写一个条件')
  return { operator: builder.operator, conditions: conds }
}

function toNum(v) {
  const n = Number(v)
  return Number.isFinite(n) ? n : v
}

async function save() {
  saving.value = true
  try {
    let condition_json
    try { condition_json = buildCondition() } catch (e) { ElMessage.warning(e.message); return }
    const payload = { ...form, condition_json }
    if (isEdit.value) await updateRule(payload)
    else await createRule(payload)
    ElMessage.success('保存成功')
    dialogVisible.value = false
    await load()
  } catch (e) {
    // 请求拦截器已提示错误
  } finally {
    saving.value = false
  }
}

async function toggleStatus(row, val) {
  await changeRuleStatus({ id: row.id, rule_status: val ? 1 : 0 })
  row.rule_status = val ? 1 : 0
  ElMessage.success(val ? '已启用' : '已停用')
}

async function remove(row) {
  await ElMessageBox.confirm(`确认删除规则「${row.rule_name}」？`, '提示', { type: 'warning' })
  await deleteRule(row.id)
  ElMessage.success('已删除')
  await load()
}

async function load() { rules.value = await listRules() }
onMounted(load)
</script>

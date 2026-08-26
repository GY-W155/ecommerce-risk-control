<template>
  <div v-if="hasData">
    <div v-for="group in groups" :key="group.key" class="snap-group">
      <div class="snap-title">{{ group.title }}</div>
      <div class="kv" v-for="row in group.items" :key="row.key">
        <span>{{ row.label }}</span>
        <span :class="{ warn: isRisky(row.value) }">{{ format(row.value) }}</span>
      </div>
    </div>
  </div>
  <el-empty v-else description="暂无特征快照" :image-size="60" />
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({ data: { type: Object, default: () => ({}) } })

const GROUP_RULES = [
  { key: 'user', prefix: 'user_', title: '用户维度' },
  { key: 'order', prefix: 'order_', title: '订单维度' },
  { key: 'address', prefix: 'address_', title: '地址维度' },
  { key: 'other', prefix: '', title: '事件信息' },
]

const groups = computed(() => {
  const entries = Object.entries(props.data || {})
  return GROUP_RULES.map((g) => {
    const items = g.prefix
      ? entries.filter(([k]) => k.startsWith(g.prefix))
      : entries.filter(([k]) => !k.startsWith('user_') && !k.startsWith('order_') && !k.startsWith('address_'))
    return { ...g, items: items.map(([k, v]) => ({ key: k, label: k, raw: v, value: v })) }
  }).filter((g) => g.items.length)
})

const hasData = computed(() => Object.keys(props.data || {}).length > 0)

function format(v) {
  if (v === null || v === undefined || v === '') return '—'
  if (typeof v === 'number') return Number.isInteger(v) ? v : v.toFixed(2)
  return v
}
// 特征里部分为风险标志字段，命中1时高亮
function isRisky(v) {
  return v === 1 || v === true
}
</script>

<style scoped>
.snap-group { margin-bottom: 12px; }
.snap-title {
  font-size: 13px; font-weight: 600; color: #409eff;
  margin-bottom: 4px;
}
.warn { color: #f56c6c; font-weight: 600; }
</style>

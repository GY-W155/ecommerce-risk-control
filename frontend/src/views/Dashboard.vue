<template>
  <div>
    <h2 class="page-title">运营看板</h2>

    <el-row :gutter="12" style="margin-bottom: 16px">
      <el-col :span="4" v-for="c in data.cards" :key="c.label">
        <el-card class="stat-card">
          <div class="stat-label">{{ c.label }}</div>
          <div class="stat-value">{{ c.value }}<span v-if="c.suffix" class="stat-suffix">{{ c.suffix }}</span></div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="12">
      <el-col :span="12">
        <el-card class="card"><template #header>风险事件趋势（近 7 天）</template>
          <VChart :option="trendOption" height="300px" />
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card class="card"><template #header>风险等级分布</template>
          <VChart :option="levelOption" height="300px" />
        </el-card>
      </el-col>

      <el-col :span="12">
        <el-card class="card"><template #header>规则命中排行</template>
          <VChart :option="ruleOption" height="320px" />
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card class="card"><template #header>黑名单命中 / 事件类型分布</template>
          <VChart :option="blacklistOption" height="320px" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { reactive, ref, onMounted, computed } from 'vue'
import { getDashboard } from '../api'
import VChart from '../components/VChart.vue'

const data = reactive({
  cards: [], level_distribution: [], trend: [], rule_rank: [], blacklist_rank: [], event_type_distribution: [],
})

const trendOption = computed(() => ({
  xAxis: { type: 'category', data: data.trend.map((t) => t.date.slice(5)) },
  yAxis: { type: 'value' },
  series: [{ type: 'line', smooth: true, areaStyle: {}, data: data.trend.map((t) => t.count) }],
  grid: { left: 40, right: 20, top: 20, bottom: 30 },
  tooltip: { trigger: 'axis' },
}))

const levelOption = computed(() => ({
  tooltip: { trigger: 'item' },
  legend: { bottom: 0 },
  series: [{
    type: 'pie', radius: ['40%', '65%'],
    label: { formatter: '{b}: {c} ({d}%)' },
    data: data.level_distribution.map((x) => ({ name: x.label, value: x.value })),
    color: ['#67c23a', '#e6a23c', '#f56c6c'],
  }],
}))

const ruleOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  grid: { left: 120, right: 20, top: 10, bottom: 30 },
  xAxis: { type: 'value' },
  yAxis: { type: 'category', data: data.rule_rank.slice(0, 8).map((r) => r.name) },
  series: [{ type: 'bar', data: data.rule_rank.slice(0, 8).map((r) => r.value), color: '#409eff', barWidth: 12 }],
}))

const blacklistOption = computed(() => {
  const names = [...data.blacklist_rank.map((b) => b.name), ...data.event_type_distribution.map((e) => e.name)]
  const bl = data.blacklist_rank.map((b) => ({ name: b.name, value: b.value }))
  const et = data.event_type_distribution.map((e) => ({ name: e.name, value: e.value }))
  return {
    tooltip: { trigger: 'item' },
    legend: { bottom: 0 },
    series: [{
      type: 'pie', radius: ['35%', '60%'],
      label: { formatter: '{b}: {c}' },
      data: [...bl, ...et],
    }],
  }
})

async function load() {
  Object.assign(data, await getDashboard())
}
onMounted(load)
</script>

<style scoped>
.stat-card { text-align: center; }
.stat-label { color: #909399; font-size: 13px; }
.stat-value { font-size: 28px; font-weight: 700; margin-top: 6px; }
.stat-suffix { font-size: 14px; margin-left: 2px; }
</style>

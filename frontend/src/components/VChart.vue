<template>
  <div ref="el" :style="{ width: '100%', height: height }"></div>
</template>

<script setup>
import { ref, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  option: { type: Object, required: true },
  height: { type: String, default: '300px' },
})

const el = ref(null)
let chart = null

function render() {
  if (!chart) return
  chart.setOption(props.option, true)
}
function resize() { chart && chart.resize() }

onMounted(async () => {
  await nextTick()
  chart = echarts.init(el.value)
  render()
  window.addEventListener('resize', resize)
})
watch(() => props.option, render, { deep: true })
onBeforeUnmount(() => {
  window.removeEventListener('resize', resize)
  chart && chart.dispose()
})
</script>

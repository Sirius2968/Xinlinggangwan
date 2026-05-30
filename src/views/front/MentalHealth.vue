<script setup>
import { ref, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import { getMentalHealthRecords, getMentalHealthStats, deleteMentalHealthRecord } from '@/api/chat'
import { useUserStore } from '@/stores/user'
import LoginGate from '@/components/common/LoginGate.vue'
import { ElMessage } from 'element-plus'
import { useConfirm } from '@/composables/useConfirm'
import * as echarts from 'echarts'

const userStore = useUserStore()
const { confirm } = useConfirm()
const records = ref([])
const stats = ref(null)
const loading = ref(false)

// 筛选条件
const period = ref('month')
const emotionFilter = ref('')
const scoreFilter = ref(null)  // null=全部, 'low'=较差1-3, 'mid'=一般4-6, 'high'=良好7-10

const scoreOptions = [
  { label: '全部', value: null },
  { label: '良好 7-10', value: 'high' },
  { label: '一般 4-6', value: 'mid' },
  { label: '较差 1-3', value: 'low' },
]

const emotionOptions = [
  '开心', '平静', '充满希望', '感恩', '满足', '放松',
  '焦虑', '悲伤', '愤怒', '恐惧', '压力', '其他',
]
const periodOptions = [
  { label: '本周', value: 'week' },
  { label: '本月', value: 'month' },
  { label: '本年', value: 'year' },
]

// 图表 refs
const trendChartRef = ref(null)
const distChartRef = ref(null)
const levelChartRef = ref(null)
let trendChart = null
let distChart = null
let levelChart = null

const emotionColors = {
  '开心': '#67c23a',
  '平静': '#409eff',
  '充满希望': '#e6a23c',
  '感恩': '#f56c6c',
  '满足': '#67c23a',
  '放松': '#409eff',
  '焦虑': '#e6a23c',
  '悲伤': '#909399',
  '愤怒': '#f56c6c',
  '恐惧': '#e6a23c',
  '压力': '#f56c6c',
  '其他': '#409eff',
}

function moodColor(score) {
  if (score <= 3) return '#f56c6c'
  if (score <= 6) return '#e6a23c'
  return '#67c23a'
}

function moodLabel(score) {
  if (score <= 3) return '较差'
  if (score <= 6) return '一般'
  return '良好'
}

function formatDate(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  return d.toLocaleString('zh-CN', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit',
  })
}

async function loadData() {
  if (!userStore.isLoggedIn) return
  loading.value = true
  try {
    const params = { period: period.value }
    if (emotionFilter.value) params.emotion_type = emotionFilter.value
    if (scoreFilter.value) {
      const map = { low: [1, 3], mid: [4, 6], high: [7, 10] }
      params.min_score = map[scoreFilter.value][0]
      params.max_score = map[scoreFilter.value][1]
    }

    const [recRes, statsRes] = await Promise.all([
      getMentalHealthRecords(params),
      getMentalHealthStats(params),
    ])
    records.value = recRes.data || recRes || []
    stats.value = statsRes.data || statsRes || null
  } catch {
    records.value = []
    stats.value = null
  } finally {
    loading.value = false
    await nextTick()
    renderCharts()
  }
}

async function handleDelete(record) {
  const ok = await confirm('确定要删除这条记录吗？', { title: '删除确认', type: 'warning' })
  if (!ok) return
  try {
    await deleteMentalHealthRecord(record.id)
    records.value = records.value.filter(r => r.id !== record.id)
    ElMessage.success('已删除')
    await loadData()
  } catch {
    ElMessage.error('删除失败')
  }
}

// ============================================================
// ECharts 渲染
// ============================================================
function destroyCharts() {
  trendChart?.dispose()
  distChart?.dispose()
  levelChart?.dispose()
  trendChart = null
  distChart = null
  levelChart = null
}

function renderCharts() {
  destroyCharts()
  if (!stats.value) return

  // ------ 趋势折线图 ------
  if (trendChartRef.value && stats.value.trend?.length) {
    trendChart = echarts.init(trendChartRef.value)
    const data = stats.value.trend
    trendChart.setOption({
      tooltip: { trigger: 'axis', confine: true },
      grid: { left: 55, right: 55, top: 35, bottom: 80 },
      xAxis: {
        type: 'category',
        data: data.map(d => d.date),
        axisLabel: { rotate: 25, fontSize: 10, color: '#a0908a', interval: 'auto' },
        axisLine: { lineStyle: { color: '#ebcdc7' } },
      },
      yAxis: {
        type: 'value', min: 0, max: 10,
        axisLabel: { fontSize: 10, color: '#a0908a' },
        splitLine: { lineStyle: { color: '#f5e0dc', type: 'dashed' } },
      },
      series: [{
        data: data.map(d => d.score),
        type: 'line',
        smooth: true,
        lineStyle: { color: '#e6a23c', width: 2 },
        itemStyle: { color: '#e6a23c' },
        areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(230,162,60,0.25)' },
          { offset: 1, color: 'rgba(230,162,60,0.02)' },
        ])},
        markLine: {
          silent: true,
          data: [
            { yAxis: 3, lineStyle: { color: '#f56c6c', type: 'dashed' }, label: { formatter: '较差', color: '#f56c6c' } },
            { yAxis: 7, lineStyle: { color: '#67c23a', type: 'dashed' }, label: { formatter: '良好', color: '#67c23a' } },
          ],
        },
      }],
    })
  }

  // ------ 情绪分布饼图 ------
  if (distChartRef.value && stats.value.distribution?.length) {
    distChart = echarts.init(distChartRef.value)
    const data = stats.value.distribution.map(d => ({
      name: d.name,
      value: d.count,
    }))
    distChart.setOption({
      tooltip: { trigger: 'item', formatter: '{b}: {c} 次 ({d}%)', confine: true },
      legend: { type: 'scroll', bottom: 10, textStyle: { color: '#8b7a74', fontSize: 10 }, pageTextStyle: { color: '#8b7a74' } },
      series: [{
        type: 'pie',
        radius: ['40%', '65%'],
        center: ['50%', '40%'],
        itemStyle: { borderRadius: 4, borderColor: '#fff9f9', borderWidth: 2 },
        label: { show: false },
        emphasis: { label: { show: true, fontSize: 14, fontWeight: 'bold' } },
        data,
        color: ['#67c23a', '#409eff', '#e6a23c', '#f56c6c', '#909399', '#b37feb',
                '#5cdbd3', '#ff85c0', '#ffc069', '#95de64', '#69c0ff', '#ff9c6e'],
      }],
    })
  }

  // ------ 等级分布柱状图 ------
  if (levelChartRef.value && stats.value.level_distribution?.length) {
    levelChart = echarts.init(levelChartRef.value)
    const data = stats.value.level_distribution
    const colors = { '较差': '#f56c6c', '一般': '#e6a23c', '良好': '#67c23a' }
    levelChart.setOption({
      tooltip: { trigger: 'axis', confine: true },
      grid: { left: 55, right: 30, top: 35, bottom: 50 },
      xAxis: {
        type: 'category',
        data: data.map(d => d.name),
        axisLabel: { fontSize: 12, color: '#a0908a' },
        axisLine: { lineStyle: { color: '#ebcdc7' } },
      },
      yAxis: {
        type: 'value', minInterval: 1,
        axisLabel: { fontSize: 10, color: '#a0908a' },
        splitLine: { lineStyle: { color: '#f5e0dc', type: 'dashed' } },
      },
      series: [{
        type: 'bar',
        barWidth: '50%',
        data: data.map(d => ({
          value: d.count,
          itemStyle: { color: colors[d.name] || '#409eff', borderRadius: [6, 6, 0, 0] },
        })),
        label: { show: true, position: 'top', fontSize: 13, fontWeight: 'bold', color: '#8b7a74' },
      }],
    })
  }
}

// 窗口大小变化时重绘
function onResize() {
  trendChart?.resize()
  distChart?.resize()
  levelChart?.resize()
}

// 监听筛选条件变化
watch([period, emotionFilter, scoreFilter], () => {
  loadData()
})

onMounted(() => {
  loadData()
  window.addEventListener('resize', onResize)
})

onBeforeUnmount(() => {
  destroyCharts()
  window.removeEventListener('resize', onResize)
})
</script>

<template>
  <div class="mental-health-page">
    <LoginGate v-if="!userStore.isLoggedIn" message="登录后即可查看心理健康记录" />

    <template v-else>
      <!-- ===== 筛选栏 ===== -->
      <div class="filter-bar">
        <div class="filter-left">
          <el-radio-group v-model="period" size="small">
            <el-radio-button v-for="p in periodOptions" :key="p.value" :value="p.value">
              {{ p.label }}
            </el-radio-button>
          </el-radio-group>
          <el-select v-model="emotionFilter" placeholder="全部情绪" size="small" clearable style="width:130px">
            <el-option v-for="e in emotionOptions" :key="e" :label="e" :value="e" />
          </el-select>
          <div class="score-filter">
            <span class="score-filter-label">评分</span>
            <button
              v-for="opt in scoreOptions"
              :key="opt.value"
              class="score-tag"
              :class="{ active: scoreFilter === opt.value }"
              @click="scoreFilter = opt.value"
            >{{ opt.label }}</button>
          </div>
        </div>
      </div>

      <!-- ===== 统计概览卡片 ===== -->
      <div v-if="stats?.summary" class="summary-cards">
        <div class="summary-card">
          <span class="summary-num">{{ stats.summary.total_records }}</span>
          <span class="summary-label">记录总数</span>
        </div>
        <div class="summary-card">
          <span class="summary-num" :style="{ color: moodColor(stats.summary.avg_score) }">{{ stats.summary.avg_score }}</span>
          <span class="summary-label">平均评分</span>
        </div>
        <div class="summary-card">
          <span class="summary-num">{{ stats.summary.max_score }}</span>
          <span class="summary-label">最高评分</span>
        </div>
        <div class="summary-card">
          <span class="summary-num">{{ stats.summary.min_score }}</span>
          <span class="summary-label">最低评分</span>
        </div>
        <div class="summary-card">
          <span class="summary-num">{{ stats.summary.dominant_emotion || '-' }}</span>
          <span class="summary-label">主要情绪</span>
        </div>
      </div>

      <!-- ===== 图表区域 ===== -->
      <div v-if="stats" class="charts-area">
        <div class="chart-card chart-trend">
          <h3 class="chart-title">情绪评分趋势</h3>
          <div ref="trendChartRef" class="chart-box"></div>
          <div v-if="!stats.trend?.length" class="chart-empty">暂无趋势数据</div>
        </div>
        <div class="charts-row">
          <div class="chart-card chart-half">
            <h3 class="chart-title">情绪分布</h3>
            <div ref="distChartRef" class="chart-box"></div>
            <div v-if="!stats.distribution?.length" class="chart-empty">暂无分布数据</div>
          </div>
          <div class="chart-card chart-half">
            <h3 class="chart-title">等级分布</h3>
            <div ref="levelChartRef" class="chart-box"></div>
            <div v-if="!stats.level_distribution?.length" class="chart-empty">暂无等级数据</div>
          </div>
        </div>
      </div>

      <!-- ===== 加载中 ===== -->
      <div v-if="loading && !records.length" class="empty-hint">
        <p>加载中...</p>
      </div>

      <!-- ===== 空记录 ===== -->
      <div v-if="!loading && records.length === 0" class="empty-hint">
        <p>暂无心理健康记录</p>
        <span class="sub">在AI咨询中谈论情绪话题时会触发自评表单，提交后将显示在这里</span>
      </div>

      <!-- ===== 记录卡片网格 ===== -->
      <div v-if="records.length" class="records-grid">
        <div v-for="r in records" :key="r.id" class="record-card">
          <div class="record-header">
            <span class="record-tag" :style="{ background: emotionColors[r.emotion_type] || '#409eff' }">
              {{ r.emotion_type }}
            </span>
            <span class="record-date">{{ formatDate(r.created_at) }}</span>
          </div>

          <div class="record-score">
            <span class="score-label">情绪评分：</span>
            <strong class="score-num" :style="{ color: moodColor(r.mood_score) }">{{ r.mood_score }} / 10</strong>
            <span class="mood-badge" :style="{ background: moodColor(r.mood_score) }">
              {{ moodLabel(r.mood_score) }}
            </span>
          </div>

          <el-progress
            :percentage="r.mood_score * 10"
            :color="moodColor(r.mood_score)"
            :stroke-width="8"
            style="margin-top: 4px;"
          />

          <div v-if="r.description" class="record-desc">
            {{ r.description }}
          </div>

          <button class="card-delete-btn" @click="handleDelete(r)" title="删除此记录">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
            <span>删除</span>
          </button>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
/* ===== 页面整体 ===== */
.mental-health-page {
  max-width: 1020px;
  margin: 0 auto;
  padding: 24px 0;
}

.page-header {
  margin-bottom: 22px;
  text-align: center;
}

.page-header h2 {
  font-size: 24px;
  color: #8b5e5e;
  margin-bottom: 4px;
}

.page-header p {
  color: #b0928a;
  font-size: 14px;
}

/* ===== 筛选栏 ===== */
.filter-bar {
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 22px;
  padding: 10px 14px;
  background: #fff9f9;
  border: 1px solid #f5e0dc;
  border-radius: 12px;
  flex-wrap: wrap;
  gap: 8px;
}

.filter-left {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  justify-content: center;
}

.score-filter {
  display: flex;
  align-items: center;
  gap: 6px;
}

.score-filter-label {
  font-size: 12px;
  color: #b0928a;
  white-space: nowrap;
  margin-right: 2px;
}

.score-tag {
  padding: 4px 12px;
  border: 1px solid #e8d5ce;
  border-radius: 14px;
  background: #fff;
  color: #8b7a74;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap;
}

.score-tag:hover {
  background: #fef5f0;
  border-color: #d4a99a;
}

.score-tag.active {
  background: #409eff;
  color: #fff;
  border-color: #409eff;
}

/* ===== 概览卡片 ===== */
.summary-cards {
  display: flex;
  gap: 14px;
  margin-bottom: 22px;
  flex-wrap: wrap;
  justify-content: center;
}

.summary-card {
  background: #fff9f9;
  border: 1px solid #f5e0dc;
  border-radius: 12px;
  padding: 12px 10px;
  text-align: center;
  flex: 1 1 0;
  min-width: 0;
  overflow: hidden;
}

.summary-num {
  display: block;
  font-size: 22px;
  font-weight: 700;
  color: #8b5e5e;
  line-height: 1.2;
  word-break: break-all;
}

.summary-label {
  font-size: 12px;
  color: #b0928a;
  margin-top: 4px;
  display: block;
}

/* ===== 图表区域 ===== */
.charts-area {
  margin-bottom: 24px;
}

.chart-card {
  background: #fff9f9;
  border: 1px solid #f5e0dc;
  border-radius: 14px;
  padding: 18px 20px 24px;
  margin-bottom: 16px;
  margin-top: 20px;
}

.chart-title {
  font-size: 14px;
  color: #8b5e5e;
  margin: 0 0 10px;
  font-weight: 600;
}

.chart-box {
  width: 100%;
  height: 320px;
  overflow: visible !important;
}

.chart-trend .chart-box {
  height: 340px;
}

.charts-row {
  display: flex;
  gap: 16px;
}

.chart-half {
  flex: 1 1 50%;
  min-width: 0;
}

.chart-empty {
  text-align: center;
  color: #c8a89c;
  font-size: 13px;
  padding: 40px 0;
}

/* ===== 空状态 ===== */
.empty-hint {
  text-align: center;
  padding: 60px 20px;
}

.empty-icon {
  font-size: 48px;
  display: block;
  margin-bottom: 10px;
}

.empty-hint p {
  color: #b0928a;
  font-size: 15px;
}

.empty-hint .sub {
  color: #d4b8b0;
  font-size: 13px;
}

/* ===== Grid 卡片网格 ===== */
.records-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
}

/* ===== 卡片 ===== */
.record-card {
  background: #fff9f9;
  border: 1px solid #f5e0dc;
  border-radius: 14px;
  padding: 14px 16px;
  box-shadow: 0 2px 12px rgba(180, 120, 110, 0.08);
  transition: transform 0.15s, box-shadow 0.15s;
  overflow: visible;
  min-width: 0;
}

.record-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 20px rgba(180, 120, 110, 0.15);
}

/* ---- 删除按钮 ---- */
.card-delete-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  margin-top: 14px;
  padding: 5px 12px;
  border: 1px solid #ebcdc7;
  border-radius: 8px;
  background: transparent;
  color: #c8a89c;
  font-size: 12px;
  cursor: pointer;
  float: right;
  transition: background 0.15s, color 0.15s, border-color 0.15s;
}

.card-delete-btn:hover {
  background: #fde8e8;
  color: #f56c6c;
  border-color: #fbc4c4;
}

/* ---- 头部 ---- */
.record-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
  gap: 8px;
  min-width: 0;
}

.record-tag {
  padding: 4px 12px;
  border-radius: 20px;
  color: #fff;
  font-size: 12px;
  font-weight: 500;
  letter-spacing: 0.5px;
}

.record-date {
  font-size: 11px;
  color: #c8a89c;
  flex-shrink: 0;
}

/* ---- 评分 ---- */
.record-score {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  color: #8b7a74;
  margin-bottom: 10px;
  flex-wrap: wrap;
}

.score-num {
  font-size: 16px;
  font-weight: 700;
}

.mood-badge {
  padding: 2px 10px;
  border-radius: 10px;
  color: #fff;
  font-size: 12px;
  font-weight: 500;
  margin-left: 4px;
}

/* ---- 描述 ---- */
.record-desc {
  font-size: 13px;
  color: #a0908a;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #f5e0dc;
  line-height: 1.6;
  overflow-wrap: break-word;
  word-break: break-word;
}

/* ===== 响应式 ===== */
@media (max-width: 768px) {
  .charts-row {
    flex-direction: column;
  }

  .summary-cards {
    gap: 10px;
  }

  .summary-card {
    min-width: 0;
    padding: 10px 8px;
  }

  .summary-num {
    font-size: 18px;
  }

  .filter-left {
    flex-direction: column;
    width: 100%;
  }

  .filter-left > * {
    width: 100%;
  }

  .chart-box {
    height: 280px;
  }

  .chart-trend .chart-box {
    height: 300px;
  }
}
</style>

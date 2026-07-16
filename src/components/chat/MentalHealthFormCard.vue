<script setup>
import { computed } from 'vue'

const props = defineProps({
  msg: { type: Object, required: true },
})

const emit = defineEmits(['submit'])

const emotionOptions = [
  { label: '开心', icon: '😊', color: '#67c23a' },
  { label: '平静', icon: '😌', color: '#409eff' },
  { label: '充满希望', icon: '🌟', color: '#e6a23c' },
  { label: '感恩', icon: '💗', color: '#f56c6c' },
  { label: '满足', icon: '☺️', color: '#67c23a' },
  { label: '放松', icon: '🌿', color: '#409eff' },
  { label: '焦虑', icon: '😰', color: '#e6a23c' },
  { label: '悲伤', icon: '😢', color: '#909399' },
  { label: '愤怒', icon: '😤', color: '#f56c6c' },
  { label: '恐惧', icon: '😨', color: '#e6a23c' },
  { label: '压力', icon: '😫', color: '#f56c6c' },
  { label: '其他', icon: '🤔', color: '#409eff' },
]

function moodEmoji(score) {
  if (score <= 3) return '😔'
  if (score <= 5) return '😐'
  if (score <= 7) return '🙂'
  return '😊'
}

function moodColor(score) {
  if (score <= 3) return '#f56c6c'
  if (score <= 5) return '#e6a23c'
  if (score <= 7) return '#409eff'
  return '#67c23a'
}

function moodLabel(score) {
  if (score <= 3) return '较差'
  if (score <= 5) return '一般'
  if (score <= 7) return '不错'
  return '良好'
}

const ringDash = computed(() => {
  const score = props.msg.formData.mood_score || 5
  const pct = (score - 1) / 9
  const len = pct * 283
  return `${len} 283`
})
</script>

<template>
  <div class="form-card" :class="{ submitted: msg.submitted }">
    <!-- 已提交状态 -->
    <template v-if="msg.submitted">
      <div class="form-done">
        <div class="done-icon">🎉</div>
        <div class="done-content">
          <span class="done-title">已保存</span>
          <span class="done-detail">{{ msg.formData.emotion_type }} · {{ msg.formData.mood_score }}/10 分</span>
        </div>
      </div>
    </template>

    <!-- 待填写状态 -->
    <template v-else>
      <div class="form-header">
        <span class="form-icon">🧠</span>
        <div class="form-title-group">
          <span class="form-title">心理健康自评</span>
          <span class="form-subtitle">花 10 秒记录此刻的感受吧 ~</span>
        </div>
      </div>

      <!-- 情绪评分 -->
      <div class="form-section">
        <span class="section-label">当前情绪评分</span>
        <div class="score-area">
          <!-- 环形进度 + emoji -->
          <div class="score-circle-wrap">
            <svg class="score-ring" viewBox="0 0 100 100">
              <circle class="ring-bg" cx="50" cy="50" r="45" />
              <circle
                class="ring-fill"
                cx="50" cy="50" r="45"
                :style="{ strokeDasharray: ringDash, stroke: moodColor(msg.formData.mood_score) }"
              />
            </svg>
            <span class="score-emoji">{{ moodEmoji(msg.formData.mood_score) }}</span>
          </div>
          <div class="score-right">
            <div class="score-value-row">
              <span class="score-num" :style="{ color: moodColor(msg.formData.mood_score) }">
                {{ msg.formData.mood_score }}
              </span>
              <span class="score-unit">/ 10</span>
              <span class="score-label-tag" :style="{ background: moodColor(msg.formData.mood_score) }">
                {{ moodLabel(msg.formData.mood_score) }}
              </span>
            </div>
            <el-slider
              v-model="msg.formData.mood_score"
              :min="1" :max="10" :step="1"
              :show-tooltip="false"
              class="score-slider"
            />
          </div>
        </div>
      </div>

      <!-- 情绪类型 -->
      <div class="form-section">
        <span class="section-label">情绪类型</span>
        <div class="emotion-chips">
          <button
            v-for="e in emotionOptions"
            :key="e.label"
            class="emotion-chip"
            :class="{ active: msg.formData.emotion_type === e.label }"
            :style="msg.formData.emotion_type === e.label ? { background: e.color, borderColor: e.color } : {}"
            @click="msg.formData.emotion_type = e.label"
          >
            <span class="chip-emoji">{{ e.icon }}</span>
            <span class="chip-label">{{ e.label }}</span>
          </button>
        </div>
      </div>

      <!-- 补充描述 -->
      <div class="form-section">
        <span class="section-label">补充描述（可选）</span>
        <el-input
          v-model="msg.formData.description"
          type="textarea"
          :rows="2"
          maxlength="200"
          show-word-limit
          placeholder="写下想说的话..."
          class="desc-input"
        />
      </div>

      <!-- 提交按钮 -->
      <button
        class="submit-btn"
        :class="{ submitting: msg.submitting }"
        :disabled="msg.submitting"
        @click="emit('submit', msg)"
      >
        <span v-if="!msg.submitting" class="btn-content">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
            <polyline points="22 4 12 14.01 9 11.01" />
          </svg>
          保存记录
        </span>
        <span v-else class="btn-content">
          <svg class="spinner" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10" stroke-opacity="0.3" />
            <path d="M12 2a10 10 0 0 1 10 10" stroke-linecap="round" />
          </svg>
          保存中...
        </span>
      </button>
    </template>
  </div>
</template>

<style lang="scss" scoped>
// ===== 卡片容器 =====
.form-card {
  max-width: 72%;
  margin: 4px 0 20px 48px;
  background: linear-gradient(135deg, #fefefe 0%, #fdf7f3 100%);
  border: 1px solid #f0ddd4;
  border-radius: 16px;
  padding: 20px 22px;
  box-shadow: 0 2px 16px rgba(180, 120, 110, 0.08);
  transition: all 0.35s ease;
}

// ===== 已提交 =====
.form-done {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 8px 0;
}

.done-icon {
  font-size: 32px;
  flex-shrink: 0;
}

.done-content {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.done-title {
  font-size: 16px;
  font-weight: 700;
  color: #67c23a;
}

.done-detail {
  font-size: 13px;
  color: #a0908a;
}

// ===== 头部 =====
.form-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 18px;
}

.form-icon {
  font-size: 28px;
  flex-shrink: 0;
}

.form-title-group {
  display: flex;
  flex-direction: column;
}

.form-title {
  font-size: 16px;
  font-weight: 700;
  color: #5d4037;
  letter-spacing: 0.3px;
}

.form-subtitle {
  font-size: 12px;
  color: #b0958b;
  margin-top: 1px;
}

// ===== 区块 =====
.form-section {
  margin-bottom: 16px;
}

.section-label {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: #6d5b53;
  margin-bottom: 8px;
}

// ===== 评分区域 =====
.score-area {
  display: flex;
  align-items: center;
  gap: 16px;
  background: #fffaf8;
  border-radius: 12px;
  padding: 12px 16px;
  border: 1px solid #f5e8e2;
}

.score-circle-wrap {
  position: relative;
  width: 64px;
  height: 64px;
  flex-shrink: 0;
}

.score-ring {
  width: 64px;
  height: 64px;
  transform: rotate(-90deg);
}

.ring-bg {
  fill: none;
  stroke: #f0ddd4;
  stroke-width: 5;
}

.ring-fill {
  fill: none;
  stroke-width: 5;
  stroke-linecap: round;
  transition: stroke-dasharray 0.3s ease, stroke 0.3s ease;
}

.score-emoji {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  font-size: 22px;
  pointer-events: none;
}

.score-right {
  flex: 1;
  min-width: 0;
}

.score-value-row {
  display: flex;
  align-items: baseline;
  gap: 4px;
  margin-bottom: 4px;
}

.score-num {
  font-size: 28px;
  font-weight: 800;
  line-height: 1;
  transition: color 0.3s ease;
}

.score-unit {
  font-size: 13px;
  color: #b0958b;
}

.score-label-tag {
  margin-left: 6px;
  padding: 2px 10px;
  border-radius: 10px;
  color: #fff;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.5px;
}

.score-slider {
  :deep(.el-slider__runway) { margin: 0; }
  :deep(.el-slider__bar) { display: none; }
  :deep(.el-slider__button) {
    width: 16px; height: 16px;
    border: 2px solid #fff;
    box-shadow: 0 1px 6px rgba(0,0,0,0.15);
  }
}

// ===== 情绪芯片 =====
.emotion-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.emotion-chip {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 6px 12px;
  border: 1px solid #e8ddd7;
  border-radius: 20px;
  background: #fffaf8;
  font-size: 12px;
  color: #6d5b53;
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap;

  &:hover {
    border-color: #d4a99a;
    background: #fef5f0;
    transform: translateY(-1px);
  }

  &.active {
    color: #fff;
    border-color: transparent;
    box-shadow: 0 2px 8px rgba(0,0,0,0.12);
  }
}

.chip-emoji { font-size: 14px; }
.chip-label { font-weight: 500; }

// ===== 描述输入 =====
.desc-input {
  :deep(.el-textarea__inner) {
    border-radius: 10px;
    border-color: #e8ddd7;
    background: #fffaf8;
    font-size: 13px;
    resize: none;
    transition: border-color 0.2s;
    &:focus { border-color: #d4a99a; box-shadow: 0 0 0 2px rgba(212,169,154,0.15); }
  }
}

// ===== 提交按钮 =====
.submit-btn {
  width: 100%;
  padding: 10px 0;
  border: none;
  border-radius: 12px;
  background: linear-gradient(135deg, #e6a23c, #d4922a);
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.25s ease;
  box-shadow: 0 3px 12px rgba(230, 162, 60, 0.3);

  &:hover:not(:disabled) {
    background: linear-gradient(135deg, #eca840, #df9f30);
    box-shadow: 0 5px 18px rgba(230, 162, 60, 0.4);
    transform: translateY(-1px);
  }

  &:active:not(:disabled) {
    transform: translateY(0);
  }

  &.submitting {
    background: linear-gradient(135deg, #d4b896, #c9a87c);
    box-shadow: none;
    cursor: not-allowed;
  }
}

.btn-content {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.spinner {
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

// ===== 响应式 =====
@media (max-width: 640px) {
  .form-card {
    max-width: 90%;
    margin-left: 16px;
    padding: 14px 16px;
  }

  .score-area { flex-direction: column; align-items: flex-start; gap: 10px; }
  .score-circle-wrap { width: 52px; height: 52px; }
  .score-ring { width: 52px; height: 52px; }
  .score-emoji { font-size: 18px; }

  .emotion-chips { gap: 6px; }
  .emotion-chip { padding: 5px 10px; font-size: 11px; }
}
</style>

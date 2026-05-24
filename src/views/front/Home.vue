<script setup>
import { ref } from 'vue'

const carouselRef = ref(null)

// hover 暂停 / 离开恢复
function pauseCarousel() {
  carouselRef.value?.pause()
}
function resumeCarousel() {
  carouselRef.value?.play()
}
</script>

<template>
  <div class="home">
    <!-- 轮播图 -->
    <div
      class="carousel-wrapper"
      @mouseenter="pauseCarousel"
      @mouseleave="resumeCarousel"
    >
      <el-carousel ref="carouselRef" height="500px" :interval="4000" arrow="always">
        <el-carousel-item v-for="n in 5" :key="n">
          <div class="slide">
            <img
              :src="`/images/carousel/${n}.jpg`"
              :alt="`轮播图 ${n}`"
              class="slide-img"
            />
            <div class="slide-mask">
              <h2>轮播图 {{ n }}</h2>
              <p>替换 /public/images/carousel/{{ n }}.jpg 即可</p>
            </div>
          </div>
        </el-carousel-item>
      </el-carousel>
    </div>

    <!-- 简介 -->
    <div class="intro">
      <h3>心灵港湾 · 你身边的心理健康平台</h3>
      <p>提供专业的心理健康服务与知识，陪伴你走过每一个需要支持的瞬间</p>
    </div>
  </div>
</template>

<style scoped>
.home {
  text-align: center;
}

/* ===== 轮播 ===== */
.carousel-wrapper {
  max-width: 1100px;
  margin: 0 auto 40px;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.12);
}

.slide {
  height: 100%;
  position: relative;
}

.slide-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

/* 图片未替换时的占位文字遮罩 */
.slide-mask {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #fff;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  pointer-events: none;
}

.slide-mask h2 {
  font-size: 36px;
  margin-bottom: 10px;
  text-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}

.slide-mask p {
  font-size: 16px;
  opacity: 0.85;
}

/* ===== 简介 ===== */
.intro {
  padding: 24px 0;
}

.intro h3 {
  font-size: 22px;
  color: #303133;
  margin-bottom: 8px;
}

.intro p {
  color: #909399;
  font-size: 15px;
}
</style>

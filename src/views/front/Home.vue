<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const carouselRef = ref(null)

// 动画计数器
const count1 = ref(0)
const count2 = ref(0)
const count3 = ref(0)
const count4 = ref(0)
const countersStarted = ref(false)

function pauseCarousel() { carouselRef.value?.pause() }
function resumeCarousel() { carouselRef.value?.play() }

// 数字滚动动画
function animateCounter(refVal, target, duration = 2000) {
  const start = performance.now()
  function step(now) {
    const elapsed = now - start
    const progress = Math.min(elapsed / duration, 1)
    const eased = 1 - Math.pow(1 - progress, 3)
    refVal.value = Math.floor(eased * target)
    if (progress < 1) requestAnimationFrame(step)
  }
  requestAnimationFrame(step)
}

// IntersectionObserver：元素进入视口时添加动画类
let observer = null
onMounted(() => {
  observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('in-view')
        // 统计数据区域触发计数器
        if (entry.target.classList.contains('stats-section') && !countersStarted.value) {
          countersStarted.value = true
          animateCounter(count1, 450)
          animateCounter(count2, 3200)
          animateCounter(count3, 128)
          animateCounter(count4, 98)
        }
      }
    })
  }, { threshold: 0.15, rootMargin: '0px 0px -50px 0px' })

  document.querySelectorAll('.anim-item').forEach(el => observer.observe(el))
})

onBeforeUnmount(() => {
  observer?.disconnect()
})

function goTo(route) {
  router.push(route)
}
</script>

<template>
  <div class="home">
    <!-- ===== 1. 轮播图 ===== -->
    <div class="carousel-wrapper" @mouseenter="pauseCarousel" @mouseleave="resumeCarousel">
      <el-carousel ref="carouselRef" height="500px" :interval="4000" arrow="always">
        <el-carousel-item v-for="n in 5" :key="n">
          <picture>
            <source :srcset="`/images/carousel/${n}.webp`" type="image/webp" />
            <img
              :src="`/images/carousel/${n}.jpg`"
              :alt="`轮播图 ${n}`"
              class="slide-img"
              :loading="n === 1 ? undefined : 'lazy'"
              decoding="async"
            />
          </picture>
        </el-carousel-item>
      </el-carousel>
      <div class="hero-overlay">
        <h1 class="hero-title">心灵港湾</h1>
        <p class="hero-subtitle">关爱心理健康，让每一颗心都被温柔以待</p>
        <el-button type="primary" size="large" round class="hero-btn" @click="goTo('/counselors')">
          开始AI心理咨询
        </el-button>
      </div>
    </div>

    <!-- ===== 2. 快速导航卡片 ===== -->
    <section class="section nav-section">
      <h2 class="section-title anim-item">探索心灵港湾</h2>
      <p class="section-desc anim-item">我们提供全方位的心理健康服务，陪伴你的每一步成长</p>
      <div class="nav-cards">
        <div class="nav-card anim-item" @click="goTo('/counselors')">
          <div class="nav-icon">&#x1f9e0;</div>
          <h3>AI 心理咨询</h3>
          <p>7x24小时智能对话，随时倾听你的心声，提供专业的心理支持和情绪疏导</p>
          <span class="nav-link">立即体验 &rarr;</span>
        </div>
        <div class="nav-card anim-item" @click="goTo('/mental-health')">
          <div class="nav-icon">&#x1f4ca;</div>
          <h3>心理健康记录</h3>
          <p>追踪情绪变化趋势，用可视化图表了解自己的心理状态，发现改善轨迹</p>
          <span class="nav-link">查看记录 &rarr;</span>
        </div>
        <div class="nav-card anim-item" @click="goTo('/articles')">
          <div class="nav-icon">&#x1f4d6;</div>
          <h3>心理知识科普</h3>
          <p>了解心理学基础知识，学习科学的情绪管理方法，提升心理韧性</p>
          <span class="nav-link">阅读文章 &rarr;</span>
        </div>
        <div class="nav-card anim-item" @click="goTo('/counselors')">
          <div class="nav-icon">&#x1f319;</div>
          <h3>睡眠健康管理</h3>
          <p>基于CBT-I认知行为疗法的科学睡眠建议，记录追踪睡眠质量变化</p>
          <span class="nav-link">改善睡眠 &rarr;</span>
        </div>
      </div>
    </section>

    <!-- ===== 3. 什么是心理健康 ===== -->
        <section class="section what-section">
      <div class="what-container">
        <div class="what-text anim-item">
          <h2>什么是心理健康？</h2>
          <p>
            心理健康不仅仅是没有心理疾病，它是一种完满的<span class="highlight">身心状态</span>。
            世界卫生组织将心理健康定义为：个人能够<span class="highlight">发挥自身潜能</span>、
            应对正常的生活压力、卓有成效地工作，并为社区做出贡献的状态。
          </p>
          <p>
            心理健康影响着我们的<span class="highlight">思维方式、情感体验和行为模式</span>。
            它决定了我们如何处理压力、与他人相处以及做出选择。从童年到成年，心理健康在每个生命阶段都至关重要。
          </p>
          <div class="what-features">
            <div class="what-feat">
              <span class="feat-dot"></span>
              <span>情绪稳定，积极乐观</span>
            </div>
            <div class="what-feat">
              <span class="feat-dot"></span>
              <span>良好的人际关系</span>
            </div>
            <div class="what-feat">
              <span class="feat-dot"></span>
              <span>适应环境变化的能力</span>
            </div>
            <div class="what-feat">
              <span class="feat-dot"></span>
              <span>自我认知与接纳</span>
            </div>
          </div>
        </div>
        <div class="what-visual anim-item">
          <div class="visual-circle">
            <div class="visual-inner">
              <span class="visual-label">心理</span>
              <span class="visual-label">健康</span>
            </div>
          </div>
          <div class="visual-ring ring-1"></div>
          <div class="visual-ring ring-2"></div>
          <div class="visual-ring ring-3"></div>
        </div>
      </div>
    </section>
    
    <!-- ===== 4. 常见心理健康问题 ===== -->
        <section class="section issues-section">
      <h2 class="section-title anim-item">常见心理健康问题</h2>
      <p class="section-desc anim-item">了解这些问题，是关爱自己和他人的第一步</p>
      <div class="issues-grid">
        <div class="issue-card anim-item">
          <div class="issue-icon-wrap">
            <span class="issue-icon">&#x1f494;</span>
          </div>
          <h3>抑郁症</h3>
          <p>持续的悲伤、失去兴趣和愉悦感，影响日常生活和工作能力。全球超过2.8亿人受其影响，是最常见的心境障碍之一。</p>
          <div class="issue-tags">
            <span>情绪低落</span><span>兴趣减退</span><span>疲劳乏力</span>
          </div>
        </div>
        <div class="issue-card anim-item">
          <div class="issue-icon-wrap">
            <span class="issue-icon">&#x1f630;</span>
          </div>
          <h3>焦虑症</h3>
          <p>过度担忧、紧张和恐惧，可能伴有心慌、出汗、失眠等身体症状。适当的焦虑是正常的，但当它失控时需要关注。</p>
          <div class="issue-tags">
            <span>紧张不安</span><span>过度担忧</span><span>心慌气短</span>
          </div>
        </div>
        <div class="issue-card anim-item">
          <div class="issue-icon-wrap">
            <span class="issue-icon">&#x1f4a5;</span>
          </div>
          <h3>压力过载</h3>
          <p>长期高压导致的身心耗竭状态，表现为情绪耗竭、工作效率下降和人际疏离。学会管理压力是现代社会的基本技能。</p>
          <div class="issue-tags">
            <span>身心疲惫</span><span>效率下降</span><span>情绪耗竭</span>
          </div>
        </div>
        <div class="issue-card anim-item">
          <div class="issue-icon-wrap">
            <span class="issue-icon">&#x1f319;</span>
          </div>
          <h3>睡眠障碍</h3>
          <p>入睡困难、早醒、浅睡多梦等问题严重影响心理健康。长期失眠与焦虑抑郁互为因果，形成恶性循环。</p>
          <div class="issue-tags">
            <span>入睡困难</span><span>早醒多梦</span><span>日间疲劳</span>
          </div>
        </div>
        <div class="issue-card anim-item">
          <div class="issue-icon-wrap">
            <span class="issue-icon">&#x1f465;</span>
          </div>
          <h3>社交恐惧</h3>
          <p>在社交场合中感到强烈的不安和恐惧，担心被他人评判或拒绝。这不仅是"害羞"，而是一种需要重视的心理状态。</p>
          <div class="issue-tags">
            <span>回避社交</span><span>恐惧评价</span><span>强烈不安</span>
          </div>
        </div>
        <div class="issue-card anim-item">
          <div class="issue-icon-wrap">
            <span class="issue-icon">&#x1f4ad;</span>
          </div>
          <h3>创伤后应激</h3>
          <p>经历或目睹创伤事件后产生的持续性心理反应，包括闪回、噩梦、警觉性增高。专业心理咨询对康复至关重要。</p>
          <div class="issue-tags">
            <span>闪回噩梦</span><span>过度警觉</span><span>回避创伤</span>
          </div>
        </div>
      </div>
    </section>
    
    <!-- ===== 5. 忽视心理健康的危害 ===== -->
        <section class="section danger-section">
      <div class="danger-container anim-item">
        <h2>忽视心理健康的代价</h2>
        <p class="danger-subtitle">心理健康问题不会自行消失，拖延只会让情况变得更糟</p>
        <div class="danger-cards">
          <div class="danger-card">
            <div class="danger-num">01</div>
            <h3>身体健康受损</h3>
            <p>长期心理压力会削弱免疫系统，增加心血管疾病、消化系统疾病的风险。心理和身体是一个整体，相互影响不可分割。</p>
          </div>
          <div class="danger-card">
            <div class="danger-num">02</div>
            <h3>人际关系破裂</h3>
            <p>未被处理的情绪问题会导致沟通障碍、亲密关系疏离，甚至家庭破裂。愤怒、抑郁会伤害身边最亲近的人。</p>
          </div>
          <div class="danger-card">
            <div class="danger-num">03</div>
            <h3>工作学习受阻</h3>
            <p>注意力不集中、记忆力减退、创造力下降——心理问题直接影响认知功能，导致工作学习效率大幅降低。</p>
          </div>
          <div class="danger-card">
            <div class="danger-num">04</div>
            <h3>生活品质下降</h3>
            <p>失去对生活的热情和意义感，无法享受日常的美好时刻。生命不应该只是"活着"，而应该是"充满活力地活着"。</p>
          </div>
        </div>
      </div>
    </section>
    
    <!-- ===== 6. 如何正确看待心理健康 ===== -->
        <section class="section view-section">
      <h2 class="section-title anim-item">正确看待心理健康</h2>
      <div class="view-grid">
        <div class="view-card anim-item">
          <span class="view-num">1</span>
          <div>
            <h3>心理健康 = 身体健康</h3>
            <p>就像感冒了要吃药、骨折了要打石膏一样，心理"感冒"了也需要被认真对待。寻求心理帮助不是软弱，而是勇敢和智慧的表现。</p>
          </div>
        </div>
        <div class="view-card anim-item">
          <span class="view-num">2</span>
          <div>
            <h3>每个人都有脆弱时刻</h3>
            <p>人生不如意十之八九。悲伤、焦虑、愤怒都是正常的情绪反应。关键在于我们如何认识、接纳并管理这些情绪，而不是否定它们的存在。</p>
          </div>
        </div>
        <div class="view-card anim-item">
          <span class="view-num">3</span>
          <div>
            <h3>早发现、早干预、早康复</h3>
            <p>大多数心理问题在早期阶段更容易处理。拖延只会让问题固化、加重。及时寻求帮助，恢复的速度和效果都会更好。</p>
          </div>
        </div>
        <div class="view-card anim-item">
          <span class="view-num">4</span>
          <div>
            <h3>心理健康是一种能力</h3>
            <p>就像锻炼身体可以增强体质一样，心理"锻炼"（如正念、自我反思、情绪管理）可以提升心理韧性，让我们更好地应对生活的挑战。</p>
          </div>
        </div>
        <div class="view-card anim-item">
          <span class="view-num">5</span>
          <div>
            <h3>去污名化，从我做起</h3>
            <p>谈论心理健康不应该是一件羞耻的事。每一次坦诚的交流，每一次勇敢的求助，都在帮助打破社会对心理问题的偏见和歧视。</p>
          </div>
        </div>
        <div class="view-card anim-item">
          <span class="view-num">6</span>
          <div>
            <h3>你不是一个人在战斗</h3>
            <p>无论你正在经历什么，总有人愿意倾听、理解和支持你。我们的AI心理咨询师随时在线，为你的心灵提供一个安全的港湾。</p>
          </div>
        </div>
      </div>
    </section>
    
    <!-- ===== 7. 日常心理调适方法 ===== -->
        <section class="section tips-section">
      <h2 class="section-title anim-item">日常心理调适方法</h2>
      <p class="section-desc anim-item">将以下方法融入日常生活，逐步建立心理韧性</p>
      <div class="tips-grid">
        <div class="tip-card anim-item">
          <div class="tip-icon-wrap">&#x1f3c3;</div>
          <h3>规律运动</h3>
          <p>每周150分钟中等强度运动，释放内啡肽，天然的抗抑郁"药物"。跑步、游泳、瑜伽都是很好的选择。</p>
        </div>
        <div class="tip-card anim-item">
          <div class="tip-icon-wrap">&#x1f9d8;</div>
          <h3>正念冥想</h3>
          <p>每天10分钟正念练习，专注于当下，不评判地观察自己的思绪，有效降低焦虑水平。</p>
        </div>
        <div class="tip-card anim-item">
          <div class="tip-icon-wrap">&#x270d;&#xfe0f;</div>
          <h3>情绪日记</h3>
          <p>用文字记录每日情绪变化，识别触发因素和思维模式。书写本身就有疏导和整理的作用。</p>
        </div>
        <div class="tip-card anim-item">
          <div class="tip-icon-wrap">&#x1f4de;</div>
          <h3>社交连接</h3>
          <p>与信任的人保持联系，分享感受和经历。高质量的人际关系是心理健康最强有力的保护因素。</p>
        </div>
        <div class="tip-card anim-item">
          <div class="tip-icon-wrap">&#x1f3b5;</div>
          <h3>艺术表达</h3>
          <p>通过音乐、绘画、写作等方式表达内心的情感。艺术是连接潜意识与意识的桥梁。</p>
        </div>
        <div class="tip-card anim-item">
          <div class="tip-icon-wrap">&#x1f4a4;</div>
          <h3>优质睡眠</h3>
          <p>保持规律的睡眠时间表，创造舒适的睡眠环境。良好睡眠是情绪稳定的基石。</p>
        </div>
      </div>
    </section>
    
    <!-- ===== 8. 统计数据 ===== -->
        <section class="section stats-section anim-item">
      <div class="stats-grid">
        <div class="stat-item">
          <span class="stat-num">{{ count1 }}+</span>
          <span class="stat-label">累计咨询服务</span>
        </div>
        <div class="stat-item">
          <span class="stat-num">{{ count2 }}+</span>
          <span class="stat-label">注册用户</span>
        </div>
        <div class="stat-item">
          <span class="stat-num">{{ count3 }}+</span>
          <span class="stat-label">科普文章</span>
        </div>
        <div class="stat-item">
          <span class="stat-num">{{ count4 }}%</span>
          <span class="stat-label">用户满意度</span>
        </div>
      </div>
    </section>
    
    <!-- ===== 9. CTA ===== -->
        <section class="section cta-section anim-item">
      <h2>准备好了吗？</h2>
      <p>迈出第一步，就是改变的开始。我们的AI心理咨询师随时准备倾听你的故事。</p>
      <div class="cta-buttons">
        <el-button type="primary" size="large" round @click="goTo('/counselors')">开始AI心理咨询</el-button>
        <el-button size="large" round class="cta-outline" @click="goTo('/articles')">浏览心理知识</el-button>
      </div>
    </section>
    
    <!-- ===== 10. 底部 ===== -->
        <footer class="home-footer anim-item">
      <p>心灵港湾 &mdash; 关爱心理健康，让每一颗心都被温柔以待</p>
      <p class="footer-sub">如果你正处于危机中，请拨打全国心理援助热线：<strong>400-161-9995</strong></p>
    </footer>
      </div>
</template>

<style lang="scss" scoped>
/* ============================================================
   性能优化策略：
   1. 只用 transform/opacity 做动画（GPU 合成，不触发重排）
   2. 去掉 blur() 滤镜（极耗 GPU），改用 opacity
   3. 去掉无限循环浮动动画，仅保留入场 + hover
   4. will-change 预通知 GPU 创建独立合成层
   5. content-visibility: auto 跳过不可见区域的渲染
   6. prefers-reduced-motion 尊重系统动画偏好
   ============================================================ */

/* ===== 入场动画（仅执行一次） ===== */
.anim-item {
  opacity: 0;
  transform: translateY(30px);
  transition: opacity 0.6s cubic-bezier(0.25, 0.46, 0.45, 0.94), transform 0.6s cubic-bezier(0.25, 0.46, 0.45, 0.94);
  will-change: transform, opacity;
}
.anim-item.in-view {
  opacity: 1;
  transform: translateY(0);
  will-change: auto;
}
.nav-card:nth-child(1) { transition-delay: 0.05s; }
.nav-card:nth-child(2) { transition-delay: 0.12s; }
.nav-card:nth-child(3) { transition-delay: 0.19s; }
.nav-card:nth-child(4) { transition-delay: 0.26s; }
.issue-card:nth-child(1), .view-card:nth-child(1), .tip-card:nth-child(1) { transition-delay: 0.05s; }
.issue-card:nth-child(2), .view-card:nth-child(2), .tip-card:nth-child(2) { transition-delay: 0.10s; }
.issue-card:nth-child(3), .view-card:nth-child(3), .tip-card:nth-child(3) { transition-delay: 0.15s; }
.issue-card:nth-child(4), .view-card:nth-child(4), .tip-card:nth-child(4) { transition-delay: 0.20s; }
.issue-card:nth-child(5), .view-card:nth-child(5), .tip-card:nth-child(5) { transition-delay: 0.25s; }
.issue-card:nth-child(6), .view-card:nth-child(6), .tip-card:nth-child(6) { transition-delay: 0.30s; }

/* ===== 唯一保留的循环动画（仅 GPU 属性） ===== */
@keyframes pulseGlow {
  0%, 100% { box-shadow: 0 0 0 0 rgba(64, 158, 255, 0.35); }
  50% { box-shadow: 0 0 0 10px rgba(64, 158, 255, 0); }
}
@keyframes gradientShift {
  0% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
  100% { background-position: 0% 50%; }
}

/* ===== 性能基础设置 ===== */
.home { text-align: center; }

/* 跳过屏幕外区域的渲染 */
.section {
  padding: 60px 0 50px;
  content-visibility: auto;
  contain-intrinsic-size: 400px;
}

.carousel-wrapper,
.nav-section,
.cta-section,
.home-footer {
  content-visibility: visible; /* 首屏关键区域不跳过 */
}

.section-title {
  font-size: 30px; font-weight: 700; color: $color-text-title; margin-bottom: 10px;
}
.section-desc { color: $color-text-secondary; font-size: 16px; margin-bottom: 36px; }

/* ===== 1. 轮播 + 覆盖层 ===== */
.carousel-wrapper {
  position: relative;
  max-width: 1100px;
  margin: 0 auto 0;
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 4px 30px rgba(0, 0, 0, 0.15);
}
.slide-img {
  width: 100%; height: 100%; object-fit: cover; display: block;
  will-change: transform;
}
.hero-overlay {
  position: absolute; inset: 0;
  background: linear-gradient(180deg, rgba(0,0,0,0.05) 0%, rgba(0,0,0,0.55) 100%);
  display: flex; flex-direction: column; align-items: center; justify-content: flex-end;
  padding-bottom: 60px; color: #fff; pointer-events: none;
}
.hero-overlay > * { pointer-events: auto; }
.hero-title {
  font-size: 48px; font-weight: 800; margin-bottom: 8px; letter-spacing: 4px;
  text-shadow: 0 2px 12px rgba(0,0,0,0.4);
}
.hero-subtitle { font-size: 18px; margin-bottom: 28px; opacity: 0.92; text-shadow: 0 1px 6px rgba(0,0,0,0.3); }
.hero-btn {
  padding: 14px 40px; font-size: 16px;
  transition: transform 0.3s ease, box-shadow 0.3s ease;
  will-change: transform;
}
.hero-btn:hover { transform: scale(1.06); }

/* ===== 2. 导航卡片 ===== */
.nav-section { background: #fafbfc; padding-bottom: 70px; }
.nav-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 24px; max-width: 1100px; margin: 0 auto;
  contain: layout style paint;
}
.nav-card {
  background: $color-white; border-radius: 16px; padding: 32px 24px;
  box-shadow: 0 2px 16px rgba(0, 0, 0, 0.06);
  cursor: pointer;
  transition: transform 0.3s ease, box-shadow 0.3s ease;
  text-align: left;
  border: 2px solid transparent;
  will-change: transform;
}
.nav-card:hover {
  transform: translateY(-6px);
  box-shadow: 0 8px 30px rgba(64, 158, 255, 0.15);
  border-color: rgba(64, 158, 255, 0.2);
}
.nav-icon { font-size: 40px; margin-bottom: 16px; }
.nav-card h3 { font-size: 18px; color: $color-text-primary; margin-bottom: 8px; }
.nav-card p { font-size: 14px; color: $color-text-secondary; line-height: 1.7; margin-bottom: 16px; }
.nav-link { color: $color-primary; font-size: 14px; font-weight: 600; }

/* ===== 3. 什么是心理健康 ===== */
.what-section {
  background: linear-gradient(135deg, #f5f7fa 0%, #fff 50%, #f5f7fa 100%);
  background-size: 200% 200%;
  animation: gradientShift 12s ease infinite;
}
.what-container {
  display: flex; align-items: center; gap: 60px;
  max-width: 1100px; margin: 0 auto; text-align: left;
}
.what-text { flex: 1 1 55%; }
.what-text h2 { font-size: 28px; color: $color-text-title; margin-bottom: 16px; }
.what-text p { font-size: 15px; color: $color-text-regular; line-height: 1.9; margin-bottom: 16px; }
.highlight { color: $color-primary; font-weight: 600; }
.what-features { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 20px; }
.what-feat { display: flex; align-items: center; gap: 8px; font-size: 14px; color: $color-text-regular; }
.feat-dot { width: 8px; height: 8px; border-radius: 50%; background: #409eff; flex-shrink: 0; }

.what-visual { flex: 0 0 260px; position: relative; height: 260px; }
.visual-circle {
  position: absolute; inset: 20px; border-radius: 50%;
  background: linear-gradient(135deg, #409eff, #66b1ff);
  display: flex; align-items: center; justify-content: center;
  z-index: 2;
}
.visual-inner { display: flex; flex-direction: column; }
.visual-label { color: #fff; font-size: 28px; font-weight: 700; line-height: 1.4; }
.visual-ring {
  position: absolute; border-radius: 50%; border: 2px dashed #c6e2ff;
  animation: ringPulse 3s ease-in-out infinite;
}
.ring-1 { inset: 8px; animation-delay: 0s; }
.ring-2 { inset: -8px; animation-delay: 0.5s; }
.ring-3 { inset: -24px; animation-delay: 1s; }

@keyframes ringPulse {
  0%, 100% { opacity: 0.3; transform: scale(1); }
  50% { opacity: 0.8; transform: scale(1.03); }
}

/* ===== 4. 常见问题 ===== */
.issues-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 24px; max-width: 1100px; margin: 0 auto;
}
.issue-card {
  background: $color-white; border: 1px solid #ebeef5; border-radius: 14px;
  padding: 28px 24px; text-align: left;
  transition: transform 0.35s cubic-bezier(0.34, 1.56, 0.64, 1),
              box-shadow 0.35s ease,
              border-color 0.35s ease;
  animation: floatRotate 8s ease-in-out infinite;
}
.issue-card:nth-child(1) { animation-delay: 0s; }
.issue-card:nth-child(2) { animation-delay: 1.3s; }
.issue-card:nth-child(3) { animation-delay: 2.6s; }
.issue-card:nth-child(4) { animation-delay: 0.65s; }
.issue-card:nth-child(5) { animation-delay: 1.95s; }
.issue-card:nth-child(6) { animation-delay: 3.25s; }
.issue-card:hover {
  transform: translateY(-8px) rotateY(2deg) scale(1.03);
  box-shadow: 0 10px 35px rgba(0,0,0,0.12);
  border-color: rgba(64, 158, 255, 0.4);
}
.issue-icon-wrap { margin-bottom: 14px; }
.issue-icon { font-size: 36px; }
.issue-card h3 { font-size: 18px; color: $color-text-primary; margin-bottom: 8px; }
.issue-card p { font-size: 14px; color: $color-text-secondary; line-height: 1.7; margin-bottom: 14px; }
.issue-tags { display: flex; gap: 8px; flex-wrap: wrap; }
.issue-tags span {
  padding: 3px 10px; border-radius: 12px; font-size: 12px;
  background: #ecf5ff; color: $color-primary;
}

/* ===== 5. 忽视危害 ===== */
.danger-section { background: #fef0f0; }
.danger-container { max-width: 1100px; margin: 0 auto; }
.danger-container h2 { font-size: 28px; color: $color-text-title; margin-bottom: 8px; }
.danger-subtitle { color: $color-text-secondary; margin-bottom: 36px; }
.danger-cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 20px; }
.danger-card {
  background: $color-white; border-radius: 14px; padding: 24px 20px;
  text-align: left; border-left: 4px solid #f56c6c;
  transition: transform 0.35s cubic-bezier(0.34, 1.56, 0.64, 1),
              box-shadow 0.35s ease,
              border-left-width 0.3s ease;
  animation: floatUpDown 7s ease-in-out infinite;
}
.danger-card:nth-child(1) { animation-delay: 0s; }
.danger-card:nth-child(2) { animation-delay: 1.75s; }
.danger-card:nth-child(3) { animation-delay: 3.5s; }
.danger-card:nth-child(4) { animation-delay: 5.25s; }
.danger-card:hover {
  transform: translateY(-8px) scale(1.02);
  box-shadow: 0 8px 30px rgba(245, 108, 108, 0.2);
  border-left-width: 8px;
}
.danger-num { font-size: 32px; font-weight: 800; color: #fde2e2; margin-bottom: 8px; }
.danger-card h3 { font-size: 16px; color: $color-text-primary; margin-bottom: 8px; }
.danger-card p { font-size: 13px; color: $color-text-secondary; line-height: 1.7; }

/* ===== 6. 正确看待 ===== */
.view-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 20px; max-width: 1100px; margin: 0 auto; }
.view-card {
  display: flex; gap: 16px; text-align: left;
  background: $color-white; border-radius: 14px; padding: 24px 20px;
  border: 1px solid #ebeef5;
  transition: transform 0.35s cubic-bezier(0.34, 1.56, 0.64, 1),
              box-shadow 0.35s ease,
              background 0.4s ease;
}
.view-card:hover {
  transform: translateY(-6px) perspective(500px) rotateX(2deg);
  box-shadow: 0 10px 30px rgba(0,0,0,0.1);
  background: #f8fbff;
}
.view-num {
  width: 40px; height: 40px; border-radius: 50%;
  background: linear-gradient(135deg, #409eff, #66b1ff);
  background-size: 200% 200%;
  animation: gradientShift 4s ease infinite;
  color: #fff; font-size: 18px; font-weight: 700;
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
  transition: transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.view-card:hover .view-num { transform: scale(1.15); }
.view-card h3 { font-size: 16px; color: $color-text-primary; margin: 0 0 6px; }
.view-card p { font-size: 13px; color: $color-text-secondary; line-height: 1.7; margin: 0; }

/* ===== 7. 调适方法 ===== */
.tips-section { background: #fafbfc; }
.tips-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 20px; max-width: 1100px; margin: 0 auto; }
.tip-card {
  background: $color-white; border-radius: 14px; padding: 28px 18px;
  transition: transform 0.35s cubic-bezier(0.34, 1.56, 0.64, 1),
              box-shadow 0.35s ease;
  animation: floatUpDown 5s ease-in-out infinite;
}
.tip-card:nth-child(1) { animation-delay: 0s; }
.tip-card:nth-child(2) { animation-delay: 0.8s; }
.tip-card:nth-child(3) { animation-delay: 1.6s; }
.tip-card:nth-child(4) { animation-delay: 2.4s; }
.tip-card:nth-child(5) { animation-delay: 3.2s; }
.tip-card:nth-child(6) { animation-delay: 4.0s; }
.tip-card:hover {
  transform: translateY(-8px) scale(1.04);
  box-shadow: 0 10px 30px rgba(0,0,0,0.12);
}
.tip-icon-wrap {
  font-size: 36px; margin-bottom: 12px;
  transition: transform 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
  display: inline-block;
}
.tip-card:hover .tip-icon-wrap { transform: scale(1.3) rotate(-10deg); }
.tip-icon-wrap { font-size: 36px; margin-bottom: 12px; }
.tip-card h3 { font-size: 16px; color: $color-text-primary; margin-bottom: 8px; }
.tip-card p { font-size: 13px; color: $color-text-secondary; line-height: 1.7; }

/* ===== 8. 统计 ===== */
.stats-section {
  background: linear-gradient(135deg, #409eff, #337ecc, #409eff);
  background-size: 200% 200%;
  animation: gradientShift 8s ease infinite;
  padding: 56px 0;
  position: relative;
  z-index: 1;
}
.stats-section::before {
  content: '';
  position: absolute; inset: 0;
  background: radial-gradient(circle at 30% 50%, rgba(255,255,255,0.1) 0%, transparent 50%),
              radial-gradient(circle at 70% 50%, rgba(255,255,255,0.05) 0%, transparent 50%);
  animation: bgPulse 5s ease-in-out infinite;
  pointer-events: none;
}
.stats-grid { display: flex; justify-content: center; gap: 80px; flex-wrap: wrap; max-width: 1000px; margin: 0 auto; position: relative; z-index: 1; }
.stat-item { text-align: center; animation: floatUpDown 4s ease-in-out infinite; }
.stat-item:nth-child(1) { animation-delay: 0s; }
.stat-item:nth-child(2) { animation-delay: 1s; }
.stat-item:nth-child(3) { animation-delay: 2s; }
.stat-item:nth-child(4) { animation-delay: 3s; }
.stat-num {
  display: block; font-size: 48px; font-weight: 800; color: #fff; line-height: 1.2;
  text-shadow: 0 0 20px rgba(255,255,255,0.3);
  transition: transform 0.3s ease;
}
.stat-item:hover .stat-num { transform: scale(1.1); }
.stat-label { font-size: 15px; color: rgba(255,255,255,0.8); margin-top: 6px; display: block; }

/* ===== 9. CTA ===== */
.cta-section {
  padding: 64px 0;
  position: relative;
  z-index: 1;
}
.cta-section h2 {
  font-size: 30px; color: $color-text-title; margin-bottom: 10px;
  transition: transform 0.3s ease;
}
.cta-section:hover h2 { transform: scale(1.03); }
.cta-section p { color: $color-text-secondary; margin-bottom: 30px; }
.cta-buttons { display: flex; gap: 16px; justify-content: center; flex-wrap: wrap; }
.cta-buttons .el-button {
  transition: transform 0.35s cubic-bezier(0.34, 1.56, 0.64, 1),
              box-shadow 0.35s ease;
}
.cta-buttons .el-button:hover {
  transform: translateY(-4px) scale(1.05);
  box-shadow: 0 8px 25px rgba(64, 158, 255, 0.3);
}
.cta-outline { border-color: $color-primary; color: $color-primary; }

/* ===== 10. 底部 ===== */
.home-footer { padding: 40px 20px; border-top: 1px solid #ebeef5; color: $color-text-secondary; font-size: 14px; }
.footer-sub { margin-top: 8px; font-size: 13px; }

/* ===== 响应式 ===== */
@media (max-width: 768px) {
  .hero-title { font-size: 32px; }
  .hero-subtitle { font-size: 15px; }
  .hero-overlay { padding-bottom: 40px; }
  .carousel-wrapper { border-radius: 0; }
  .what-container { flex-direction: column; gap: 30px; }
  .what-visual { flex: 0 0 200px; width: 200px; }
  .stats-grid { gap: 40px; }
  .stat-num { font-size: 36px; }
  .nav-cards { grid-template-columns: 1fr; }
  .issues-grid, .view-grid { grid-template-columns: 1fr; }
  .danger-cards { grid-template-columns: 1fr; }
  .tips-grid { grid-template-columns: repeat(2, 1fr); }
  .section-title { font-size: 24px; }
  .section { padding: 40px 0 30px; }
}
</style>

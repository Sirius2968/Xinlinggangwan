<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useArticleStore } from '@/stores/articles'
import { useUserStore } from '@/stores/user'
import { ElMessage } from 'element-plus'
import { listArticles, toggleArticleFavorite, getUserFavorites } from '@/api/articles'
import BaseDialog from '@/components/common/BaseDialog.vue'

const router = useRouter()
const store = useArticleStore()
const userStore = useUserStore()
const showFavoritesOnly = ref(false)
const sharedArticles = ref([])
const sharedFavIds = ref(new Set())  // 当前用户已收藏的社区文章 ID（按账号隔离）

const displayArticles = computed(() =>
  showFavoritesOnly.value ? store.favoritedArticles : store.filteredArticles
)

function handleCardClick(article) {
  store.openArticle(article)
}

function requireLogin(msg) {
  if (!userStore.isLoggedIn) {
    ElMessage.warning(msg || '请先登录')
    router.push('/login')
    return false
  }
  return true
}

function handleToggleFavorite(e, articleId) {
  e.stopPropagation()
  if (!requireLogin('请先登录后再收藏')) return
  store.toggleFavorite(articleId)
}

function handleDetailFavorite(articleId) {
  if (!requireLogin('请先登录后再收藏')) return
  store.toggleFavorite(articleId)
}

const relatedArticles = computed(() =>
  store.selectedArticle ? store.getRelatedArticles(store.selectedArticle) : []
)

// ===== 社区分享文章 =====
async function loadSharedArticles() {
  try {
    const [listRes, favRes] = await Promise.all([
      listArticles(),
      userStore.isLoggedIn ? getUserFavorites() : Promise.resolve({ code: 200, data: [] }),
    ])
    if (listRes.code === 200) sharedArticles.value = listRes.data
    if (favRes.code === 200) sharedFavIds.value = new Set(favRes.data)
  } catch { /* ignore */ }
}

function isSharedFavorited(id) {
  return sharedFavIds.value.has(id)
}

async function handleSharedFavorite(article) {
  if (!requireLogin('请先登录后再收藏')) return
  const isFav = isSharedFavorited(article.id)
  try {
    const res = await toggleArticleFavorite(article.id, isFav ? 'remove' : 'add')
    if (res.code === 200) {
      const next = new Set(sharedFavIds.value)
      if (isFav) { next.delete(article.id) }
      else { next.add(article.id) }
      sharedFavIds.value = next
      article.favorite_count = res.data.favorite_count
    }
  } catch { /* ignore */ }
}

onMounted(() => loadSharedArticles())
</script>

<template>
  <div class="articles-page">
    <!-- 页面头部 -->
    <div class="page-header">
      <h1>心理知识科普</h1>
      <p>了解心理学知识，学会科学地关爱自己和他人</p>
    </div>

    <!-- 搜索栏 -->
    <div class="toolbar">
      <div class="search-wrap">
        <span class="search-icon">&#x1f50d;</span>
        <input
          v-model="store.searchQuery"
          type="text"
          placeholder="搜索文章标题、标签..."
          class="search-input"
        />
        <button v-if="store.searchQuery" class="search-clear" @click="store.setSearchQuery('')">
          &times;
        </button>
      </div>
      <button
        class="favorite-toggle"
        :class="{ active: showFavoritesOnly }"
        @click="showFavoritesOnly = !showFavoritesOnly"
      >
        &#x2764; 收藏 ({{ store.favoriteCount }})
      </button>
    </div>

    <!-- 分类标签 -->
    <div class="category-tabs">
      <button
        v-for="cat in store.categories"
        :key="cat"
        class="cat-tab"
        :class="{ active: store.activeCategory === cat }"
        @click="store.setCategory(cat)"
      >
        {{ cat }}
      </button>
    </div>

    <!-- 文章网格 -->
    <div v-if="displayArticles.length > 0" class="articles-grid">
      <div
        v-for="article in displayArticles"
        :key="article.id"
        class="article-card"
        @click="handleCardClick(article)"
      >
        <div class="card-icon">{{ article.icon }}</div>
        <div class="card-body">
          <div class="card-top">
            <span class="card-category">{{ article.category }}</span>
            <span class="card-time">{{ article.readTime }}</span>
          </div>
          <h3>{{ article.title }}</h3>
          <p>{{ article.summary }}</p>
          <div class="card-tags">
            <span v-for="tag in article.tags" :key="tag" class="tag">{{ tag }}</span>
          </div>
        </div>
        <button
          class="favorite-card-btn"
          :class="{ favorited: store.isFavorited(article.id) }"
          @click="handleToggleFavorite($event, article.id)"
        >
          {{ store.isFavorited(article.id) ? '&#x2764; 已收藏' : '&#x1f90f; 收藏' }}
        </button>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-else class="empty-state">
      <div class="empty-icon">&#x1f4da;</div>
      <p v-if="showFavoritesOnly">还没有收藏任何文章</p>
      <p v-else>没有找到匹配的文章</p>
      <button v-if="showFavoritesOnly" class="empty-action" @click="showFavoritesOnly = false">
        浏览全部文章
      </button>
      <button v-else class="empty-action" @click="store.setSearchQuery(''); store.setCategory('全部')">
        清除筛选
      </button>
    </div>

    <!-- ===== 社区分享文章 ===== -->
    <div v-if="sharedArticles.length > 0" class="shared-section">
      <div class="shared-header">
        <h2>社区分享</h2>
        <router-link to="/article-share" class="shared-more">查看更多 &rarr;</router-link>
      </div>
      <div class="shared-grid">
        <div v-for="article in sharedArticles.slice(0, 6)" :key="article.id" class="shared-card">
          <div class="shared-top">
            <h4>{{ article.title }}</h4>
            <div class="shared-tags" v-if="article.tags">
              <span v-for="tag in article.tags.split(',').filter(Boolean).slice(0, 3)" :key="tag" class="stag">{{ tag.trim() }}</span>
            </div>
          </div>
          <p>{{ article.content.slice(0, 120) }}{{ article.content.length > 120 ? '...' : '' }}</p>
          <div class="shared-bottom">
            <span class="shared-author">&#x1f464; {{ article.author }}</span>
            <span class="shared-date">{{ article.created_at?.slice(0, 10) || '' }}</span>
            <button
              class="shared-fav"
              :class="{ active: isSharedFavorited(article.id) }"
              @click="handleSharedFavorite(article)"
            >
              &#x2764; {{ article.favorite_count || 0 }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 文章详情弹窗 -->
    <BaseDialog
      :model-value="!!store.selectedArticle"
      :title="store.selectedArticle?.title || ''"
      width="680px"
      :show-footer="false"
      @close="store.closeArticle()"
    >
      <template v-if="store.selectedArticle">
        <div class="article-detail">
          <div class="detail-meta">
            <span class="detail-category">{{ store.selectedArticle.category }}</span>
            <span class="detail-time">{{ store.selectedArticle.readTime }}</span>
            <button
              class="detail-fav"
              :class="{ favorited: store.isFavorited(store.selectedArticle.id) }"
              @click="handleDetailFavorite(store.selectedArticle.id)"
            >
              {{ store.isFavorited(store.selectedArticle.id) ? '&#x2764; 已收藏' : '&#x1f90f; 收藏' }}
            </button>
          </div>
          <div class="detail-content">{{ store.selectedArticle.content }}</div>
          <div class="detail-tags">
            <span v-for="tag in store.selectedArticle.tags" :key="tag" class="tag">{{ tag }}</span>
          </div>
          <div v-if="relatedArticles.length > 0" class="related-section">
            <h4>相关文章</h4>
            <div class="related-list">
              <div
                v-for="rel in relatedArticles"
                :key="rel.id"
                class="related-item"
                @click="store.openArticle(rel)"
              >
                <span class="related-icon">{{ rel.icon }}</span>
                <div>
                  <strong>{{ rel.title }}</strong>
                  <p>{{ rel.summary.slice(0, 50) }}...</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </template>
    </BaseDialog>
  </div>
</template>

<style scoped>
.articles-page { max-width: 1100px; margin: 0 auto; }

/* ===== 头部 ===== */
.page-header { text-align: center; padding: 40px 0 24px; }
.page-header h1 { font-size: 30px; font-weight: 700; color: #2c3e50; margin-bottom: 8px; }
.page-header p { color: #909399; font-size: 15px; }

/* ===== 搜索栏 ===== */
.toolbar { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; }
.search-wrap { flex: 1; position: relative; display: flex; align-items: center; }
.search-icon { position: absolute; left: 14px; font-size: 16px; pointer-events: none; }
.search-input {
  width: 100%; padding: 10px 40px 10px 40px;
  border: 1px solid #dcdfe6; border-radius: 10px; font-size: 14px;
  outline: none; transition: border-color 0.25s, box-shadow 0.25s;
}
.search-input:focus { border-color: #409eff; box-shadow: 0 0 0 3px rgba(64,158,255,0.12); }
.search-clear {
  position: absolute; right: 10px; border: none; background: none;
  font-size: 18px; cursor: pointer; color: #c0c4cc; padding: 0 4px; line-height: 1;
}
.search-clear:hover { color: #909399; }
.favorite-toggle {
  flex-shrink: 0; padding: 10px 18px; border: 1px solid #dcdfe6; border-radius: 10px;
  background: #fff; font-size: 14px; cursor: pointer; color: #606266;
  transition: all 0.25s; white-space: nowrap;
}
.favorite-toggle:hover { border-color: #f56c6c; color: #f56c6c; }
.favorite-toggle.active { background: #fef0f0; border-color: #f56c6c; color: #f56c6c; font-weight: 600; }

/* ===== 分类标签 ===== */
.category-tabs { display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 24px; }
.cat-tab {
  padding: 8px 18px; border: 1px solid #ebeef5; border-radius: 20px;
  background: #fff; font-size: 14px; color: #606266; cursor: pointer; transition: all 0.25s;
}
.cat-tab:hover { border-color: #409eff; color: #409eff; }
.cat-tab.active { background: #409eff; color: #fff; border-color: #409eff; font-weight: 600; }

/* ===== 文章网格 ===== */
.articles-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 20px; }
.article-card {
  background: #fff; border-radius: 14px; padding: 24px;
  border: 1px solid #ebeef5; cursor: pointer; position: relative;
  display: flex; gap: 16px;
  transition: transform 0.3s cubic-bezier(0.34,1.56,0.64,1), box-shadow 0.3s ease, border-color 0.3s ease;
}
.article-card:hover { transform: translateY(-4px); box-shadow: 0 8px 28px rgba(0,0,0,0.1); border-color: rgba(64,158,255,0.25); }
.card-icon { font-size: 32px; flex-shrink: 0; width: 48px; height: 48px; display: flex; align-items: center; justify-content: center; background: #f5f7fa; border-radius: 12px; }
.card-body { flex: 1; min-width: 0; }
.card-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.card-category { font-size: 12px; color: #409eff; background: #ecf5ff; padding: 2px 10px; border-radius: 10px; }
.card-time { font-size: 12px; color: #c0c4cc; }
.article-card h3 { font-size: 16px; color: #303133; margin-bottom: 8px; line-height: 1.4; }
.article-card p {
  font-size: 13px; color: #909399; line-height: 1.6; margin-bottom: 12px;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
}
.card-tags { display: flex; gap: 6px; flex-wrap: wrap; padding-bottom: 28px; }
.tag { padding: 2px 8px; border-radius: 8px; font-size: 11px; background: #f5f7fa; color: #909399; }

/* 收藏按钮 — 右下角 */
.favorite-card-btn {
  position: absolute; bottom: 16px; right: 16px;
  border: 1px solid #ebeef5; border-radius: 8px;
  background: #fff; font-size: 13px; cursor: pointer;
  padding: 4px 12px; color: #c0c4cc;
  transition: all 0.2s;
}
.favorite-card-btn:hover { border-color: #f56c6c; color: #f56c6c; transform: scale(1.05); }
.favorite-card-btn.favorited { border-color: #f56c6c; color: #f56c6c; background: #fef0f0; }

/* ===== 空状态 ===== */
.empty-state { text-align: center; padding: 60px 20px; color: #909399; }
.empty-icon { font-size: 48px; margin-bottom: 16px; }
.empty-state p { font-size: 15px; margin-bottom: 16px; }
.empty-action {
  padding: 10px 24px; border: 1px solid #409eff; border-radius: 20px;
  background: #fff; color: #409eff; font-size: 14px; cursor: pointer; transition: all 0.25s;
}
.empty-action:hover { background: #ecf5ff; }

/* ===== 文章详情弹窗 ===== */
.article-detail { text-align: left; }
.detail-meta { display: flex; align-items: center; gap: 16px; margin-bottom: 20px; padding-bottom: 16px; border-bottom: 1px solid #ebeef5; }
.detail-category { font-size: 13px; color: #409eff; background: #ecf5ff; padding: 3px 12px; border-radius: 10px; }
.detail-time { font-size: 13px; color: #c0c4cc; }
.detail-fav {
  margin-left: auto; border: 1px solid #dcdfe6; border-radius: 8px;
  background: #fff; font-size: 13px; cursor: pointer; padding: 4px 12px;
  color: #909399; transition: all 0.2s;
}
.detail-fav:hover { border-color: #f56c6c; color: #f56c6c; }
.detail-fav.favorited { background: #fef0f0; border-color: #f56c6c; color: #f56c6c; }
.detail-content { font-size: 14px; color: #606266; line-height: 1.9; white-space: pre-line; margin-bottom: 20px; }
.detail-tags { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 24px; }
.related-section { border-top: 1px solid #ebeef5; padding-top: 20px; }
.related-section h4 { font-size: 15px; color: #303133; margin-bottom: 12px; }
.related-list { display: flex; flex-direction: column; gap: 10px; }
.related-item {
  display: flex; align-items: center; gap: 12px; padding: 12px;
  border-radius: 10px; border: 1px solid #ebeef5; cursor: pointer; transition: all 0.2s;
}
.related-item:hover { background: #f8fbff; border-color: #c6e2ff; }
.related-icon { font-size: 24px; flex-shrink: 0; }
.related-item strong { display: block; font-size: 14px; color: #303133; margin-bottom: 2px; }
.related-item p { font-size: 12px; color: #c0c4cc; margin: 0; }

/* ===== 社区分享文章 ===== */
.shared-section {
  margin-top: 48px; padding-top: 32px;
  border-top: 2px solid #ebeef5;
}
.shared-header {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 20px;
}
.shared-header h2 { font-size: 22px; color: #2c3e50; }
.shared-more { font-size: 14px; color: #409eff; text-decoration: none; }
.shared-more:hover { text-decoration: underline; }
.shared-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
}
.shared-card {
  background: #fff; border: 1px solid #ebeef5; border-radius: 12px;
  padding: 18px; transition: box-shadow 0.3s ease;
}
.shared-card:hover { box-shadow: 0 4px 18px rgba(0,0,0,0.07); }
.shared-top { margin-bottom: 8px; }
.shared-top h4 { font-size: 15px; color: #303133; margin-bottom: 6px; }
.shared-tags { display: flex; gap: 4px; flex-wrap: wrap; }
.stag {
  padding: 1px 8px; border-radius: 8px; font-size: 11px;
  background: #f0f9eb; color: #67c23a;
}
.shared-card p {
  font-size: 13px; color: #909399; line-height: 1.6; margin-bottom: 12px;
}
.shared-bottom {
  display: flex; align-items: center; gap: 12px;
  font-size: 12px; color: #c0c4cc;
}
.shared-author { color: #606266; }
.shared-date { flex: 1; }
.shared-fav {
  border: 1px solid #fde2e2; border-radius: 6px;
  background: #fff; font-size: 12px; cursor: pointer;
  padding: 2px 10px; color: #f56c6c; transition: all 0.2s;
}
.shared-fav:hover { background: #fef0f0; }
.shared-fav.active { background: #fef0f0; border-color: #f56c6c; }

/* ===== 响应式 ===== */
@media (max-width: 768px) {
  .articles-grid { grid-template-columns: 1fr; }
  .page-header { padding: 20px 0 16px; }
  .page-header h1 { font-size: 24px; }
  .toolbar { flex-direction: column; }
  .favorite-toggle { width: 100%; text-align: center; }
  .shared-grid { grid-template-columns: 1fr; }
}

</style>

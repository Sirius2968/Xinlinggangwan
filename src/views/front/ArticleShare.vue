<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { useArticleStore } from '@/stores/articles'
import { myArticles, listArticles, toggleArticleFavorite, getUserFavorites, createArticle, updateArticle, deleteArticle } from '@/api/articles'
import { ElMessage } from 'element-plus'
import { useConfirm } from '@/composables/useConfirm'
import BaseDialog from '@/components/common/BaseDialog.vue'
import LoginGate from '@/components/common/LoginGate.vue'

const router = useRouter()
const userStore = useUserStore()
const articleStore = useArticleStore()
const { confirm: confirmFn } = useConfirm()

const tab = ref('my') // 'my' | 'favorites'
const articles = ref([])
const favArticles = ref([]) // 收藏的社区文章
const showDialog = ref(false)
const editId = ref(null)
const form = ref({ title: '', content: '', tags: '' })
const submitting = ref(false)

async function loadMyArticles() {
  try {
    const res = await myArticles()
    if (res.code === 200) articles.value = res.data
  } catch { /* ignore */ }
}

async function loadFavArticles() {
  try {
    const [listRes, favRes] = await Promise.all([
      listArticles(),
      getUserFavorites(),
    ])
    if (favRes.code === 200 && listRes.code === 200) {
      const ids = new Set(favRes.data)
      favArticles.value = listRes.data.filter(a => ids.has(a.id))
    }
  } catch { /* ignore */ }
}

function loadData() {
  if (tab.value === 'my') loadMyArticles()
  else loadFavArticles()
}

function switchTab(t) {
  tab.value = t
  loadData()
}

// 收藏的内置文章（来自 Pinia store）
const favBuiltinArticles = computed(() => articleStore.favoritedArticles)

async function handleRemoveFav(article) {
  try {
    const res = await toggleArticleFavorite(article.id, 'remove')
    if (res.code === 200) {
      article.favorite_count = res.data.favorite_count
      favArticles.value = favArticles.value.filter(a => a.id !== article.id)
    }
  } catch { /* ignore */ }
}

// ===== 文章 CRUD =====
function openCreate() {
  editId.value = null
  form.value = { title: '', content: '', tags: '' }
  showDialog.value = true
}

function openEdit(article) {
  editId.value = article.id
  form.value = { title: article.title, content: article.content, tags: article.tags || '' }
  showDialog.value = true
}

async function handleSubmit() {
  if (!form.value.title.trim() || !form.value.content.trim()) {
    ElMessage.warning('请填写标题和内容')
    return
  }
  submitting.value = true
  try {
    const data = {
      title: form.value.title.trim(),
      content: form.value.content.trim(),
      tags: form.value.tags.trim(),
    }
    if (editId.value) {
      await updateArticle(editId.value, data)
      ElMessage.success('更新成功')
    } else {
      await createArticle(data)
      ElMessage.success('发布成功')
    }
    showDialog.value = false
    await loadMyArticles()
  } catch { ElMessage.error('操作失败') }
  finally { submitting.value = false }
}

async function handleDelete(article) {
  const ok = await confirmFn('确定要删除这篇文章吗？', { title: '删除确认', type: 'warning' })
  if (!ok) return
  try {
    await deleteArticle(article.id)
    ElMessage.success('已删除')
    await loadMyArticles()
  } catch { ElMessage.error('删除失败') }
}

onMounted(() => {
  articleStore.loadArticles()
  if (userStore.isLoggedIn) loadData()
})
</script>

<template>
  <div class="share-page">
    <LoginGate v-if="!userStore.isLoggedIn" message="登录后即可发布和管理你的心理知识文章" />

    <template v-else>
      <!-- 头部 -->
      <div class="page-header">
        <h1>心理知识分享</h1>
        <p>发布你的心理知识文章，浏览你收藏的内容</p>
      </div>

      <!-- 标签切换 -->
      <div class="tab-bar">
        <button :class="{ active: tab === 'my' }" @click="switchTab('my')">我的文章</button>
        <button :class="{ active: tab === 'favorites' }" @click="switchTab('favorites')">我的收藏</button>
        <el-button v-if="tab === 'my'" type="primary" round class="publish-btn" @click="openCreate">
          &#x270d; 发布文章
        </el-button>
      </div>

      <!-- ===== 我的文章 ===== -->
      <template v-if="tab === 'my'">
        <div v-if="articles.length > 0" class="article-list">
          <div v-for="article in articles" :key="article.id" class="article-card">
            <div class="card-header">
              <h3>{{ article.title }}</h3>
              <div class="card-tags" v-if="article.tags">
                <span v-for="tag in article.tags.split(',').filter(Boolean)" :key="tag" class="tag">
                  {{ tag.trim() }}
                </span>
              </div>
            </div>
            <p class="card-content">{{ article.content.slice(0, 250) }}{{ article.content.length > 250 ? '...' : '' }}</p>
            <div class="card-footer">
              <span class="time">{{ article.created_at?.slice(0, 10) || '' }}</span>
              <div class="card-actions">
                <button class="edit-btn" @click="openEdit(article)">编辑</button>
                <button class="del-btn" @click="handleDelete(article)">删除</button>
              </div>
            </div>
          </div>
        </div>
        <div v-else class="empty-state">
          <div class="empty-icon">&#x1f4dd;</div>
          <p>你还没有发布过文章</p>
          <el-button type="primary" round @click="openCreate">写一篇文章</el-button>
        </div>
      </template>

      <!-- ===== 我的收藏 ===== -->
      <template v-if="tab === 'favorites'">
        <!-- 内置文章收藏 -->
        <div v-if="favBuiltinArticles.length > 0" class="fav-section">
          <h3 class="fav-section-title">心理知识</h3>
          <div class="fav-grid">
            <div v-for="article in favBuiltinArticles" :key="'b'+article.id" class="fav-card">
              <span class="fav-icon">{{ article.icon }}</span>
              <div class="fav-info">
                <strong>{{ article.title }}</strong>
                <p>{{ article.summary.slice(0, 60) }}...</p>
                <span class="fav-cat">{{ article.category }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 社区文章收藏 -->
        <div v-if="favArticles.length > 0" class="fav-section">
          <h3 class="fav-section-title">社区分享</h3>
          <div class="article-list">
            <div v-for="article in favArticles" :key="'s'+article.id" class="article-card">
              <div class="card-header">
                <h3>{{ article.title }}</h3>
                <div class="card-tags" v-if="article.tags">
                  <span v-for="tag in article.tags.split(',').filter(Boolean)" :key="tag" class="tag">
                    {{ tag.trim() }}
                  </span>
                </div>
              </div>
              <p class="card-content">{{ article.content.slice(0, 200) }}{{ article.content.length > 200 ? '...' : '' }}</p>
              <div class="card-footer">
                <div class="card-meta">
                  <span class="author">&#x1f464; {{ article.author }}</span>
                  <span class="time">{{ article.created_at?.slice(0, 10) || '' }}</span>
                </div>
                <button class="unfav-btn" @click="handleRemoveFav(article)">取消收藏</button>
              </div>
            </div>
          </div>
        </div>

        <!-- 收藏空状态 -->
        <div v-if="favBuiltinArticles.length === 0 && favArticles.length === 0" class="empty-state">
          <div class="empty-icon">&#x2764;</div>
          <p>还没有收藏任何文章</p>
          <router-link to="/articles" class="go-browse">去心理知识页面浏览</router-link>
        </div>
      </template>

      <!-- 写文章弹窗 -->
      <BaseDialog
        v-model="showDialog"
        :title="editId ? '编辑文章' : '发布文章'"
        width="620px"
        confirm-text="发布"
        :loading="submitting"
        @confirm="handleSubmit"
      >
        <div class="form-group">
          <label>标题</label>
          <el-input v-model="form.title" placeholder="文章标题" maxlength="200" />
        </div>
        <div class="form-group">
          <label>标签 <span class="hint">（逗号分隔，如：焦虑, 正念, 自我调适）</span></label>
          <el-input v-model="form.tags" placeholder="焦虑, 正念, 自我调适" maxlength="500" />
        </div>
        <div class="form-group">
          <label>内容</label>
          <el-input
            v-model="form.content"
            type="textarea"
            :rows="10"
            placeholder="分享你的心理知识、心得或感悟..."
            maxlength="5000"
            show-word-limit
          />
        </div>
      </BaseDialog>
    </template>
  </div>
</template>

<style scoped>
.share-page { max-width: 900px; margin: 0 auto; }

/* ===== 头部 ===== */
.page-header { text-align: center; padding: 40px 0 24px; }
.page-header h1 { font-size: 30px; font-weight: 700; color: #2c3e50; margin-bottom: 8px; }
.page-header p { color: #909399; font-size: 15px; }

/* ===== 标签切换 ===== */
.tab-bar {
  display: flex; align-items: center; gap: 0;
  margin-bottom: 24px; border-bottom: 2px solid #ebeef5;
}
.tab-bar button {
  padding: 10px 28px; border: none; background: none;
  font-size: 15px; color: #909399; cursor: pointer;
  border-bottom: 2px solid transparent; margin-bottom: -2px;
  transition: all 0.25s;
}
.tab-bar button:hover { color: #409eff; }
.tab-bar button.active { color: #409eff; border-bottom-color: #409eff; font-weight: 600; }
.publish-btn { margin-left: auto; margin-bottom: -2px; }

/* ===== 文章卡片列表 ===== */
.article-list { display: flex; flex-direction: column; gap: 16px; }
.article-card {
  background: #fff; border: 1px solid #ebeef5; border-radius: 14px;
  padding: 24px; transition: box-shadow 0.3s ease, transform 0.2s ease;
}
.article-card:hover { box-shadow: 0 4px 20px rgba(0,0,0,0.08); transform: translateY(-2px); }
.card-header { margin-bottom: 12px; }
.card-header h3 { font-size: 18px; color: #303133; margin-bottom: 8px; }
.card-tags { display: flex; gap: 6px; flex-wrap: wrap; }
.tag { padding: 2px 10px; border-radius: 10px; font-size: 12px; background: #ecf5ff; color: #409eff; }
.card-content { font-size: 14px; color: #606266; line-height: 1.7; margin-bottom: 16px; }
.card-footer { display: flex; align-items: center; justify-content: space-between; }
.card-meta { display: flex; gap: 16px; font-size: 13px; color: #909399; }
.author { color: #606266; font-weight: 500; }
.time { color: #c0c4cc; }
.card-actions { display: flex; align-items: center; gap: 8px; }

.edit-btn, .del-btn {
  border: 1px solid #ebeef5; border-radius: 6px;
  background: #fff; font-size: 12px; cursor: pointer; padding: 4px 10px;
  color: #909399; transition: all 0.2s;
}
.edit-btn:hover { border-color: #409eff; color: #409eff; }
.del-btn:hover { border-color: #f56c6c; color: #f56c6c; }

.unfav-btn {
  border: 1px solid #fde2e2; border-radius: 6px;
  background: #fff; font-size: 12px; cursor: pointer; padding: 4px 10px;
  color: #f56c6c; transition: all 0.2s;
}
.unfav-btn:hover { background: #fef0f0; }

/* ===== 收藏区域 ===== */
.fav-section { margin-bottom: 32px; }
.fav-section-title { font-size: 16px; color: #303133; margin-bottom: 12px; padding-left: 4px; }
.fav-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 12px; }
.fav-card {
  display: flex; align-items: center; gap: 14px;
  background: #fff; border: 1px solid #ebeef5; border-radius: 12px;
  padding: 16px; transition: box-shadow 0.2s;
}
.fav-card:hover { box-shadow: 0 4px 16px rgba(0,0,0,0.06); }
.fav-icon { font-size: 28px; flex-shrink: 0; }
.fav-info { min-width: 0; }
.fav-info strong { display: block; font-size: 14px; color: #303133; margin-bottom: 4px; }
.fav-info p { font-size: 12px; color: #909399; margin: 0 0 4px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.fav-cat { font-size: 11px; color: #409eff; background: #ecf5ff; padding: 1px 8px; border-radius: 8px; }

/* ===== 空状态 ===== */
.empty-state { text-align: center; padding: 80px 20px; color: #909399; }
.empty-icon { font-size: 48px; margin-bottom: 16px; }
.empty-state p { font-size: 15px; margin-bottom: 16px; }
.go-browse { color: #409eff; text-decoration: none; font-size: 14px; }
.go-browse:hover { text-decoration: underline; }

/* ===== 表单 ===== */
.form-group { margin-bottom: 18px; }
.form-group label { display: block; font-size: 14px; color: #303133; margin-bottom: 6px; font-weight: 500; }
.hint { font-weight: 400; color: #c0c4cc; font-size: 12px; }

/* ===== 响应式 ===== */
@media (max-width: 768px) {
  .page-header { padding: 20px 0 16px; }
  .page-header h1 { font-size: 24px; }
  .tab-bar { flex-wrap: wrap; gap: 0; }
  .publish-btn { width: 100%; margin-top: 8px; }
  .fav-grid { grid-template-columns: 1fr; }
}
</style>

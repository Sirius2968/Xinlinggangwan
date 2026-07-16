import { ref, shallowRef, computed } from 'vue'
import { defineStore } from 'pinia'
import { getKnowledgeArticles, toggleKnowledgeFavorite } from '@/api/articles'

const CATEGORIES = ['全部', '自我调适', '心理问题', '治疗方法', '人际关系']

export const useArticleStore = defineStore('articles', () => {
  // ---- 状态 ----
  const articles = shallowRef([])          // 从数据库加载的文章列表
  const favorites = ref(new Set())         // 当前用户收藏的文章 ID
  const searchQuery = ref('')
  const activeCategory = ref('全部')
  const selectedArticle = shallowRef(null)
  const loading = ref(false)               // 是否正在加载

  // ---- 计算属性 ----
  const categories = computed(() => CATEGORIES)

  const filteredArticles = computed(() => {
    let result = articles.value
    if (activeCategory.value !== '全部') {
      result = result.filter((a) => a.category === activeCategory.value)
    }
    if (searchQuery.value.trim()) {
      const q = searchQuery.value.trim().toLowerCase()
      result = result.filter(
        (a) =>
          a.title.toLowerCase().includes(q) ||
          a.tags.some((t) => t.toLowerCase().includes(q)) ||
          a.summary.toLowerCase().includes(q),
      )
    }
    return result
  })

  const favoritedArticles = computed(() =>
    articles.value.filter((a) => favorites.value.has(a.id)),
  )

  const favoriteCount = computed(() => favorites.value.size)

  // ---- 方法 ----

  /** 从数据库加载知识文章 */
  async function loadArticles() {
    if (loading.value) return
    loading.value = true
    try {
      const res = await getKnowledgeArticles()
      if (res.code === 200) {
        articles.value = res.data
        // 同步服务端返回的收藏状态
        const favIds = new Set()
        res.data.forEach((a) => {
          if (a.isFavorited) favIds.add(a.id)
        })
        favorites.value = favIds
      }
    } catch {
      // 网络错误时保持现有数据
    } finally {
      loading.value = false
    }
  }

  function setCategory(cat) {
    activeCategory.value = cat
  }

  function setSearchQuery(q) {
    searchQuery.value = q
  }

  function openArticle(article) {
    selectedArticle.value = article
  }

  function closeArticle() {
    selectedArticle.value = null
  }

  /** 收藏/取消收藏（数据库持久化） */
  async function toggleFavorite(articleId) {
    const isFav = favorites.value.has(articleId)
    try {
      const res = await toggleKnowledgeFavorite(articleId, isFav ? 'remove' : 'add')
      if (res.code === 200) {
        const next = new Set(favorites.value)
        if (isFav) {
          next.delete(articleId)
        } else {
          next.add(articleId)
        }
        favorites.value = next
      }
    } catch {
      // 忽略网络错误
    }
  }

  function isFavorited(articleId) {
    return favorites.value.has(articleId)
  }

  function getRelatedArticles(article, count = 3) {
    return articles.value
      .filter((a) => a.id !== article.id && a.tags.some((t) => article.tags.includes(t)))
      .slice(0, count)
  }

  return {
    articles,
    favorites,
    searchQuery,
    activeCategory,
    selectedArticle,
    loading,
    categories,
    filteredArticles,
    favoritedArticles,
    favoriteCount,
    loadArticles,
    setCategory,
    setSearchQuery,
    openArticle,
    closeArticle,
    toggleFavorite,
    isFavorited,
    getRelatedArticles,
  }
})

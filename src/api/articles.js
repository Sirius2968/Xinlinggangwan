import request from '@/utils/request'

/** 发布文章 */
export function createArticle(data) {
  return request.post('/articles/', data)
}

/** 获取所有分享文章 */
export function listArticles() {
  return request.get('/articles/')
}

/** 获取自己的文章 */
export function myArticles() {
  return request.get('/articles/my')
}

/** 编辑文章 */
export function updateArticle(articleId, data) {
  return request.put(`/articles/${articleId}`, data)
}

/** 删除文章 */
export function deleteArticle(articleId) {
  return request.delete(`/articles/${articleId}`)
}

/** 收藏/取消收藏文章 */
export function toggleArticleFavorite(articleId, action) {
  return request.post(`/articles/${articleId}/favorite?action=${action}`)
}

/** 获取当前用户收藏的文章 ID 列表 */
export function getUserFavorites() {
  return request.get('/articles/favorites')
}

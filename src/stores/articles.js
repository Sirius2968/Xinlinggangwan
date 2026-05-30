import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { useUserStore } from '@/stores/user'

/**
 * 心理知识文章数据
 * 每篇文章包含：id, title, summary, content, category, tags, readTime, icon
 */
const ARTICLE_DATA = [
  {
    id: 1,
    title: '什么是认知行为疗法（CBT）？',
    summary: '认知行为疗法是目前最主流的心理治疗方法之一，通过改变不合理的思维模式来改善情绪和行为。',
    content: '认知行为疗法（Cognitive Behavioral Therapy，简称CBT）由Aaron Beck在20世纪60年代创立。它的核心观点是：影响我们情绪和行为的不是事件本身，而是我们对事件的看法和解释。\n\nCBT帮助来访者识别自动化的负面思维（如"我什么都做不好"），检验这些思维的真实性，并用更平衡、更现实的思维方式替代它们。\n\nCBT通常包含以下步骤：识别问题情境 → 记录自动思维 → 挑战不合理信念 → 发展替代性思维 → 行为实验验证。大量研究证明CBT对抑郁症、焦虑症、强迫症等心理问题具有显著疗效。',
    category: '治疗方法',
    tags: ['CBT', '认知行为', '心理治疗', '抑郁', '焦虑'],
    readTime: '5分钟',
    icon: '🧠',
  },
  {
    id: 2,
    title: '正念冥想入门指南',
    summary: '正念冥想是一种训练注意力和觉察力的方法，帮助你活在当下，减少焦虑和压力。',
    content: '正念（Mindfulness）源自佛教禅修传统，由Jon Kabat-Zinn在1979年引入西方医学领域，创立了正念减压（MBSR）项目。\n\n正念的核心是"有意识地、不加评判地关注当下"。这听起来简单，但实践起来需要持续练习。\n\n基础正念呼吸练习：找个安静的地方坐下 → 闭上眼睛 → 将注意力放在呼吸上 → 当思绪飘走时，温和地将注意力带回呼吸 → 每次练习5-10分钟。\n\n研究显示，持续8周的正念练习可以显著降低焦虑水平、改善睡眠质量、增强专注力和情绪调节能力。',
    category: '自我调适',
    tags: ['正念', '冥想', '减压', '焦虑', '专注力'],
    readTime: '4分钟',
    icon: '🧘',
  },
  {
    id: 3,
    title: '焦虑症：不只是"想太多"',
    summary: '焦虑症是最常见的心理障碍之一，了解它的症状和应对方法对每个人都很有帮助。',
    content: '焦虑是人类正常的情绪反应，但当焦虑变得过度、持续，并严重影响日常生活时，就可能发展为焦虑障碍。\n\n常见类型包括：广泛性焦虑障碍（GAD）、惊恐障碍、社交焦虑障碍、特定恐惧症等。\n\n典型症状：持续的担忧和紧张、心慌心悸、出汗手抖、肌肉紧绷、睡眠困难、注意力难以集中。\n\n应对方法：规律运动（每周150分钟中等强度）、练习深呼吸（4-7-8呼吸法）、正念冥想、限制咖啡因摄入、保持规律作息。如果自我调节效果不佳，建议寻求专业心理咨询或精神科医生的帮助。',
    category: '心理问题',
    tags: ['焦虑', '焦虑症', '心理健康', '自我调适'],
    readTime: '4分钟',
    icon: '😰',
  },
  {
    id: 4,
    title: '睡眠与心理健康的双向关系',
    summary: '睡眠问题与心理健康密不可分，改善睡眠是维护心理健康的重要一环。',
    content: '睡眠与心理健康存在密切的双向关系：心理问题会导致睡眠困难，而长期睡眠不足又会诱发或加重心理问题。\n\n失眠的认知行为疗法（CBT-I）是国际公认的一线治疗方案，包含以下核心策略：\n1. 刺激控制：只在感到困倦时上床，如果20分钟内无法入睡就起床，将床只与睡眠关联\n2. 睡眠限制：减少在床上的时间，提高睡眠效率\n3. 认知重建：纠正对睡眠的不合理信念（如"我必须睡满8小时"）\n4. 放松训练：渐进式肌肉放松、腹式呼吸\n\n良好的睡眠卫生习惯：固定起床时间、睡前1小时不看屏幕、卧室温度适宜、避免睡前饮酒及咖啡因。',
    category: '自我调适',
    tags: ['睡眠', '失眠', 'CBT-I', '心理健康', '放松'],
    readTime: '4分钟',
    icon: '😴',
  },
  {
    id: 5,
    title: '抑郁症的早期识别与应对',
    summary: '了解抑郁症的早期信号，及时寻求帮助，是走出抑郁的关键第一步。',
    content: '抑郁症不是简单的"心情不好"，而是一种需要认真对待的心境障碍。全球约有2.8亿人患有抑郁症。\n\n早期识别信号：持续两周以上的情绪低落、对曾经喜欢的事物失去兴趣、食欲或体重显著变化、失眠或嗜睡、精力减退易疲劳、自我价值感降低、注意力难以集中、反复出现死亡或自杀念头。\n\n如果你或身边的人出现以上多个症状，请：到精神科或心理科就诊评估、接受心理咨询（如CBT或人际关系疗法）、遵医嘱服药（如需要）、建立规律的生活作息。\n\n记住，抑郁症是可以治疗的，寻求帮助是勇敢而非软弱的表现。',
    category: '心理问题',
    tags: ['抑郁', '抑郁症', '早期识别', '心理健康'],
    readTime: '4分钟',
    icon: '💙',
  },
  {
    id: 6,
    title: '情绪管理：成为情绪的主人',
    summary: '情绪管理不是压抑情绪，而是学会健康地识别、表达和调节情绪。',
    content: '情绪管理（Emotion Regulation）是心理健康的基石能力之一。\n\n五大核心策略：\n1. 情绪觉察：学会命名和描述自己的情绪（"我感到焦虑是因为..."）\n2. 接纳而非对抗：允许负面情绪存在，不评判自己\n3. 认知重评：从不同角度看待引发情绪的事件\n4. 表达而非压抑：通过书写、倾诉、艺术等方式表达情绪\n5. 生理调节：运动、呼吸、放松训练从身体层面调节情绪\n\n日常生活中可以实践：每天花3分钟做情绪"体检"扫描、建立情绪日记习惯、使用"STOP"技巧（Stop暂停-Take a breath呼吸-Observe观察-Proceed继续）。\n\n情绪本身没有好坏，关键在于我们如何与之相处。',
    category: '自我调适',
    tags: ['情绪管理', '情绪调节', '认知重评', '自我关怀'],
    readTime: '4分钟',
    icon: '🎭',
  },
  {
    id: 7,
    title: '人际关系与心理健康',
    summary: '高质量的人际关系是心理健康最有力的保护因素之一。',
    content: '哈佛大学长达75年的追踪研究发现，良好的人际关系是幸福和健康的最重要预测因素。\n\n人际关系如何影响心理健康：提供情感支持和归属感、作为压力缓冲器、帮助获得新的视角和解决问题的方法、增强自我价值感。\n\n建立健康人际关系的技巧：学会积极倾听（专注于理解而非回应）、表达真实的感受和需求（非暴力沟通）、设立健康的边界、主动关心他人、学会处理冲突而非回避。\n\n社交孤立是心理健康的危险因素，如果你感到孤独，可以从小的社交行为开始：加入兴趣小组、定期联系老朋友、参加志愿活动。',
    category: '人际关系',
    tags: ['人际关系', '社交', '沟通', '孤独', '幸福感'],
    readTime: '4分钟',
    icon: '🤝',
  },
  {
    id: 8,
    title: '自我关怀：对自己温柔一点',
    summary: '自我关怀是一种在困难时刻对自己友善和理解的实践，是心理健康的重要组成部分。',
    content: '自我关怀（Self-Compassion）由Kristin Neff教授提出，包含三个核心要素：\n1. 自我友善：对待自己像对待好朋友一样温柔，而非严厉批评\n2. 共同人性：认识到困难和痛苦是人类共同的经历，你并不孤单\n3. 正念觉察：客观地观察自己的痛苦，不过度认同也不回避\n\n实践练习：\n- 自我关怀日记：每天写下1-2件让你感到困难的事，然后用关怀的语气给自己回应\n- 自我关怀暂停：当感到压力时，把手放在心口，深呼吸，对自己说"这一刻很困难，但我会陪伴自己度过"\n- 写给自己的一封信：以无条件接纳你的朋友的身份给自己写一封信\n\n研究显示，自我关怀水平越高，焦虑抑郁水平越低，生活满意度越高。',
    category: '自我调适',
    tags: ['自我关怀', '自我友善', '正念', '心理韧性'],
    readTime: '4分钟',
    icon: '💗',
  },
  {
    id: 9,
    title: '压力管理：化压力为动力',
    summary: '适度的压力是成长的机会，学会科学管理压力是现代人必备的能力。',
    content: '压力不是必须被消除的敌人。耶克斯-多德森定律告诉我们：适度的压力能带来最佳表现。关键在于将压力保持在合理范围。\n\n压力管理工具箱：\n- 身体层面：规律运动、深呼吸、渐进式肌肉放松、充足的睡眠\n- 心理层面：认知重构（将"威胁"视为"挑战"）、正念练习、感恩日记\n- 行为层面：时间管理、任务优先级排序、学会说"不"\n- 社交层面：寻求支持、表达感受、帮助他人（助人可降低压力激素）\n\n警惕职业倦怠信号：持续疲惫、工作热情丧失、效率显著下降。出现这些信号时请及时调整。',
    category: '自我调适',
    tags: ['压力', '压力管理', '倦怠', '时间管理', '放松'],
    readTime: '4分钟',
    icon: '⚡',
  },
  {
    id: 10,
    title: '青少年心理健康：家长指南',
    summary: '青春期是心理健康问题的易发期，家长的理解和支持至关重要。',
    content: '青少年期（12-18岁）是大脑发育的关键期，也是心理健康问题的高发期。约1/5的青少年会经历心理健康问题。\n\n家长可以做什么：\n1. 保持开放的沟通渠道：少评判多倾听，创造安全的表达空间\n2. 观察变化：注意睡眠、食欲、社交、学业方面的突然变化\n3. 尊重隐私与边界：在给予空间和保持关注之间找到平衡\n4. 示范健康的应对方式：孩子从家长身上学习如何处理情绪\n5. 减少屏幕时间：鼓励户外活动和面对面社交\n\n何时需要寻求专业帮助：情绪问题持续两周以上、出现自伤行为或自杀念头、严重影响日常生活和学业。\n\n全国青少年心理援助热线：12355',
    category: '人际关系',
    tags: ['青少年', '青春期', '家长', '家庭教育', '心理健康'],
    readTime: '5分钟',
    icon: '🌱',
  },
  {
    id: 11,
    title: '创伤与心理恢复',
    summary: '创伤经历会对心理产生深远影响，但通过正确的支持和治疗，恢复是可能的。',
    content: '心理创伤是指经历或目睹威胁生命或安全的事件后产生的心理反应。常见的创伤后反应包括：闪回（仿佛重新经历创伤）、噩梦、过度警觉、回避与创伤相关的情境、情绪麻木。\n\n创伤后应激障碍（PTSD）的诊断要求症状持续超过一个月且严重影响功能。但请注意，大多数经历创伤的人并不会发展为PTSD。\n\n有效的治疗方法：\n- 创伤聚焦的认知行为疗法（TF-CBT）\n- 眼动脱敏与再加工治疗（EMDR）\n- 叙事暴露疗法（NET）\n\n恢复过程中的自我照顾：建立安全感、重建对生活的掌控感、与支持性的人保持联系、允许自己以自己的节奏恢复。',
    category: '心理问题',
    tags: ['创伤', 'PTSD', '心理恢复', 'EMDR', '安全感'],
    readTime: '4分钟',
    icon: '🕊️',
  },
  {
    id: 12,
    title: '建立心理韧性的六个习惯',
    summary: '心理韧性不是天生的，而是可以通过日常练习培养的能力。',
    content: '心理韧性（Resilience）是指面对逆境、创伤或重大压力时的适应和反弹能力。好消息是，它可以被培养。\n\n六个关键习惯：\n1. 保持乐观但不脱离现实：关注可控因素，接受不可控因素\n2. 建立支持网络：至少维护2-3个可以深度交流的关系\n3. 保持身体活动：运动提升内啡肽和脑源性神经营养因子\n4. 培养意义感：找到比自身更大的目标或信仰\n5. 拥抱变化与不确定性：视变化为成长的机会\n6. 练习感恩：每天记录3件值得感谢的事\n\n心理韧性不是避免痛苦，而是在痛苦中找到继续前行的力量。',
    category: '自我调适',
    tags: ['心理韧性', '适应力', '成长', '感恩', '习惯'],
    readTime: '4分钟',
    icon: '🏋️',
  },
]

const CATEGORIES = ['全部', '自我调适', '心理问题', '治疗方法', '人际关系']

// 按账号隔离的 localStorage key
function favoritesKey() {
  const userStore = useUserStore()
  const uid = userStore.userInfo?.id
  return uid ? `article_favorites_${uid}` : 'article_favorites'
}

// 从 localStorage 读取收藏
function loadFavorites() {
  try {
    return new Set(JSON.parse(localStorage.getItem(favoritesKey()) || '[]'))
  } catch {
    return new Set()
  }
}

export const useArticleStore = defineStore('articles', () => {
  // ---- 状态 ----
  const articles = ref(ARTICLE_DATA)
  const favorites = ref(loadFavorites())
  const searchQuery = ref('')
  const activeCategory = ref('全部')
  const selectedArticle = ref(null)

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
          a.summary.toLowerCase().includes(q)
      )
    }
    return result
  })

  const favoritedArticles = computed(() =>
    articles.value.filter((a) => favorites.value.has(a.id))
  )

  const favoriteCount = computed(() => favorites.value.size)

  // ---- 方法 ----
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

  function toggleFavorite(articleId) {
    const newSet = new Set(favorites.value)
    if (newSet.has(articleId)) {
      newSet.delete(articleId)
    } else {
      newSet.add(articleId)
    }
    favorites.value = newSet
    localStorage.setItem(favoritesKey(), JSON.stringify([...newSet]))
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
    categories,
    filteredArticles,
    favoritedArticles,
    favoriteCount,
    setCategory,
    setSearchQuery,
    openArticle,
    closeArticle,
    toggleFavorite,
    isFavorited,
    getRelatedArticles,
  }
})

"""
对话路由辅助函数 —— 关键词检测与表单触发逻辑
"""

# 用户情绪好转的关键词（心情改善时鼓励记录情绪）
_IMPROVEMENT_KEYWORDS = [
    "好多了", "好一些", "好点了", "好多啦", "感觉好",
    "好转", "好很多", "好多",
    "开心了", "平静了", "放松了", "舒服多",
    "想通了", "释然", "轻松", "放下来", "想开",
]

# AI 建议记录的关键词（命中则触发表单）
_RECORD_SUGGEST_KEYWORDS = [
    "记录", "自评", "表单", "填写", "评估", "追踪",
]

# 睡眠相关关键词（睡眠话题不触发心理健康表单）
_SLEEP_KEYWORDS = [
    "睡眠", "失眠", "入睡", "早醒", "浅睡", "多梦", "熬夜",
    "睡觉", "睡不着", "睡不好", "睡不深", "噩梦", "作息",
    "就寝", "起床时间", "睡眠质量",
]


def should_trigger_form(user_message: str, ai_response: str = "") -> bool:
    """检测是否应触发心理健康表单：
    1. 用户表示心情好转 → 鼓励记录
    2. AI 主动建议记录 → 触发
    注意：睡眠相关话题不弹，用 sleep_tracker 工具处理
    """
    # 睡眠话题不弹
    if any(kw in user_message for kw in _SLEEP_KEYWORDS):
        return False
    if any(kw in ai_response for kw in _SLEEP_KEYWORDS):
        return False

    if any(kw in user_message for kw in _IMPROVEMENT_KEYWORDS):
        return True
    if any(kw in ai_response for kw in _RECORD_SUGGEST_KEYWORDS):
        return True
    return False


def check_ownership(session, user: dict | None):
    """校验对话是否属于当前用户。session.user_id 为 NULL 视为匿名对话。
    返回 None 表示校验通过；返回 JSONResponse 表示鉴权/授权失败（由路由直接 return）。"""
    if session.user_id is None:
        return None
    if user is None:
        from schemas import fail
        return fail(401, "请先登录")
    if str(session.user_id) != str(user["user_id"]):
        from schemas import fail
        return fail(403, "无权访问此对话")
    return None

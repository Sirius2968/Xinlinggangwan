"""
数据库配置 —— SQLite + SQLAlchemy
"""

import json
import os
import random
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# 数据库文件存放在 backend 目录下
DATABASE_URL = "sqlite:///./psychology.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI 依赖注入：每个请求获取一个数据库会话，请求结束后关闭"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def seed_knowledge_articles():
    """首次启动时从 JSON 文件填充心理知识文章"""
    from models import KnowledgeArticle

    db = SessionLocal()
    try:
        if db.query(KnowledgeArticle).count() > 0:
            return

        seed_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "seed_data.json")
        with open(seed_file, "r", encoding="utf-8") as f:
            articles = json.load(f)

        for a in articles:
            db.add(KnowledgeArticle(**a))
        db.commit()
        print(f"[数据库] 已填充 {len(articles)} 篇心理知识文章")
    finally:
        db.close()


def seed_shared_articles():
    """首次启动时为 Sirius 用户创建示例社区分享文章"""
    from models import User, SharedArticle

    db = SessionLocal()
    try:
        existing = db.query(SharedArticle).count()
        if existing > 0:
            return

        sirius = db.query(User).filter(User.username == "Sirius").first()
        if not sirius:
            return

        articles = [
            {
                "title": "我的CBT治疗经历：从怀疑到受益",
                "content": "最初听说认知行为疗法的时候，我是持怀疑态度的。改变想法就能改变情绪？听起来太过简单了。\n\n但在咨询师的引导下，我开始记录自己的自动思维。我发现每当工作中出现问题，我的第一反应总是\"这全是我的错\"。通过CBT的思维记录表，我学会了识别这种\"个人化\"的认知歪曲，并尝试用更客观的视角看待问题。\n\n三个月后，我的焦虑水平明显下降了。CBT教会我的是：想法不等于事实，我们有能力选择如何看待发生在我们身上的事情。\n\n如果你也在犹豫是否尝试心理咨询，我的建议是：勇敢迈出第一步，你可能会像我一样收获意想不到的成长。",
                "tags": "CBT,个人经历,焦虑,心理咨询",
            },
            {
                "title": "坚持正念冥想一年后的变化",
                "content": "一年前读了一篇关于正念冥想的文章，决定每天练习10分钟。说实话，前两周真的很难坚持——坐着不动、专注于呼吸，脑子里却像开了水龙头一样思绪不断。\n\n第一个月，我学会了不评判自己的\"走神\"，温柔地把注意力带回来。第三个月，发现自己对情绪的反应变得不那么自动了。以前遇到令人烦躁的事会立刻发火，现在好像多了一个\"暂停\"的空间。\n\n最大的变化是睡眠质量的提升。以前需要半小时以上才能入睡，现在基本10分钟内就能睡着。而且即使半夜醒来，也能很快重新入睡。\n\n第六个月时，我开始和同事们分享这个习惯，组建了一个\"午间冥想小组\"，每天中午一起练习5分钟。\n\n一年后的今天，正念已经成了我生活中不可或缺的一部分。它不是\"让我没有负面情绪\"，而是让我能和任何情绪和平共处。",
                "tags": "正念,冥想,个人成长,坚持,睡眠",
            },
            {
                "title": "陪伴抑郁症朋友的一年：我的心得体会",
                "content": "去年，我最好的朋友被诊断为中度抑郁症。在那之前，我对抑郁症的了解仅限于\"心情不好\"。这一年的陪伴让我学到了很多。\n\n以下是我的一些心得：\n\n1. 不要说\"加油\"或\"想开点\"。这不是意志力的问题，就像你不能让一个骨折的人\"用力站起来\"一样。\n\n2. 用行动代替言语。帮她带一顿饭，陪她散个步，帮她整理一下房间——这些具体的小事比任何大道理都有用。\n\n3. 照顾好自己。陪伴抑郁的人很消耗，如果你自己也垮了，就无法继续支持对方。\n\n4. 鼓励但不强迫专业求助。多次温和地建议她去看心理咨询师，最终她同意了，这是她好转的转折点。\n\n5. 耐心是最好的礼物。恢复是一个螺旋上升的过程，会有反复。只要你在，你就是在帮助她。\n\n现在她已经基本康复了。她说，在她最黑暗的时候，知道有一个人从未放弃她，是她坚持下去的重要力量。",
                "tags": "抑郁症,陪伴,朋友,支持,经历分享",
            },
            {
                "title": "冥想初学者最常犯的五个错误",
                "content": "作为一个冥想练习了三年的人，回顾自己刚开始时的种种误区，发现很多初学者都会犯相似的错。\n\n错误1：追求\"完全放空\"。很多人以为冥想是什么都不想，结果越努力越焦虑。冥想不是停止思考，而是观察思考。思绪飘走很正常，发现它、把它带回来，这就是冥想的过程。\n\n错误2：太在意姿势和时间。非要盘腿坐、非要半小时——这些执念反而成了障碍。坐在椅子上、床上，哪怕只有3分钟，只要你在练习，就是好的。\n\n错误3：期待立竿见影的效果。冥想是一个\"慢\"过程，需要持续练习。我差不多练了两个月才开始感觉到变化。急不来。\n\n错误4：只在焦虑时才练。就像健身不能只在生病时才去一样，把冥想变成日常习惯效果最好。固定时间（比如早起后或睡前）更容易坚持。\n\n错误5：频繁切换冥想类型和应用。今天用这个app的正念，明天试那个引导——选一个合适的，坚持至少一个月再说。\n\n希望这些经验能帮到刚开始冥想旅程的你！",
                "tags": "冥想,初学者,经验,正念,误区",
            },
            {
                "title": "如何在快节奏的城市里找到内心平静",
                "content": "生活在快节奏的城市，地铁、加班、社交媒体……每天都被各种信息轰炸。去年我经历了一段严重的burnout，后来慢慢摸索出了一些在都市里保持内心平静的方法。\n\n1. 建立\"数字日落\"：晚上9点后不碰手机。起初很难，我用一本实体书替代了刷手机的习惯。一周后睡眠质量明显改善。\n\n2. 通勤时间的正念：地铁上不看手机，而是做\"五感觉察\"练习——看到什么、听到什么、闻到什么、身体有什么感觉。15分钟的通勤变成了15分钟的练习。\n\n3. 找到你的\"城市绿洲\"：我在公司附近发现了一个小公园，每天午饭后去坐10分钟。不一定要去郊区才能接触自然。\n\n4. 学会温柔地说\"不\"：减少无意义的社交和加班。保护自己的时间和能量不是自私。\n\n5. 创造小仪式：周末早上慢慢泡一杯手冲咖啡，这个过程本身就是一种冥想。\n\n城市不会为你慢下来，但你可以学会在城市中找到自己的节奏。",
                "tags": "城市生活,平静,压力管理,burnout,数字排毒",
            },
        ]

        now = datetime.utcnow()
        for i, a in enumerate(articles):
            article = SharedArticle(
                user_id=sirius.id,
                title=a["title"],
                content=a["content"],
                tags=a["tags"],
                favorite_count=random.randint(3, 15),
                created_at=now - timedelta(days=random.randint(1, 30)),
            )
            db.add(article)

        db.commit()
        print(f"[数据库] 已为 Sirius 用户填充 {len(articles)} 篇社区分享文章")
    finally:
        db.close()


def seed_mental_health_data():
    """首次启动时为 Sirius 用户填充示例心理健康记录，覆盖近 2 个月"""
    from models import User, MentalHealthRecord
    import bcrypt

    db = SessionLocal()
    try:
        # 查找或创建 Sirius 用户
        sirius = db.query(User).filter(User.username == "Sirius").first()
        if not sirius:
            sirius = User(
                username="Sirius",
                email="sirius@example.com",
                sex="男",
                password_hash=bcrypt.hashpw("123456".encode("utf-8"), bcrypt.gensalt()).decode("utf-8"),
            )
            db.add(sirius)
            db.commit()
            db.refresh(sirius)
            print("[数据库] 已创建 Sirius 用户 (密码: 123456)")

        # 已有足够记录则跳过；不足 200 条则删除旧数据重建
        existing_count = db.query(MentalHealthRecord).filter(MentalHealthRecord.user_id == sirius.id).count()
        if existing_count >= 200:
            return
        if existing_count > 0:
            db.query(MentalHealthRecord).filter(MentalHealthRecord.user_id == sirius.id).delete()
            db.commit()
            print(f"[数据库] 旧记录仅 {existing_count} 条，删除重建...")

        emotions_positive = ["开心", "平静", "充满希望", "感恩", "满足", "放松"]
        emotions_negative = ["焦虑", "悲伤", "愤怒", "恐惧", "压力"]

        descriptions = [
            "今天工作很有成就感，完成了一个大项目",
            "和朋友聊了很久，心情好了很多",
            "做了半小时正念冥想，感觉平静了一些",
            "睡眠质量不错，早上起来精力充沛",
            "和家人通了电话，感觉很温暖",
            "下雨天待在家里看书，很惬意",
            "最近工作压力有点大，需要调整",
            "遇到了一些人际关系的困扰",
            "对未来有些迷茫和担忧",
            "尝试了新的放松方法，效果不错",
            "今天去运动了，流汗后心情舒畅",
            "听了一首好听的音乐，情绪稳定了很多",
            "写下了三件值得感恩的事情",
            "完成了一次深呼吸练习",
            "帮助了一位同事，感觉很有价值",
            "下午喝了一杯热茶，阳光洒在窗台上很舒服",
            "完成了一直拖延的任务，如释重负",
            "晚饭后散步半小时，看到美丽的晚霞",
            "和朋友互相鼓励，感到被理解和支持",
            "练习了十分钟腹式呼吸，心率降下来了",
            "今天效率很高，状态比昨天好很多",
            "整理了一下房间，感觉心情也跟着整洁了",
            "收到了一份意外的礼物，很感动",
            "看了一部治愈的电影，眼泪流完舒服多了",
            "在冥想app上完成了连续7天的打卡",
            "早起看到阳光透过窗帘，心情一下子明亮了",
            "下午去公园散步，看到孩子们在草地上奔跑，自己也跟着开心起来",
            "终于鼓起勇气和老板谈了加薪的事，虽然紧张但很为自己骄傲",
            "睡前听了一段放松音乐，入睡很快，好久没睡得这么踏实了",
            "和一个很久没联系的老朋友约了视频，聊了两个小时",
            "今天尝试了自己做饭，虽然不太好看但味道不错",
            "在工作中得到了同事的认可，这种被认可的感觉真好",
            "做了一件一直想做却拖延的事情，完成后的满足感让人上瘾",
            "晚上看星星发了会呆，感觉很宁静",
            "今天对自己说：你做得很好。自我肯定真重要",
        ]

        records = []
        today = datetime.utcnow()
        # 生成过去 60 天的记录，每天 3-5 条，几乎每天都有 → ~200+ 条
        for days_ago in range(60, 0, -1):
            # 仅 5% 概率跳过，确保密集
            if random.random() < 0.05:
                continue
            count = random.randint(3, 5)
            used_hours = set()
            for _ in range(count):
                hour = random.randint(7, 23)
                attempts = 0
                while hour in used_hours and attempts < 10:
                    hour = random.randint(7, 23)
                    attempts += 1
                used_hours.add(hour)
                minute = random.randint(0, 59)
                record_date = today - timedelta(days=days_ago, hours=today.hour - hour, minutes=today.minute - minute)

                # 70% 概率积极情绪，让数据偏向正面（心理健康平台用户趋势）
                if random.random() < 0.7:
                    emotion = random.choice(emotions_positive)
                    score = random.randint(6, 10)
                else:
                    emotion = random.choice(emotions_negative)
                    score = random.randint(2, 6)

                records.append(MentalHealthRecord(
                    user_id=sirius.id,
                    chat_id=None,
                    mood_score=score,
                    emotion_type=emotion,
                    description=random.choice(descriptions),
                    ai_context="",
                    created_at=record_date,
                ))

        db.add_all(records)
        db.commit()
        print(f"[数据库] 已为 Sirius 用户填充 {len(records)} 条心理健康记录（近 2 个月）")
    finally:
        db.close()

"""基于规则/关键词的话题分类器（零成本，无需 BERT 模型）。"""
from typing import Dict, List

# 分类关键词词典
CATEGORY_KEYWORDS: Dict[str, List[str]] = {
    "科技": ["AI", "人工智能", "芯片", "算法", "编程", "代码", "手机", "数码", "互联网", "科技", "机器人", "大模型", "GPT", "量子", "5G", "6G", "半导体", "软件", "黑客", "网络安全"],
    "娱乐": ["明星", "电影", "电视剧", "综艺", "演唱会", "偶像", "八卦", "娱乐圈", "影视", "演员", "歌手", "导演"],
    "社会": ["社会", "民生", "事故", "救援", "警方", "通报", "市民", "老人", "孩子", "家庭", "纠纷"],
    "体育": ["足球", "篮球", "比赛", "冠军", "奥运", "世界杯", "NBA", "球员", "教练", "联赛", "运动"],
    "财经": ["股市", "基金", "经济", "金融", "央行", "降息", "加息", "GDP", "通胀", "理财", "投资", "房地产", "房价", "汇率"],
    "生活": ["美食", "旅游", "健康", "养生", "穿搭", "家居", "宠物", "亲子", "教育", "考试", "高考", "考研"],
    "国际": ["美国", "俄罗斯", "乌克兰", "日本", "韩国", "欧洲", "联合国", "外交", "总统", "总理", "国际", "全球"],
    "军事": ["军事", "武器", "导弹", "航母", "战机", "军队", "国防", "演习"],
}

CATEGORY_LIST = list(CATEGORY_KEYWORDS.keys())


def classify(text: str) -> str:
    """对话题文本分类，返回最匹配的类别。"""
    if not text:
        return "其他"
    scores = {cat: 0 for cat in CATEGORY_LIST}
    for cat, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in text.lower():
                scores[cat] += 1
    best = max(scores, key=scores.get)
    if scores[best] == 0:
        return "其他"
    return best


def classify_with_scores(text: str) -> Dict[str, int]:
    """返回各分类得分。"""
    scores = {cat: 0 for cat in CATEGORY_LIST}
    if not text:
        return scores
    for cat, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in text.lower():
                scores[cat] += 1
    return scores

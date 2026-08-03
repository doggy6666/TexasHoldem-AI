"""第四阶段联网教练：仅在页面按钮被明确点击时调用 DeepSeek。"""

from __future__ import annotations

import hashlib
import json
import random
import re

from agent.decision_support import build_decision_context
from agent.deepseek_client import DeepSeekClient, DeepSeekError
from agent.expert_agent import estimate_outcome_probabilities
from agent.training import build_training_summary


class CoachError(RuntimeError):
    """策略提示或复盘无法生成。"""


TIP_SYSTEM_PROMPT = """你是德州扑克实时策略教练。
只能使用用户提供的牌局信息，不能假设或猜测对手隐藏手牌。
根据 legal_actions 给真人玩家一个可执行建议。重点使用 probability_model
中的基础胜率、结合行动后的参考胜率、平局率、对手更强概率与综合获胜机会，
并结合底池和跟注成本；基础概率来自未知牌随机抽样，参考胜率只根据对手公开
行动进行有限幅度的加权，两者都不等于读取了对手真实手牌。
authoritative_facts 是本地程序已经确认的事实，必须严格遵守：
- your_two_cards_same_suit 表示两张起手牌是否同一花色；
- your_current_best_hand 与 your_current_hand_category 是本地牌型引擎根据当前
  已发牌精确计算的牌型。描述玩家当前已有牌型时必须严格服从这些字段，不能把
  单张 A、K 等踢脚牌误当成对子；
- blind_posts 中的小盲和大盲只是强制投入，绝不是下注或加注；
- 只有 opponent_voluntary_aggressive_actions 中记录的行动才能称为对手主动下注、
  加注或全下。不要根据 street_bet 或 hand_contribution 自行推断有人加注。
用户是德州扑克新手，必须使用日常中文解释。禁止直接使用 EV、equity、range、
outs、SPR、GTO、pot odds、blocker、value bet、bluff catcher 等专业缩写或英文术语。
应改写为“长期平均收益”“综合获胜机会”“对手可能持有的牌”
“能帮助反超的剩余牌”“剩余筹码与底池的比例”等通俗表达。
输出 JSON：
{
  "action": "fold/check/call/bet/raise/all_in",
  "amount_to": 整数或 null,
  "reason": "给玩家看的简短依据",
  "risk": "一句风险提醒"
}
不要输出隐藏思考过程，不要添加 JSON 以外的内容。"""

TIP_ACTION_LABELS = {
    "fold": "弃牌（fold）",
    "check": "过牌（check）",
    "call": "跟注（call）",
    "bet": "下注（bet）",
    "raise": "加注（raise）",
    "all_in": "全下（all in）",
}


REVIEW_SYSTEM_PROMPT = """你是德州扑克累计深度复盘教练。
基于当前会话从第一局到最新一局的全部结构化记录，分析真人玩家反复出现的决策模式，
不得虚构对手隐藏手牌，也不要为了填满格式而强行评价单次偶然行动。
优先分析至少出现两次的模式；单次关键行动可以作为案例，但必须明确它只是单局证据。
用户是德州扑克新手，必须使用日常中文，不直接使用未经解释的专业缩写或英文术语；
例如把 EV 写成“长期平均收益”，把 range 写成“可能持有的牌”，
把 pot odds 写成“跟注成本与可能回报的比例”。
输出 JSON：
{
  "summary": "跨局整体打法画像",
  "confidence": "较低/中等/较高，并说明样本依据",
  "strengths": ["反复出现的优势"],
  "improvements": ["反复出现且应优先改进的问题"],
  "evidence": ["第N局 + 阶段 + 具体行动 + 为什么能支持结论"],
  "next_focus": "接下来3至5局的具体训练计划"
}
结论必须与 session_metrics 和 hands 中的事实一致；不得把盲注说成主动加注。
strengths、improvements 和 evidence 各至少提供一项，next_focus 必须是字符串。
不要输出隐藏思考过程或 JSON 以外内容。"""


MIN_DEEP_REVIEW_HANDS = 5


COACHING_TERM_REPLACEMENTS = (
    (r"长期\s*EV\s*为负", "从长期平均结果看会亏损"),
    (r"负\s*EV", "长期平均收益较差"),
    (r"正\s*EV", "长期平均收益较好"),
    (r"\bexpected value\b", "长期平均收益"),
    (r"\bEV\b", "长期平均收益"),
    (r"\bequity\b", "综合获胜机会"),
    (r"\bpot odds\b", "跟注成本与可能回报的比例"),
    (r"底池赔率", "跟注成本与可能回报的比例"),
    (r"\brange\b", "可能持有的牌"),
    (r"\bouts?\b", "能帮助反超的剩余牌"),
    (r"\bSPR\b", "剩余筹码与底池的比例"),
    (r"\bGTO\b", "均衡打法"),
    (r"\bthin value\b", "用较弱优势牌争取额外筹码"),
    (r"\bvalue bet\b", "用强牌下注争取更多筹码"),
    (r"\bbluff catcher\b", "主要用于识别对手诈唬的牌"),
    (r"\bblockers?\b", "会减少对手强牌可能性的关键牌"),
    (r"\bc-?bet\b", "翻牌后的持续下注"),
    (r"\bvariance\b", "短期结果波动"),
)

_PLAYER_HAND_CATEGORY_CLAIM = re.compile(
    r"(?:"
    r"你的(?:当前)?(?:最佳)?(?:手牌|牌型|牌)"
    r"|你(?:目前|现在)?"
    r"|当前(?:的)?(?:最佳)?(?:牌型|成牌)"
    r"|目前(?:的)?(?:最佳)?(?:牌型|成牌)"
    r")"
    r".{0,8}?"
    r"(?:已经|已)?(?:是|为|有|拿到|组成|形成|属于|只有)"
    r".{0,6}?"
    r"(皇家同花顺|同花顺|四条|葫芦|同花|顺子|三条|两对|双对|一对|高牌)",
    flags=re.IGNORECASE,
)


def decision_cache_key(game) -> str:
    parts = [
        str(game.hand_number),
        game.street_name,
        str(game.pot),
        str(game.current_bet),
        str(game.human.chips),
        ",".join(str(card) for card in game.human.hole_cards),
        ",".join(str(card) for card in game.community_cards),
        str(len(game.current_hand_record.get("actions", []))),
    ]
    return "|".join(parts)


def review_cache_key(completed_records: list[dict]) -> str:
    serialized = json.dumps(
        completed_records,
        ensure_ascii=False,
        sort_keys=True,
    )
    digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]
    return f"{len(completed_records)}|{digest}"


def build_tip_payload(game, probability_samples: int = 1500) -> dict:
    if game.status != "进行中" or not game.turn_is_human:
        raise CoachError("只有轮到你行动时才能获取实时策略提示。")
    context = build_decision_context(game, 0)
    seed_bytes = hashlib.sha256(
        decision_cache_key(game).encode("utf-8")
    ).digest()[:8]
    probabilities = estimate_outcome_probabilities(
        game,
        0,
        samples=probability_samples,
        rng=random.Random(int.from_bytes(seed_bytes, "big")),
    )
    probabilities["average_pot_share"] = probabilities.pop(
        "estimated_equity"
    )
    probabilities["model_assumption"] = (
        "基础概率将对手未知手牌与未发公共牌从剩余牌堆随机抽样；"
        "参考胜率根据对手公开行动温和加权，但不读取其真实手牌。"
    )
    context["probability_model"] = probabilities
    context["structured_actions_this_hand"] = list(
        game.current_hand_record.get("actions", [])
    )
    return context


def build_review_payload(
    completed_records: list[dict],
    minimum_hands: int = MIN_DEEP_REVIEW_HANDS,
) -> dict:
    records = [
        record for record in completed_records
        if record.get("completed")
    ]
    if len(records) < minimum_hands:
        raise CoachError(
            f"至少完成 {minimum_hands} 局后才能生成累计 AI 深度复盘。"
        )
    indexed_records = []
    for session_hand_number, record in enumerate(records, start=1):
        indexed_record = dict(record)
        indexed_record["session_hand_number"] = session_hand_number
        indexed_records.append(indexed_record)
    return {
        "scope": "当前浏览器会话从第一局到最新一局",
        "hand_count": len(indexed_records),
        "session_metrics": build_training_summary(records),
        "hands": indexed_records,
    }


def generate_realtime_tip(game, client=None) -> dict:
    try:
        payload = build_tip_payload(game)
        active_client = client or DeepSeekClient.from_environment()
        result = active_client.complete_json(
            TIP_SYSTEM_PROMPT,
            "请分析以下当前决策：\n"
            + json.dumps(payload, ensure_ascii=False),
            max_tokens=240,
            temperature=0.4,
            timeout_seconds=15,
        )
        validated = _validate_tip(result, payload["legal_actions"])
        fact_errors = _tip_fact_errors(result, payload)
        if fact_errors:
            correction = "；".join(fact_errors)
            result = active_client.complete_json(
                TIP_SYSTEM_PROMPT,
                "请重新分析以下当前决策：\n"
                + json.dumps(payload, ensure_ascii=False)
                + "\n上一次回答存在事实错误："
                + correction
                + "。必须以 authoritative_facts 为准重新输出完整 JSON。",
                max_tokens=240,
                temperature=0.1,
                timeout_seconds=15,
            )
            validated = _validate_tip(
                result,
                payload["legal_actions"],
            )
            if _tip_fact_errors(result, payload):
                raise CoachError(
                    "AI 策略解释与牌面事实冲突，错误内容已被拦截，请重新获取。"
                )
        validated["probability_model"] = payload["probability_model"]
        return validated
    except DeepSeekError as error:
        raise CoachError(str(error)) from None


def generate_deep_review(
    completed_records: list[dict],
    client=None,
    minimum_hands: int = MIN_DEEP_REVIEW_HANDS,
) -> dict:
    try:
        payload = build_review_payload(
            completed_records,
            minimum_hands=minimum_hands,
        )
        active_client = client or DeepSeekClient.from_environment()
        result = active_client.complete_json(
            REVIEW_SYSTEM_PROMPT,
            "请综合复盘以下会话级牌局记录：\n"
            + json.dumps(payload, ensure_ascii=False),
            max_tokens=1200,
            temperature=0.5,
            timeout_seconds=40,
        )
        return _validate_review(result, payload["hand_count"])
    except DeepSeekError as error:
        raise CoachError(str(error)) from None


def _validate_tip(result: dict, legal_actions: dict) -> dict:
    if not isinstance(result, dict):
        raise CoachError("实时策略提示格式错误。")
    required_text = ("action", "reason", "risk")
    if any(not isinstance(result.get(key), str) or not result[key].strip() for key in required_text):
        raise CoachError("实时策略提示缺少必要内容。")
    action = result["action"].strip()
    if action not in legal_actions["actions"]:
        raise CoachError("实时策略提示返回了当前不可执行的行动。")
    amount = result.get("amount_to")
    if action in {"bet", "raise"}:
        if isinstance(amount, bool) or not isinstance(amount, int):
            raise CoachError("实时策略提示的金额格式错误。")
        minimum = (
            legal_actions["minimum_bet_to"]
            if action == "bet"
            else legal_actions["minimum_raise_to"]
        )
        if not minimum <= amount <= legal_actions["maximum_to"]:
            raise CoachError("实时策略提示的金额超出合法范围。")
    else:
        amount = None
    return {
        "recommended_action": TIP_ACTION_LABELS[action],
        "amount_to": amount,
        "reason": simplify_coaching_language(result["reason"]),
        "risk": simplify_coaching_language(result["risk"]),
    }


def _tip_fact_errors(result: dict, payload: dict) -> list[str]:
    if not isinstance(result, dict):
        return []
    text = " ".join(
        str(result.get(key, ""))
        for key in ("reason", "risk")
    )
    facts = payload.get("authoritative_facts", {})
    errors = []

    if facts.get("your_two_cards_same_suit") is True and re.search(
        r"不同花色|不是同一花色|并非同一花色|杂色|offsuit",
        text,
        flags=re.IGNORECASE,
    ):
        errors.append("两张起手牌同一花色，不能描述为不同花色")
    if facts.get("your_two_cards_same_suit") is False and re.search(
        r"(?:两张牌|手牌|起手牌).{0,8}(?:同一花色|同花)"
        r"|同花起手牌|suited",
        text,
        flags=re.IGNORECASE,
    ):
        errors.append("两张起手牌不同花色，不能描述为同花起手牌")

    aggressive_seats = {
        action["seat"]
        for action in facts.get(
            "opponent_voluntary_aggressive_actions",
            [],
        )
    }
    for opponent in payload.get("opponents", []):
        if opponent.get("seat") in aggressive_seats:
            continue
        name = re.escape(str(opponent.get("name", "")))
        if name and re.search(
            rf"{name}.{{0,16}}(?:已经|已|曾经|进行了|选择了)"
            rf".{{0,6}}(?:加注|下注|全下)",
            text,
        ):
            errors.append(
                f"{opponent.get('name')}没有主动下注、加注或全下"
            )

    if not aggressive_seats and (
        re.search(
            r"(?:对手|其他玩家|有人).{0,12}"
            r"(?:已经|已|曾经|进行了|选择了).{0,6}"
            r"(?:加注|下注|全下)",
            text,
        )
        or re.search(
            r"面对(?:了)?(?:对手|其他玩家|有人).{0,8}"
            r"(?:加注|下注|全下)",
            text,
        )
    ):
        errors.append("本局尚无对手主动下注、加注或全下")

    actual_category = str(
        facts.get("your_current_hand_category") or ""
    ).strip()
    if actual_category:
        for match in _PLAYER_HAND_CATEGORY_CLAIM.finditer(text):
            if re.search(
                r"可能|机会|有望|如果|假如|若能|可以|能够",
                match.group(0),
            ):
                continue
            claimed_category = match.group(1)
            if claimed_category == "双对":
                claimed_category = "两对"
            if claimed_category == actual_category:
                continue
            exact_hand = str(
                facts.get("your_current_best_hand")
                or actual_category
            )
            errors.append(
                f"本地牌型引擎确认玩家当前最佳牌型为{exact_hand}，"
                f"不能描述为{claimed_category}"
            )

    return list(dict.fromkeys(errors))


def _validate_review(result: dict, hand_count: int) -> dict:
    if not isinstance(result, dict):
        raise CoachError("AI 深度复盘格式错误。")

    summary_items = _review_text_items(
        _first_review_value(result, "summary", "本局总结")
    )
    if not summary_items:
        raise CoachError("AI 深度复盘缺少总结。")

    strengths = _review_text_items(
        _first_review_value(result, "strengths", "做得好的地方")
    )
    if not strengths:
        strengths = ["当前样本尚未形成明确、重复出现的优势模式。"]

    improvements = _review_text_items(
        _first_review_value(
            result,
            "improvements",
            "可以改进的地方",
        )
    )
    if not improvements:
        improvements = ["继续积累决策记录，再判断最应优先改进的问题。"]

    evidence = _review_text_items(
        _first_review_value(
            result,
            "evidence",
            "examples",
            "关键证据",
            "分析依据",
        )
    )
    if not evidence:
        evidence = ["当前回复未提供可核对的具体局次证据。"]

    next_focus_items = _review_text_items(
        _first_review_value(
            result,
            "next_focus",
            "nextFocus",
            "training_focus",
            "下一局训练重点",
        )
    )
    if not next_focus_items:
        next_focus_items = [improvements[0]]

    confidence_items = _review_text_items(
        _first_review_value(
            result,
            "confidence",
            "analysis_confidence",
            "结论可信度",
        )
    )
    if not confidence_items:
        confidence_level = (
            "较高" if hand_count >= 20
            else "中等" if hand_count >= 8
            else "较低"
        )
        confidence_items = [
            f"{confidence_level}，当前累计分析 {hand_count} 局。"
        ]

    return {
        "summary": simplify_coaching_language("；".join(summary_items)),
        "confidence": simplify_coaching_language(
            "；".join(confidence_items)
        ),
        "strengths": [
            simplify_coaching_language(item) for item in strengths
        ],
        "improvements": [
            simplify_coaching_language(item)
            for item in improvements
        ],
        "evidence": [
            simplify_coaching_language(item) for item in evidence
        ],
        "next_focus": simplify_coaching_language(
            "；".join(next_focus_items)
        ),
    }


def _first_review_value(result: dict, *keys: str):
    for key in keys:
        if key in result:
            return result[key]
    return None


def _review_text_items(value) -> list[str]:
    """兼容模型偶尔返回的字符串、列表或简单对象。"""
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    if isinstance(value, list):
        items = []
        for item in value:
            items.extend(_review_text_items(item))
        return items
    if isinstance(value, dict):
        items = []
        for item in value.values():
            items.extend(_review_text_items(item))
        return items
    return []


def simplify_coaching_language(text: str) -> str:
    simplified = text.strip()
    for pattern, replacement in COACHING_TERM_REPLACEMENTS:
        simplified = re.sub(
            pattern,
            replacement,
            simplified,
            flags=re.IGNORECASE,
        )
    return simplified

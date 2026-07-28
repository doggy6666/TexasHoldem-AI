# TexasHoldem AI｜德州扑克智能对战

面向德州扑克学习者的 AI 对战 Demo。当前版本支持 2–4 人连续牌局、四种 AI 模式与 DeepSeek 决策；API 不可用或返回非法行动时，会自动切换本地规则 AI，保证演示不中断。

## 第三阶段功能

- 线下对战：全部对手使用本地默认 AI，强制不调用 DeepSeek，不消耗 API Token。
- 简单模式：全部对手使用新手 AI。
- 进阶模式：对手在内部使用保守或激进策略，页面统一标记为“进阶 AI”。
- 困难模式：全部对手使用高手 AI，结合蒙特卡洛胜率、底池赔率、SPR、最低防守频率、位置和建议下注尺度进行 GTO 启发式决策。
- 自定义模式：可为每个 AI 座位选择新手、进阶或高手 AI。
- AI 姓名右侧是唯一类型标记；DeepSeek 不可用时，该标记变为“默认 AI”。
- AI 不展示行动理由，也不会把其他玩家的隐藏手牌或牌堆内容发送给模型。
- 所有模型输出都会经过合法行动和下注金额校验，非法输出直接由默认 AI 接管。
- 支持庄家轮换、盲注、完整下注轮、反复加注、全下跑牌、未跟注筹码退还、主池/边池及多人平分结算。

高手 AI 是适合演示和陪练的 GTO 启发式实现，并非离线求解器或严格纳什均衡解算器。

## 第四阶段功能

- 结构化牌局记录：记录每次行动前后的阶段、底池、下注压力、筹码与公开牌面，可在页面展开查看。
- 实时策略提示：只在联网模式、轮到真人玩家时显示；只有点击按钮才调用 DeepSeek。
- AI深度复盘：只在联网模式牌局结束后显示；只有点击按钮才调用 DeepSeek。
- 陪练面板：统计连续牌局数、累计筹码变化、玩家决策次数与行动分布，方便评估其产品价值。
- 结构化记录和发送给 DeepSeek 的内容都不包含对手未公开手牌或牌堆。
- 线下对战不显示联网提示与复盘按钮，继续保持零 API 调用。

实时策略提示和 AI 深度复盘不提供本地分析替代；API 不可用时会直接提示暂不可用。

## DeepSeek API

API Key 只从 Windows 用户环境变量读取，不写入项目文件：

```text
DEEPSEEK_API_KEY=你的 API 密钥
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=你选择的通用模型
```

修改环境变量后需要关闭并重新打开终端。不要把 API Key 写入源码、截图、日志或 Git 仓库。

## 如何运行

在 PowerShell 中进入项目目录后启动：

```powershell
Set-Location -LiteralPath D:\Zikky\Documents\TexasHoldem
py -m pip install -r requirements.txt
py -m streamlit run app.py
```

保持终端窗口运行，并打开命令输出中的本地地址，通常是 `http://localhost:8501`。网页由本机 Python 进程提供，关闭终端中的 Streamlit 进程后网页也会停止。

## 如何测试

```powershell
Set-Location -LiteralPath D:\Zikky\Documents\TexasHoldem
py -m pytest -q
```

重点手工验证：

1. 分别选择线下、简单、进阶、困难、自定义模式并开始新对局。
2. 确认 AI 姓名右侧只出现一个难度标记，行动栏不重复显示。
3. 临时移除 `DEEPSEEK_API_KEY` 后重启应用，确认 AI 姓名右侧变为“默认 AI”，牌局仍可继续。
4. 自定义模式选择不同难度，确认对应座位显示正确标记。

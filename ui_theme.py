"""TexasHoldem AI 的 Streamlit 视觉主题。"""

APP_CSS = r"""
<style>
:root {
  --app-bg: #203238;
  --app-bg-deep: #18282d;
  --surface: #f2f0ea;
  --surface-strong: #fbfaf6;
  --surface-line: #96aaa5;
  --ink: #173038;
  --muted: #68777b;
  --felt: #07593f;
  --felt-deep: #03432f;
  --wood: #75452f;
  --wood-deep: #3e241b;
  --teal: #2f7773;
  --teal-bright: #18d8df;
  --cyan: #00e7f0;
  --magenta: #ff2f7d;
  --yellow: #e9ef3a;
  --panel: #03151c;
}

html, body, [class*="css"] {
  font-family: "Segoe UI", "Microsoft YaHei UI", "Microsoft YaHei", sans-serif;
  font-synthesis: none;
}

.stApp {
  color: var(--ink);
  background:
    radial-gradient(circle at 48% 32%, rgba(75, 111, 112, .28), transparent 34%),
    linear-gradient(145deg, var(--app-bg) 0%, var(--app-bg-deep) 100%);
}

[data-testid="stHeader"] {
  height: 1.75rem;
  background: transparent;
}

[data-testid="stMainBlockContainer"],
[data-testid="stAppViewBlockContainer"] {
  max-width: 1760px;
  padding: 1rem 1.8rem 1.5rem !important;
}

[data-testid="stSidebar"],
[data-testid="collapsedControl"] { display: none !important; }

.app-shell-header {
  min-height: 76px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  margin-bottom: 14px;
  padding: 0 24px;
  border: 1px solid rgba(171, 187, 181, .92);
  border-top: 3px solid #6c9f99;
  border-radius: 15px;
  background: linear-gradient(105deg, #f7f5ef, #e7e5de);
  box-shadow: 0 12px 28px rgba(4, 18, 22, .24);
}

.brand-lockup {
  display: flex;
  align-items: center;
  gap: 15px;
  min-width: 0;
}

.brand-mark {
  width: 49px;
  height: 49px;
  display: grid;
  place-items: center;
  flex: 0 0 49px;
  border-radius: 11px;
  color: #f8f7f2;
  background: linear-gradient(145deg, #347c79, #205e61);
  box-shadow: 0 5px 12px rgba(21, 64, 66, .25);
  font-size: 28px;
}

.brand-title {
  color: #0c2832;
  font-size: clamp(1.35rem, 2vw, 1.72rem);
  font-weight: 560;
  letter-spacing: .01em;
  white-space: nowrap;
}

.header-meta {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  min-width: 0;
}

.header-pill {
  min-height: 42px;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 16px;
  border: 1px solid rgba(78, 96, 95, .22);
  border-radius: 10px;
  color: #f7f5ee;
  background: #7f7866;
  font-size: .92rem;
  font-weight: 500;
  white-space: nowrap;
}

.header-pill.mode {
  color: #eaf9f6;
  background: #276b69;
}

.st-key-top_toolbar {
  margin: -4px 0 14px;
  padding: 8px 10px;
  border: 1px solid rgba(120, 160, 154, .42);
  border-radius: 10px;
  background: rgba(17, 45, 50, .72);
}

.st-key-top_toolbar button {
  min-height: 42px;
  border: 1px solid rgba(117, 218, 208, .55) !important;
  border-radius: 7px !important;
  color: #eaffff !important;
  background: #236b6c !important;
  font-weight: 520 !important;
}

.st-key-top_toolbar button:hover {
  border-color: var(--yellow) !important;
  color: #ffffff !important;
  background: #2f8987 !important;
}

.nickname-gate-title {
  max-width: 520px;
  margin: 18vh auto 18px;
  color: #eaffff;
  font-size: 1.8rem;
  font-weight: 560;
  text-align: center;
  letter-spacing: .03em;
}

[data-testid="stTextInput"] {
  max-width: 520px;
  margin: 0 auto 12px;
}

[data-testid="stTextInput"] label {
  color: #d8eced !important;
}

[data-testid="stTextInput"] input::placeholder {
  color: rgba(0, 0, 0, .52) !important;
  opacity: 1;
}

.st-key-nickname_submit {
  width: 240px;
  max-width: 70%;
  min-width: 0;
  box-sizing: border-box;
  margin: 0 auto;
}

.st-key-nickname_submit button {
  width: 100% !important;
  max-width: 240px;
}

.st-key-audio_controls {
  position: fixed;
  z-index: 100;
  right: 18px;
  bottom: 16px;
  width: 206px;
  height: 62px;
  padding: 3px 8px;
  border: 0;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
}

.st-key-audio_controls iframe {
  width: 100% !important;
  height: 62px !important;
  border: 0 !important;
}

.st-key-audio_controls > div > div {
  width: 100%;
}

.st-key-audio_controls button,
.st-key-audio_controls [data-testid="stSlider"] {
  display: none;
}

.st-key-audio_controls button {
  width: 42px;
  min-width: 42px;
  height: 42px;
  min-height: 42px;
  padding: 0 !important;
  border: 1px solid var(--cyan) !important;
  border-radius: 50% !important;
  color: #eaffff !important;
  background: #12525d !important;
  font-size: 1.05rem !important;
}

.st-key-audio_controls button:hover {
  color: var(--yellow) !important;
  background: #1b6e77 !important;
}

.st-key-audio_controls [data-testid="stSlider"] {
  padding-top: 7px;
}

.st-key-audio_controls [data-testid="stSlider"] label {
  display: none;
}

.game-grid {
  display: grid;
  grid-template-columns: minmax(720px, 1fr) minmax(330px, 390px);
  gap: 18px;
  align-items: start;
}

/* ----- 牌桌场景 ----- */
.table-stage {
  position: relative;
  min-height: 736px;
  overflow: hidden;
  border: 1px solid rgba(127, 158, 153, .42);
  border-radius: 18px;
  background:
    radial-gradient(circle at 50% 46%, rgba(77, 116, 112, .24), transparent 52%),
    linear-gradient(145deg, rgba(39, 59, 64, .96), rgba(26, 43, 48, .98));
  box-shadow: 0 20px 42px rgba(4, 16, 20, .3);
}

.table-surface {
  position: absolute;
  z-index: 1;
  left: 12%;
  top: 102px;
  width: 76%;
  height: 500px;
  border: 15px solid var(--wood);
  border-bottom-width: 25px;
  border-radius: 50%;
  background:
    radial-gradient(ellipse at 50% 36%, rgba(21, 121, 82, .34), transparent 48%),
    repeating-linear-gradient(12deg, rgba(255, 255, 255, .012) 0 1px, transparent 1px 4px),
    linear-gradient(160deg, var(--felt) 0%, var(--felt-deep) 100%);
  box-shadow:
    inset 0 0 0 4px #b3a87e,
    inset 0 0 34px rgba(0, 15, 8, .58),
    0 18px 0 var(--wood-deep),
    0 30px 38px rgba(3, 14, 17, .44);
  transform: perspective(1200px) rotateX(10deg);
  transform-origin: 50% 76%;
}

.game-status-bar {
  margin-bottom: 8px;
  padding: 8px 12px;
  overflow: hidden;
  border: 1px solid rgba(114, 154, 150, .42);
  border-radius: 8px;
  color: #c6d8d4;
  background: rgba(19, 45, 50, .78);
  font-size: .76rem;
  letter-spacing: .025em;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.player-count-4 .table-surface {
  left: 18%;
  width: 64%;
}

.player-count-4 .hole-left { left: 19%; }
.player-count-4 .hole-right { right: 19%; }

.pot-hud {
  position: absolute;
  z-index: 5;
  left: 24px;
  top: 79px;
  min-width: 126px;
  padding: 10px 14px;
  border: 1px solid rgba(118, 167, 162, .62);
  border-radius: 9px;
  color: #e8f3ef;
  background: rgba(20, 49, 54, .9);
  box-shadow: 0 7px 18px rgba(6, 18, 21, .2);
}

.pot-hud-label {
  margin-bottom: 2px;
  color: #a9bdb8;
  font-size: .72rem;
  font-weight: 450;
  letter-spacing: .05em;
}

.pot-hud-value {
  font-size: 1.55rem;
  font-weight: 440;
  line-height: 1.1;
}

.board-caption {
  position: absolute;
  z-index: 4;
  left: 24px;
  top: 154px;
  color: #91a8a5;
  font-size: .72rem;
  letter-spacing: .04em;
}

.community-zone {
  position: absolute;
  z-index: 5;
  left: 50%;
  top: 348px;
  min-width: 352px;
  min-height: 84px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  transform: translate(-50%, -50%);
}

.community-empty {
  color: rgba(230, 241, 236, .58);
  font-size: .86rem;
  letter-spacing: .04em;
}

.player-seat {
  position: absolute;
  overflow: visible;
  z-index: 7;
  width: 204px;
  min-height: 94px;
  display: grid;
  grid-template-columns: 66px minmax(0, 1fr);
  gap: 10px;
  align-items: center;
  padding: 9px 10px;
  border: 1px solid rgba(177, 194, 187, .62);
  border-radius: 12px;
  color: #f3f6f2;
  background: linear-gradient(145deg, #71817d, #61706d);
  box-shadow: 0 10px 22px rgba(4, 17, 20, .24);
}

.player-seat.is-human {
  border-color: #bbb68c;
  background: linear-gradient(145deg, #777968, #666957);
  grid-template-columns: 1fr;
}

.seat-avatar {
  width: 66px;
  height: 66px;
  display: grid;
  place-items: center;
  overflow: hidden;
  border-radius: 10px;
  color: #f8faf7;
  background: #2d7b76;
  font-size: 1rem;
  font-weight: 600;
}

.seat-avatar img {
  width: 100%;
  height: 100%;
  display: block;
  object-fit: cover;
}

.player-seat.is-human .seat-avatar { display: none; }

.seat-copy { min-width: 0; }

.seat-line {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
}

.seat-name {
  overflow: hidden;
  color: #ffffff;
  font-size: .91rem;
  font-weight: 540;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.dealer-marker {
  color: #f3e68d;
  font-size: .74rem;
  white-space: nowrap;
}

.ai-level {
  display: inline-flex;
  margin-top: 3px;
  padding: 1px 6px 2px;
  border: 1px solid rgba(207, 231, 225, .38);
  border-radius: 999px;
  color: #e1efeb;
  font-size: .64rem;
  font-weight: 450;
}

.seat-chips {
  margin-top: 4px;
  color: #e4ebe7;
  font-size: .76rem;
  font-variant-numeric: tabular-nums;
}

.seat-status {
  position: absolute;
  z-index: 2;
  overflow: visible;
  color: #d5dfdc;
  font-size: .72rem;
  font-weight: 500;
  line-height: 1.35;
  text-align: center;
  white-space: normal;
  word-break: break-word;
}

.seat-status.acting { color: #f8eb72; }
.seat-status.danger { color: #ffc5c9; }

/* Side seats keep their action text below the avatar card. */
.seat-left .seat-status,
.seat-right .seat-status {
  top: calc(100% + 7px);
  left: 0;
  width: 100%;
}

/* Top and bottom seats keep their action text outside the left edge. */
.seat-top .seat-status,
.seat-bottom .seat-status,
.seat-top-left .seat-status,
.seat-top-right .seat-status {
  top: 50%;
  right: calc(100% + 10px);
  width: max-content;
  max-width: none;
  transform: translateY(-50%);
  text-align: right;
  white-space: nowrap;
}

.seat-bottom { left: 50%; bottom: 8px; transform: translateX(-50%); }
.seat-top { left: 50%; top: 8px; transform: translateX(-50%); }
.seat-left { left: 8px; top: 50%; transform: translateY(-50%); }
.seat-right { right: 8px; top: 50%; transform: translateY(-50%); }
.seat-top-left { left: 10%; top: 25px; }
.seat-top-right { right: 10%; top: 25px; }

.hole-cards {
  position: absolute;
  z-index: 6;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  perspective: 700px;
}

.hole-bottom { left: 50%; bottom: 144px; --deal-x: 0px; --deal-y: -190px; transform: translateX(-50%); }
.hole-top { left: 50%; top: 121px; --deal-x: 0px; --deal-y: 190px; transform: translateX(-50%); }
.hole-left { left: 16.5%; top: 47%; --deal-x: 300px; --deal-y: 0px; transform: translateY(-50%); }
.hole-right { right: 16.5%; top: 47%; --deal-x: -300px; --deal-y: 0px; transform: translateY(-50%); }
.hole-top-left { left: 25%; top: 109px; --deal-x: 210px; --deal-y: 140px; }
.hole-top-right { right: 25%; top: 109px; --deal-x: -210px; --deal-y: 140px; }

.hole-cards.fold-out {
  pointer-events: none;
  animation: fold-cards-exit .42s cubic-bezier(.3, .78, .4, 1) forwards;
}

.poker-card {
  position: relative;
  width: 52px;
  height: 74px;
  display: inline-flex;
  flex: 0 0 52px;
  align-items: center;
  justify-content: center;
  box-sizing: border-box;
  overflow: hidden;
  border: 1px solid #cfd4d0;
  border-radius: 6px;
  color: #172126;
  background: #fdfcf8;
  box-shadow: 0 3px 5px rgba(1, 17, 11, .32);
  font-family: Georgia, "Times New Roman", serif;
}

.poker-card.red { color: #c6323c; }

.card-corner {
  position: absolute;
  left: 6px;
  top: 4px;
  display: flex;
  flex-direction: column;
  align-items: center;
  font-size: .9rem;
  font-weight: 700;
  line-height: .92;
}

.card-suit-main {
  margin-top: 9px;
  font-size: 1.55rem;
}

.poker-card.back {
  border: 4px solid #f4f1e8;
  background-color: #172a72;
  background-image:
    linear-gradient(30deg, rgba(255,255,255,.18) 12%, transparent 12.5%, transparent 87%, rgba(255,255,255,.18) 87.5%),
    linear-gradient(150deg, rgba(255,255,255,.18) 12%, transparent 12.5%, transparent 87%, rgba(255,255,255,.18) 87.5%),
    linear-gradient(30deg, rgba(255,255,255,.18) 12%, transparent 12.5%, transparent 87%, rgba(255,255,255,.18) 87.5%),
    linear-gradient(150deg, rgba(255,255,255,.18) 12%, transparent 12.5%, transparent 87%, rgba(255,255,255,.18) 87.5%),
    linear-gradient(60deg, rgba(255,255,255,.12) 25%, transparent 25.5%, transparent 75%, rgba(255,255,255,.12) 75%);
  background-position: 0 0, 0 0, 8px 14px, 8px 14px, 0 0;
  background-size: 16px 28px;
  box-shadow:
    inset 0 0 0 1px rgba(255,255,255,.62),
    0 3px 5px rgba(1, 17, 11, .32);
}

.poker-card.deal-in {
  opacity: 0;
  animation: deal-from-center .52s cubic-bezier(.2, .78, .26, 1) forwards;
  animation-delay: calc(var(--card-order, 0) * 90ms);
}

.poker-card.new-card {
  opacity: 0;
  animation: board-card-arrive .42s cubic-bezier(.22, .85, .3, 1) forwards;
  animation-delay: calc(var(--card-order, 0) * 85ms);
}

.poker-card.face-reveal {
  animation: card-face-reveal .5s cubic-bezier(.2, .75, .3, 1);
}

@keyframes deal-from-center {
  from {
    opacity: 0;
    transform: translate(var(--deal-x), var(--deal-y)) scale(.72) rotate(-5deg);
  }
  70% { opacity: 1; }
  to { opacity: 1; transform: translate(0, 0) scale(1) rotate(0); }
}

@keyframes board-card-arrive {
  from { opacity: 0; transform: translateY(-34px) scale(.78); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}

@keyframes card-face-reveal {
  from { opacity: .25; transform: rotateY(82deg) scale(.92); }
  to { opacity: 1; transform: rotateY(0) scale(1); }
}

@keyframes fold-cards-exit {
  from { opacity: 1; filter: saturate(1); }
  to { opacity: 0; filter: saturate(.55); transform: translateY(-16px) scale(.88); }
}

/* ----- 操作区 ----- */
.st-key-action_area {
  margin-top: 14px;
  padding: 15px 18px 18px;
  border: 1px solid #91a39e;
  border-radius: 14px;
  background: linear-gradient(110deg, #f7f5ef, #e5e4dd);
  box-shadow: 0 12px 26px rgba(4, 16, 20, .24);
}

.st-key-action_area h3 {
  margin: 0 0 8px !important;
  color: #243b42;
  font-size: 1rem !important;
  font-weight: 520 !important;
}

.st-key-action_area p,
.st-key-action_area label,
.st-key-action_area [data-testid="stCaptionContainer"] {
  color: #4c6064 !important;
}

.st-key-action_area button {
  min-height: 52px;
  border: 1px solid rgba(255, 255, 255, .14) !important;
  border-radius: 7px !important;
  color: #ffffff !important;
  font-family: "Segoe UI", "Microsoft YaHei UI", sans-serif !important;
  font-size: .94rem !important;
  font-weight: 560 !important;
  letter-spacing: .01em;
  text-shadow: 0 1px 1px rgba(0, 0, 0, .28);
}

.st-key-action_area button p,
.st-key-action_area button span,
.st-key-action_area button div {
  color: #ffffff !important;
  font-size: inherit !important;
  font-weight: inherit !important;
}

.st-key-fold_action button {
  background: #596a6f !important;
  color: #ffffff !important;
  box-shadow: inset 0 -3px 0 rgba(21, 36, 40, .72);
}

.st-key-call_action button {
  background: #377b70 !important;
  color: #ffffff !important;
  box-shadow: inset 0 -3px 0 rgba(18, 61, 56, .72);
}

.st-key-raise_action button {
  background: #8a7345 !important;
  color: #ffffff !important;
  box-shadow: inset 0 -3px 0 rgba(70, 54, 28, .72);
}

.st-key-all_in_action button {
  background: #7e4353 !important;
  color: #ffffff !important;
  box-shadow: inset 0 -3px 0 rgba(61, 25, 38, .72);
}

.st-key-action_area button:hover:not(:disabled) {
  border-color: rgba(255, 255, 255, .62) !important;
  filter: brightness(1.12);
}

.st-key-action_area button:disabled {
  color: rgba(255, 255, 255, .72) !important;
  filter: saturate(.65) brightness(.86);
}

.st-key-action_area input[type="range"] {
  accent-color: #2f7773 !important;
}

/* ----- 赛博策略面板 ----- */
.st-key-coach_panel {
  position: relative;
  height: min(900px, calc(100vh - 132px));
  min-height: 0;
  max-height: 900px;
  overflow-y: auto;
  overflow-x: hidden;
  overscroll-behavior: contain;
  padding: 17px 16px 20px;
  border: 1px solid var(--cyan);
  border-top: 4px solid var(--cyan);
  border-radius: 2px 14px 14px 14px;
  color: #d5eff0;
  background:
    linear-gradient(114deg, transparent 0 35%, rgba(0, 229, 240, .045) 35.5% 38%, transparent 38.5%),
    radial-gradient(circle at 96% 7%, rgba(255, 47, 125, .22), transparent 27%),
    repeating-linear-gradient(0deg, rgba(0, 229, 240, .025) 0 1px, transparent 1px 19px),
    #03151c;
  box-shadow: 0 18px 38px rgba(2, 12, 17, .4), inset 0 0 40px rgba(0, 214, 224, .025);
  scrollbar-color: var(--cyan) #10262d;
  scrollbar-width: thin;
}

.st-key-coach_panel::before {
  content: "01101010  0x7A  101101  // DECISION SUPPORT";
  position: absolute;
  z-index: 0;
  left: 14px;
  top: 8px;
  color: rgba(0, 229, 240, .17);
  font-family: Consolas, monospace;
  font-size: .55rem;
  letter-spacing: .12em;
  pointer-events: none;
}

.st-key-coach_panel > div { position: relative; z-index: 1; }

.cyber-panel-title {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 6px 0 15px;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(0, 229, 240, .36);
  color: #ecffff;
  font-size: 1.17rem;
  font-weight: 520;
  letter-spacing: .025em;
}

.cyber-panel-title::before {
  content: "◆";
  width: 31px;
  height: 31px;
  display: grid;
  place-items: center;
  border: 1px solid var(--cyan);
  color: var(--yellow);
  background: rgba(0, 229, 240, .08);
  font-size: .8rem;
  transform: rotate(45deg);
}

.st-key-coach_panel h1,
.st-key-coach_panel h2,
.st-key-coach_panel h3,
.st-key-coach_panel h4,
.st-key-coach_panel p,
.st-key-coach_panel li,
.st-key-coach_panel label,
.st-key-coach_panel [data-testid="stCaptionContainer"],
.st-key-coach_panel [data-testid="stMetricLabel"],
.st-key-coach_panel [data-testid="stMetricValue"] {
  color: #d8eced !important;
  font-weight: 400 !important;
}

.st-key-coach_panel [data-testid="stMetric"] {
  min-height: 82px;
  padding: 10px 11px;
  border: 1px solid rgba(0, 229, 240, .28);
  background: rgba(4, 31, 38, .82);
}

.st-key-coach_panel [data-testid="stMetricValue"] {
  color: #3de0df !important;
  font-size: 1.42rem !important;
}

.st-key-coach_panel [data-testid="stExpander"] {
  border: 1px solid rgba(0, 229, 240, .3);
  border-radius: 0;
  background: rgba(3, 24, 31, .82);
}

/* Keep expanded sections compact; long reports scroll inside the section. */
.st-key-coach_panel [data-testid="stExpander"] details[open] > div {
  max-height: 520px;
  overflow-y: auto;
  overflow-x: hidden;
  overscroll-behavior: contain;
  scrollbar-gutter: stable;
  scrollbar-color: var(--cyan) #10262d;
  scrollbar-width: thin;
}

.st-key-coach_panel [data-testid="stExpander"] details[open] > div > div {
  min-width: 0;
}

.st-key-data_panel_area [data-testid="stExpander"] details[open] > div {
  max-height: 680px;
}

/* The separate showdown box returns after all right-panel expanders close. */
[data-testid="column"]:has(.st-key-coach_panel details[open]) .st-key-showdown_area,
[data-testid="stColumn"]:has(.st-key-coach_panel details[open]) .st-key-showdown_area {
  display: none !important;
}

.st-key-coach_panel [data-testid="stExpander"] summary,
.st-key-coach_panel [data-testid="stExpander"] summary:hover,
.st-key-coach_panel [data-testid="stExpander"] summary:focus,
.st-key-coach_panel [data-testid="stExpander"] summary:focus-visible {
  color: #d9f4f4 !important;
  background: rgba(3, 24, 31, .82) !important;
}

.st-key-coach_panel [data-testid="stExpander"] summary {
  color: #d9f4f4;
  font-weight: 450;
}

.st-key-coach_panel button {
  border: 1px solid var(--cyan) !important;
  border-radius: 0 8px 0 8px !important;
  color: #eaffff !important;
  background: linear-gradient(110deg, #004455, #052837) !important;
  font-weight: 450 !important;
}

.st-key-coach_panel button:hover,
.st-key-coach_panel button:focus,
.st-key-coach_panel button:active,
.st-key-coach_panel button:focus-visible,
.st-key-coach_panel button:disabled {
  background: linear-gradient(110deg, #004455, #052837) !important;
  color: #eaffff !important;
}

.st-key-coach_panel button:hover {
  border-color: var(--yellow) !important;
  color: var(--yellow) !important;
}

.st-key-coach_panel [data-testid="stAlert"] {
  border: 1px solid rgba(0, 229, 240, .3);
  border-radius: 0;
  color: #d9efef;
  background: rgba(6, 31, 38, .86);
}

.st-key-coach_panel hr { border-color: rgba(0, 229, 240, .22); }

.st-key-coach_panel [data-testid="stDataFrame"] {
  border: 1px solid rgba(0, 229, 240, .24);
}

.st-key-coach_panel .strategy-placeholder {
  margin-bottom: 12px;
  padding: 14px;
  border-left: 3px solid rgba(0, 229, 240, .5);
  color: #91aaad;
  background: rgba(0, 229, 240, .035);
  font-size: .85rem;
  line-height: 1.6;
}

.st-key-coach_panel .strategy-block {
  margin: 10px 0 14px;
  padding: 14px;
  border: 1px solid rgba(237, 239, 61, .38);
  background: rgba(10, 27, 31, .85);
}

.strategy-label {
  color: #60e7e2;
  font-size: .72rem;
  letter-spacing: .08em;
}

.strategy-action {
  margin: 4px 0 12px;
  color: var(--yellow);
  font-size: 1.38rem;
  font-weight: 520;
}

.strategy-copy {
  color: #d5e5e5;
  font-size: .86rem;
  line-height: 1.62;
}

.strategy-copy.risk {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid rgba(255, 47, 125, .28);
  color: #f1b4cc;
}

/* 结果与辅助信息 */
.st-key-result_area,
.st-key-showdown_area {
  position: relative;
  z-index: 0;
  margin-top: 14px;
  padding: 14px 16px;
  border: 1px solid rgba(0, 229, 240, .36);
  border-radius: 10px;
  color: #d8eced;
  background: #061b22;
  box-shadow: 0 12px 24px rgba(2, 12, 17, .26);
}

.st-key-result_area p,
.st-key-showdown_area p,
.st-key-result_area h4,
.st-key-showdown_area h3 {
  color: #eafefe !important;
}

.st-key-result_area [data-testid="stAlert"],
.st-key-showdown_area [data-testid="stAlert"] {
  color: #d8eced !important;
  background: #09262d !important;
  border-color: rgba(0, 229, 240, .35) !important;
}

.st-key-result_area [data-testid="stAlert"] p,
.st-key-showdown_area [data-testid="stAlert"] p,
.st-key-result_area [data-testid="stCaptionContainer"],
.st-key-showdown_area [data-testid="stCaptionContainer"] {
  color: #d8eced !important;
}

.st-key-result_area button {
  border: 1px solid rgba(0, 229, 240, .48) !important;
  border-radius: 0 8px 0 8px !important;
  color: #d8eced !important;
  background: transparent !important;
  box-shadow: none !important;
}

.st-key-result_area button:hover,
.st-key-result_area button:focus,
.st-key-result_area button:active {
  border-color: var(--cyan) !important;
  color: #ffffff !important;
  background: #164b55 !important;
}

@media (max-width: 1240px) {
  .game-grid { grid-template-columns: 1fr; }
  .st-key-coach_panel {
    height: min(680px, calc(100vh - 170px));
    max-height: 680px;
  }
}

@media (max-width: 860px) {
  [data-testid="stMainBlockContainer"],
  [data-testid="stAppViewBlockContainer"] { padding-left: .7rem !important; padding-right: .7rem !important; }
  .app-shell-header { padding: 0 14px; }
  .header-pill.mode { display: none; }
  .table-stage { min-height: 680px; overflow-x: auto; }
  .table-surface { left: 8%; width: 84%; }
  .player-seat { width: 166px; }
  .st-key-coach_panel {
    height: min(620px, calc(100vh - 150px));
    max-height: 620px;
  }
  .seat-left { left: 3px; }
  .seat-right { right: 3px; }
  .hole-left { left: 12%; }
  .hole-right { right: 12%; }
}
</style>
"""

# -*- coding: utf-8 -*-
# 成果物まとめ 自動精査・再生成スクリプト（コンパクト版）
# html.ai フォルダを毎回スキャンし、PJ別に「必要なもの」を自動精査してHTMLを更新する。
#   - ルーティン系（朝ブリーフィング/週次/月次レビュー等）は自動除外
#   - 各PJごとに更新日時の新しい順で最大 PER_PJ 件を採用（古いものは自然に消える）
#   - 直近 NEW_DAYS 日に更新されたものには 🆕 バッジ
#   - PIN（重要固定）に書いたファイルは常に最優先で表示
import os, datetime, re, glob, json

BASE = os.path.dirname(os.path.abspath(__file__))
OUT  = os.path.join(BASE, "_成果物まとめ_全プレビュー.html")
PER_PJ   = 10      # 1PJあたり最大表示件数
NEW_DAYS = 5       # この日数以内の更新を 🆕 とみなす

# ── 永久除外リスト（このファイルに書いたファイル名は二度と表示されない） ──
HIDE_FILE = os.path.join(BASE, "_非表示リスト.txt")
HIDDEN = set()
if os.path.exists(HIDE_FILE):
    for line in open(HIDE_FILE, encoding="utf-8"):
        s = line.strip()
        if s and not s.startswith("#"):
            HIDDEN.add(s)
else:
    # 初回はテンプレートを作成しておく
    with open(HIDE_FILE, "w", encoding="utf-8") as fp:
        fp.write("# このファイルに「成果物まとめから恒久的に消したいHTMLファイル名」を1行ずつ書く\n")
        fp.write("# 例: trustfit_terms.html\n")

# PJ定義: (表示名, アイコン, 色, 説明, [ファイル名に含まれるキーワード], [PIN=常に最優先で出す代表ファイル])
PROJECTS = [
    ("TrustFit", "🤝", "#2563eb", "企業向けトレーナー派遣マッチングPF",
        ["trustfit"],
        ["TrustFit_事業企画書.html", "trustfit-proposal-lp.html", "TrustFit_全体まとめ.html"]),
    ("PRISM CUP", "🏆", "#9333ea", "スポーツイベント／クラファン",
        ["prism", "プリズム"],
        ["プリズムカップ_企画書.html", "prismcup-proposal.html", "prismcup_sponsor.html"]),
    ("CARAS", "💪", "#dc2626", "パーソナルジム（西宮・夙川）",
        ["caras"],
        ["caras_analysis_report.html", "caras_instagram_strategy.html"]),
    ("SORA / 陸上クラブ", "🏃", "#ea580c", "子ども向け陸上育成クラブ",
        ["sora"],
        ["sora-schedule-2026.html", "sora_overview_infographic.html"]),
    ("オギラボ", "🧠", "#0891b2", "AI活用オンラインサロン",
        ["オギラボ", "ogilab", "note", "MOON_content", "サロン", "tiktok", "sprint", "台本"],
        ["オギラボ_LINE公式設計書.html", "オギラボ_note販売戦略_2026-04-07.html", "MOON_content_menu.html"]),
    ("健康経営", "🏢", "#16a34a", "B2B法人健康支援",
        ["健康経営"],
        ["健康経営優良法人_ギャップ分析.html", "健康経営_進捗管理システム.html"]),
    ("関学・むーん・その他", "📋", "#7c3aed", "法人業務・行政・関係者",
        ["関西学院", "関学", "moon-welfare", "むーん", "deloitte", "取引先", "futsal", "集客", "報告データ", "競技結果"],
        ["関西学院大学陸上競技部_部則図解.html", "取引先マスター.html"]),
    ("AI組織・管理", "⚙️", "#475569", "組織運営・自動化フロー",
        ["AI組織", "oversight", "obsidian"],
        ["AI組織フロー.html", "AI組織_スキル_スケジュール総覧.html", "morning-briefing_latest.html"]),
]

# 除外パターン（ルーティン・テンプレ・自分自身）
EXCLUDE_RE = re.compile(
    r"(^_成果物まとめ|^morning-briefing_2026|^weekly-review|^monthly-review|月次|これです_|"
    r"^oversight-report|^sns-follower|^sns-weekly|buzz_report|voireco-flow|-TEMPLATE|"
    r"^report|報告データ)", re.IGNORECASE)
# ただし morning-briefing_latest.html だけは AI組織のPINで拾うので除外対象から外す

# ── 日本語ラベル辞書（既知ファイル: ファイル名 -> (タイトル, 説明)） ──
LABELS = {
    # TrustFit
    "TrustFit_事業企画書.html": ("事業企画書", "事業の全体像・収益モデル"),
    "trustfit-proposal-lp.html": ("提案LP", "サービス紹介ランディングページ"),
    "TrustFit_全体まとめ.html": ("全体まとめ", "設計・戦略の総まとめ"),
    "trustfit_sora_superior_integrated_20260522.html": ("SORA/SUPERIOR連携案", "陸上クラブとの統合提案"),
    "trustfit_lp_zehitomo_style.html": ("LP（ゼヒトモ風）", "ランディングページ案"),
    "trustfit_register_company.html": ("企業登録ページ", "採用企業の登録画面"),
    "trustfit_terms.html": ("利用規約", "サービス利用規約"),
    "trustfit_simulator.html": ("料金シミュレーター", "料金シミュレーション"),
    "trustfit_register_cast.html": ("トレーナー登録ページ", "キャスト登録画面"),
    "trustfit_ranks.html": ("ランク制度", "トレーナーランク設計"),
    "TrustFit_matcher_demo.html": ("マッチングデモ", "マッチング機能のデモ画面"),
    "TrustFit_モニター提案書.html": ("モニター提案書", "モニター募集向け提案"),
    "TrustFit_籠谷様_提案書.html": ("籠谷様 提案書", "採用企業向け個別提案"),
    "TrustFit_新機能要件ロードマップ.html": ("新機能ロードマップ", "今後の開発計画"),
    "TrustFit_事業企画書.html ": ("事業企画書", "事業の全体像・収益モデル"),
    # PRISM CUP
    "プリズムカップ_企画書.html": ("企画書", "イベント全体企画"),
    "prismcup-proposal.html": ("提案書", "スポンサー・関係者向け提案"),
    "prismcup_proposal.html": ("提案書", "スポンサー・関係者向け提案"),
    "prismcup_sponsor.html": ("スポンサー資料", "協賛メニュー一覧"),
    "prismcup_proposal_20260522.html": ("提案書（5/22版）", "提案書の改訂版"),
    "prismcup-prospect-list.html": ("見込み客リスト", "営業先リスト"),
    "prismcup-master.html": ("運営マスター", "運営管理ダッシュボード"),
    "prismcup-crm.html": ("顧客管理（CRM）", "関係者・顧客の管理"),
    "prismcup_cast_guide.html": ("キャストガイド", "出演者向け案内"),
    "prismcup_participant_guide.html": ("参加者ガイド", "出場選手向け案内"),
    "prismcup_company_notice.html": ("企業向け案内", "協賛企業への通知文"),
    "prismcup-dm-templates.html": ("DMテンプレート", "営業DMの文面集"),
    "prismcup-timeschedule.html": ("タイムスケジュール", "当日進行表"),
    "prismcup_sponsor_dm.html": ("スポンサーDM", "協賛打診DM文面"),
    # CARAS
    "caras_analysis_report.html": ("分析レポート", "現状分析・改善提案"),
    "caras_instagram_strategy.html": ("Instagram戦略", "SNS集客戦略"),
    "caras_instagram_20260415.html": ("Instagram投稿（4/15）", "Instagram投稿案"),
    "caras_madame_diagnosis.html": ("マダム向け診断", "女性向け診断コンテンツ"),
    "caras_golf_diagnosis.html": ("ゴルフ診断", "ゴルファー向け診断コンテンツ"),
    "caras_madame_ad_1x1.html": ("マダム向け広告", "正方形広告クリエイティブ"),
    "caras_golf_ad_1x1.html": ("ゴルフ広告", "正方形広告クリエイティブ"),
    "CARAS_AI指示文.html": ("AI指示文", "コンテンツ生成用プロンプト"),
    "caras_blog_4weeks.html": ("ブログ4週分", "HP用ブログ記事ストック"),
    # SORA
    "sora-schedule-2026.html": ("年間スケジュール2026", "練習・イベント年間計画"),
    "sora_overview_infographic.html": ("クラブ概要インフォグラフィック", "クラブ紹介ビジュアル"),
    "sora_new_operator_strategy.html": ("新運営者戦略", "運営体制の戦略"),
    "sora_yonden_strategy_v2.html": ("四電戦略v2", "四国電力 提携・拡大戦略"),
    "sora_yonden_training_strategy.html": ("四電トレーニング戦略", "指導プログラム戦略"),
    "sora_base_full_facility.html": ("拠点フル施設案", "拠点施設の全体構想"),
    "sora_base_building_cost.html": ("拠点建設コスト", "施設建設費の試算"),
    "sora_yashima_meeting_script.html": ("八島MTG台本", "商談トークスクリプト"),
    "sora_reality_check.html": ("現実性チェック", "事業の実現性検証"),
    "sora_yashima_program.html": ("八島プログラム", "拠点別プログラム"),
    "sora_event_plan_2026.html": ("イベント企画2026", "年間イベント計画"),
    "sora_kagawa_plan_2027.html": ("香川展開プラン2027", "香川エリア展開計画"),
    # オギラボ
    "オギラボ_LINE公式設計書.html": ("LINE公式設計書", "LINE構築の全体設計"),
    "オギラボ_note販売戦略_2026-04-07.html": ("note販売戦略", "有料note収益化戦略"),
    "MOON_content_menu.html": ("コンテンツメニュー", "全コンテンツ一覧"),
    "競技結果がすべてじゃない_NOTE記事_統合版.html": ("NOTE記事「競技結果がすべてじゃない」", "統合版note記事"),
    "note_kinniku-tsuu_olympian.html": ("note「筋肉痛とオリンピアン」", "note記事"),
    "note_kinniku-tsuu_olympian_public.html": ("note「筋肉痛とオリンピアン」公開版", "公開用note記事"),
    "note完全版_進捗管理.html": ("note完全版・進捗管理", "コンテンツ進捗管理"),
    "note_食事戦略_最終版.html": ("note「食事戦略」最終版", "食事戦略のnote記事"),
    "sprint_ch1_thumb.html": ("スプリント第1章 サムネ", "記事サムネイル"),
    "sprint_ch1_note.html": ("スプリント第1章 note", "連載note記事"),
    "note_article.html": ("note記事", "note本文"),
    "note_article_運動会スタート.html": ("note記事「運動会スタート」", "note本文"),
    "note有料コンテンツ_初月5本.html": ("note有料コンテンツ 初月5本", "有料note記事案"),
    # 健康経営
    "健康経営優良法人_ギャップ分析.html": ("優良法人ギャップ分析", "認定取得に向けた現状分析"),
    "健康経営_進捗管理システム.html": ("進捗管理システム", "取得プロセス管理"),
    "健康経営_取得要項チェックリスト.html": ("取得要項チェックリスト", "申請要件チェック"),
    # 関学・むーん・その他
    "関西学院大学陸上競技部_部則図解.html": ("関学陸上部 部則図解", "部則のビジュアル化"),
    "取引先マスター.html": ("取引先マスター", "全取引先一覧"),
    "deloitte_yonehara_meeting_20260522.html": ("デロイト米原氏 MTG", "部活動地域移行 商談記録"),
    "futsal-event-proposal.html": ("フットサルイベント提案", "企業向けフットサル企画"),
    "集客強化_イベント提案_2026-04-02.html": ("集客強化 イベント提案", "イベント集客企画"),
    "moon-welfare-report_2026-03-28.html": ("むーん 行政報告書", "児童発達支援の行政報告"),
    # AI組織
    "AI組織フロー.html": ("AI組織フロー", "自動化フローの可視化"),
    "AI組織_スキル_スケジュール総覧.html": ("スキル・スケジュール総覧", "全スキル・タスク一覧"),
    "morning-briefing_latest.html": ("最新 朝ブリーフィング", "直近の全PJ進捗報告"),
    "AI組織図_まとめ＆改善提案.html": ("AI組織図・改善提案", "組織設計と改善案"),
}

# 未知ファイル用: 英単語 -> 日本語（フォールバック翻訳）
WORD_JA = {
    "proposal":"提案書","strategy":"戦略","report":"レポート","guide":"ガイド",
    "schedule":"スケジュール","list":"リスト","register":"登録","company":"企業",
    "cast":"キャスト","terms":"規約","simulator":"シミュレーター","ranks":"ランク",
    "rank":"ランク","master":"マスター","crm":"顧客管理","notice":"案内",
    "analysis":"分析","instagram":"Instagram","diagnosis":"診断","golf":"ゴルフ",
    "madame":"マダム","blog":"ブログ","overview":"概要","infographic":"インフォグラフィック",
    "operator":"運営","training":"トレーニング","base":"拠点","facility":"施設",
    "building":"建設","cost":"コスト","meeting":"MTG","script":"台本",
    "reality":"現実","check":"チェック","program":"プログラム","content":"コンテンツ",
    "menu":"メニュー","sprint":"スプリント","thumb":"サムネ","note":"note",
    "welfare":"福祉","futsal":"フットサル","event":"イベント","yonden":"四電",
    "yashima":"八島","sora":"SORA","superior":"SUPERIOR","integrated":"連携",
    "public":"公開版","new":"新","full":"フル","demo":"デモ","matcher":"マッチング",
    "templates":"テンプレート","template":"テンプレート","dm":"DM","sponsor":"スポンサー",
    "participant":"参加者","prospect":"見込み客","plan":"プラン","kagawa":"香川",
    "weeks":"週分","article":"記事","monitor":"モニター","ad":"広告","style":"風",
    "zehitomo":"ゼヒトモ","lp":"LP","contact":"問い合わせ","faq":"FAQ","privacy":"プライバシー",
}

def _translate_tokens(base):
    base = re.sub(r"20\d{6}", "", base)               # 20260522 など
    base = re.sub(r"\b20\d{2}([-_ ]\d{1,2})*\b", "", base)
    parts = re.split(r"[ _\-]+", base)
    out = []
    for p in parts:
        if not p or p.isdigit():
            continue
        low = p.lower()
        out.append(WORD_JA.get(low, p))
    return " ".join(out).strip()

def labels_for(fname):
    """日本語の (タイトル, 説明) を返す。辞書優先、無ければ英単語を和訳。"""
    if fname in LABELS:
        return LABELS[fname]
    base = os.path.splitext(fname)[0]
    # PJ接頭辞を除去
    t = re.sub(r"^(trustfit|caras|sora|prismcup|superior)[ _\-]?", "", base, flags=re.IGNORECASE)
    title = _translate_tokens(t) or _translate_tokens(base) or fname
    memo  = _translate_tokens(base)
    return (title[:30], memo[:34])

# 全HTMLを収集
all_html = [os.path.basename(p) for p in glob.glob(os.path.join(BASE, "*.html"))]

def classify(fname):
    low = fname.lower()
    for (name,icon,color,desc,keys,pins) in PROJECTS:
        if fname in pins:
            return name
    for (name,icon,color,desc,keys,pins) in PROJECTS:
        for k in keys:
            if k.lower() in low:
                return name
    return None  # どのPJにも当てはまらない

# PJ -> 候補ファイル
buckets = {p[0]: [] for p in PROJECTS}
for f in all_html:
    if f in HIDDEN:                       # 永久除外リストにあるものは完全スキップ
        continue
    if f == "morning-briefing_latest.html":
        buckets["AI組織・管理"].append(f); continue
    if EXCLUDE_RE.search(f):
        continue
    pj = classify(f)
    if pj:
        buckets[pj].append(f)

today = datetime.date.today()
now = datetime.datetime.now().timestamp()
total = 0
nav_html, sec_html = [], []

for i,(name,icon,color,desc,keys,pins) in enumerate(PROJECTS):
    files = buckets[name]
    # 重複除去
    files = list(dict.fromkeys(files))
    # PIN を先頭固定、残りは更新日時の新しい順
    pinned = [f for f in pins if f in files]
    rest   = [f for f in files if f not in pinned]
    rest.sort(key=lambda f: os.path.getmtime(os.path.join(BASE,f)), reverse=True)
    chosen = (pinned + rest)[:PER_PJ]
    if not chosen:
        continue
    sid=f"s{i}"
    nav_html.append(f'<a href="#{sid}" class="pill" style="--c:{color}">{icon} {name}<b>{len(chosen)}</b></a>')
    rows=[]
    for f in chosen:
        mt = os.path.getmtime(os.path.join(BASE,f))
        days = (now - mt)/86400
        new = ' <span class="new">🆕</span>' if days <= NEW_DAYS else ""
        d = datetime.date.fromtimestamp(mt).strftime("%-m/%-d")
        _t, _m = labels_for(f)
        rows.append(f'''<li class="row" data-file="{f}">
  <div class="ri" data-src="{f}">
    <button class="hide" type="button" title="この表示から消す">×</button>
    <span class="dot"></span>
    <span class="t">{_t}{new}</span>
    <span class="m">{_m}</span>
    <span class="date">{d}</span>
    <span class="acts"><button class="pv" type="button">👁</button><a href="{f}" target="_blank" rel="noopener" class="op">開く↗</a></span>
  </div>
  <div class="frame"></div>
</li>''')
        total += 1
    sec_html.append(f'''<section id="{sid}" class="sec" style="--c:{color}">
  <h2><span>{icon}</span>{name}<small>{desc}</small></h2>
  <ul class="list">{''.join(rows)}</ul>
</section>''')

stamp = datetime.datetime.now().strftime("%Y年%m月%d日 %H:%M")
perma_json = json.dumps(sorted(HIDDEN), ensure_ascii=False)

html=f'''<!DOCTYPE html><html lang="ja"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>成果物まとめ</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,"Hiragino Sans","Yu Gothic",sans-serif;background:#f4f6f9;color:#1f2937;font-size:14px}}
.hero{{background:#1e293b;color:#fff;padding:18px 20px;display:flex;align-items:baseline;gap:14px;flex-wrap:wrap}}
.hero h1{{font-size:18px}}
.hero span{{color:#94a3b8;font-size:12px}}
.nav{{position:sticky;top:0;z-index:20;background:#fff;border-bottom:1px solid #e5e7eb;padding:8px 10px;display:flex;flex-wrap:wrap;gap:6px}}
.pill{{text-decoration:none;color:var(--c);border:1px solid var(--c);padding:3px 9px;border-radius:14px;font-size:12px;font-weight:600;display:inline-flex;align-items:center;gap:5px}}
.pill b{{background:var(--c);color:#fff;border-radius:8px;padding:0 6px;font-size:10px;font-weight:700}}
.pill:hover{{background:var(--c);color:#fff}}
.pill:hover b{{background:#fff;color:var(--c)}}
.wrap{{max-width:920px;margin:0 auto;padding:14px 12px 50px}}
.sec{{margin-bottom:20px;scroll-margin-top:54px}}
.sec h2{{font-size:15px;color:var(--c);display:flex;align-items:center;gap:7px;padding:6px 4px;border-bottom:2px solid var(--c);margin-bottom:6px}}
.sec h2 small{{font-weight:400;color:#94a3b8;font-size:11px;margin-left:auto}}
.list{{list-style:none;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,.06)}}
.row{{border-bottom:1px solid #f1f3f6}}
.row:last-child{{border-bottom:0}}
.ri{{display:flex;align-items:center;gap:9px;padding:8px 12px;cursor:pointer}}
.ri:hover{{background:#f8fafc}}
.dot{{width:7px;height:7px;border-radius:50%;background:var(--c);flex:none}}
.t{{font-weight:600;font-size:13.5px;white-space:nowrap}}
.new{{font-size:10px}}
.m{{color:#94a3b8;font-size:11.5px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex:1}}
.date{{color:#cbd5e1;font-size:10.5px;flex:none}}
.acts{{display:flex;gap:6px;flex:none;align-items:center}}
.pv{{border:1px solid #d1d5db;background:#fff;color:#475569;font-size:11px;padding:2px 7px;border-radius:6px;cursor:pointer}}
.pv:hover{{background:#f1f5f9}}
.op{{font-size:11px;color:var(--c);text-decoration:none;font-weight:600;padding:2px 4px}}
.op:hover{{text-decoration:underline}}
.frame{{height:0;overflow:hidden;transition:height .2s;background:#f8fafc}}
.frame.open{{height:340px;border-top:1px solid #e5e7eb}}
.frame iframe{{width:100%;height:340px;border:0}}
/* 編集・非表示まわり */
.ctrl{{margin-left:auto;display:flex;gap:8px;align-items:center}}
.btn{{background:rgba(255,255,255,.14);color:#fff;border:1px solid rgba(255,255,255,.3);border-radius:8px;font-size:12px;padding:4px 10px;cursor:pointer}}
.btn:hover{{background:rgba(255,255,255,.28)}}
.hidecnt{{color:#cbd5e1;font-size:12px}}
.hidecnt a{{color:#fca5a5;cursor:pointer;text-decoration:underline;margin-left:4px}}
.hide{{display:none;flex:none;width:20px;height:20px;border-radius:50%;border:1px solid #fca5a5;background:#fff;color:#dc2626;font-size:13px;line-height:1;cursor:pointer;padding:0}}
.hide:hover{{background:#dc2626;color:#fff}}
body.edit .hide{{display:inline-flex;align-items:center;justify-content:center}}
body.edit .ri{{cursor:default}}
.row.gone{{display:none}}
.sec.gone{{display:none}}
@media(max-width:560px){{.m,.date{{display:none}}}}
footer{{text-align:center;color:#9ca3af;font-size:11px;padding:18px}}
</style></head><body>
<div class="hero"><h1>📂 成果物まとめ</h1><span>{total} 件を自動精査 ／ 最終更新 {stamp}　🆕=直近{NEW_DAYS}日</span>
<div class="ctrl"><span class="hidecnt" id="hc"></span><button class="btn" id="saveBtn" type="button" style="display:none">💾 保存</button><button class="btn" id="editBtn" type="button">🗑 編集</button></div></div>
<nav class="nav">{''.join(nav_html)}</nav>
<div class="wrap">{''.join(sec_html)}</div>
<footer>株式会社MOON ／ html.aiを自動スキャンして生成。新しい成果物は自動で追加され、古いものは押し出されます</footer>
<script>
// ── プレビュー展開 ──
document.querySelectorAll('.ri[data-src]').forEach(function(ri){{
  var li=ri.closest('.row'),frame=li.querySelector('.frame'),src=ri.dataset.src;
  function toggle(){{
    if(frame.classList.contains('open')){{frame.classList.remove('open');setTimeout(function(){{frame.innerHTML=''}},200);}}
    else{{if(!frame.querySelector('iframe'))frame.innerHTML='<iframe src="'+src+'" loading="lazy"></iframe>';frame.classList.add('open');}}
  }}
  ri.addEventListener('click',function(e){{
    if(e.target.closest('.op')||e.target.closest('.hide'))return;   // ×やリンクは無視
    if(document.body.classList.contains('edit'))return;             // 編集中はプレビューしない
    toggle();
  }});
}});

// ── 非表示（自分で消す）機能。状態はブラウザに保存され再生成しても保持 ──
var PERMA={perma_json};   // すでに永久除外リストに入っているファイル
var KEY='seika_hidden_v1';
function load(){{ try{{return new Set(JSON.parse(localStorage.getItem(KEY)||'[]'));}}catch(e){{return new Set();}} }}
function save(s){{ try{{localStorage.setItem(KEY,JSON.stringify([...s]));}}catch(e){{}} }}
var hidden=load();

function refresh(){{
  // 行の表示/非表示
  document.querySelectorAll('.row').forEach(function(li){{
    li.classList.toggle('gone', hidden.has(li.dataset.file));
  }});
  // 空になったセクションを隠す＆ナビ件数を更新
  document.querySelectorAll('.sec').forEach(function(sec,i){{
    var vis=sec.querySelectorAll('.row:not(.gone)').length;
    sec.classList.toggle('gone', vis===0);
    var pill=document.querySelectorAll('.nav .pill')[i];
    if(pill){{ var b=pill.querySelector('b'); if(b)b.textContent=vis; pill.style.display=vis===0?'none':''; }}
  }});
  // 非表示カウンタ
  var hc=document.getElementById('hc');
  if(hidden.size>0){{ hc.innerHTML='非表示 '+hidden.size+'件 <a id="resetH">すべて戻す</a>'; }}
  else{{ hc.textContent=''; }}
  var r=document.getElementById('resetH');
  if(r) r.onclick=function(){{ hidden.clear(); save(hidden); refresh(); }};
}}

// ×ボタン
document.querySelectorAll('.hide').forEach(function(btn){{
  btn.addEventListener('click',function(e){{
    e.stopPropagation();
    var li=btn.closest('.row');
    hidden.add(li.dataset.file); save(hidden); refresh();
  }});
}});

// 編集モードのトグル
document.getElementById('editBtn').addEventListener('click',function(){{
  var on=document.body.classList.toggle('edit');
  this.textContent=on?'✓ 完了':'🗑 編集';
  document.getElementById('saveBtn').style.display=on?'':'none';
}});

// 💾 保存：永久除外リスト(_非表示リスト.txt)を書き出す。これを html.ai に置けば全環境で恒久的に消える
document.getElementById('saveBtn').addEventListener('click',function(){{
  var all=new Set(PERMA);
  hidden.forEach(function(f){{all.add(f);}});
  var list=[...all].sort();
  if(list.length===0){{ alert('消したい項目がありません。先に編集モードで × を押してください。'); return; }}
  var text='# 成果物まとめから恒久的に非表示にするHTMLファイル名（1行ずつ）\\n'+list.join('\\n')+'\\n';
  var blob=new Blob([text],{{type:'text/plain;charset=utf-8'}});
  var a=document.createElement('a');
  a.href=URL.createObjectURL(blob);
  a.download='_非表示リスト.txt';
  document.body.appendChild(a); a.click(); a.remove();
  alert('「_非表示リスト.txt」を書き出しました（'+list.length+'件）。\\nこのファイルを html.ai フォルダに上書き保存すると、次回からこれらは完全に表示されなくなります。');
}});

refresh();
</script></body></html>'''

open(OUT,"w",encoding="utf-8").write(html)
print("収録:",total,"件 ／ 出力:",OUT)
for p in PROJECTS:
    print("  ",p[0],"->",len(buckets[p[0]]),"候補")

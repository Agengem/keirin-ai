<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <meta name="apple-mobile-web-app-capable" content="yes" />
  <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
  <meta name="apple-mobile-web-app-title" content="競輪AI予想" />
  <title>KEIRIN AI PREDICTOR PRO</title>
  <style>
    :root {
      --bg: #060a12;
      --card: #101726;
      --card2: #172136;
      --border: #25344f;
      --text: #f1f5f9;
      --muted: #94a3b8;
      --accent: #38bdf8;
      --honmei: #2563eb;
      --ana: #dc2626;
      --ok: #10b981;
      --warn: #f59e0b;
    }
    * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "Hiragino Sans", sans-serif;
      font-size: 13px;
      line-height: 1.4;
      padding-bottom: 40px;
    }
    .wrap { max-width: 980px; margin: 0 auto; padding: 8px; }
    .top-bar {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 8px 10px;
      margin-bottom: 8px;
    }
    .top-row { display: flex; align-items: center; justify-content: space-between; gap: 6px; }
    .brand { font-weight: 800; font-size: 14px; display: flex; align-items: center; gap: 6px; }
    .badge { font-size: 10px; padding: 2px 6px; border-radius: 999px; background: #1e293b; color: var(--accent); font-weight: 700; }
    .btn {
      background: var(--card2); color: var(--text); border: 1px solid var(--border);
      border-radius: 7px; padding: 5px 9px; font-size: 11px; font-weight: 700; cursor: pointer;
    }
    .btn.active { background: var(--accent); color: #041019; border-color: var(--accent); }
    .btn.honmei-active { background: var(--honmei); color: #fff; border-color: var(--honmei); }
    .btn.ana-active { background: var(--ana); color: #fff; border-color: var(--ana); }
    .collapse-body.hidden { display: none; }
    .controls-grid { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 7px; align-items: center; }
    input[type="number"], input[type="text"] {
      background: var(--bg); color: var(--text); border: 1px solid var(--border);
      border-radius: 7px; padding: 5px 7px; font-size: 12px;
    }
    .stats-strip { display: grid; grid-template-columns: repeat(4, 1fr); gap: 5px; margin-bottom: 8px; }
    .stat-box { background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 6px; text-align: center; }
    .stat-label { font-size: 10px; color: var(--muted); }
    .stat-val { font-size: 14px; font-weight: 800; margin-top: 1px; }
    .race-bar { display: flex; gap: 5px; overflow-x: auto; padding-bottom: 4px; margin-bottom: 8px; }
    .race-chip {
      flex-shrink: 0; padding: 5px 9px; border-radius: 7px; border: 1px solid var(--border);
      background: var(--card); color: var(--text); font-size: 11px; font-weight: 700; cursor: pointer;
    }
    .race-chip.active { background: var(--accent); color: #041019; border-color: var(--accent); }
    .ai-box {
      background: var(--card); border: 1px solid var(--border); border-radius: 10px;
      padding: 9px 10px; margin-bottom: 8px;
    }
    .ai-title { font-weight: 800; color: var(--accent); font-size: 12px; margin-bottom: 4px; }
    .line-tags { display: flex; flex-wrap: wrap; gap: 6px; margin: 6px 0; }
    .line-tag { background: var(--card2); border: 1px solid var(--border); border-radius: 6px; padding: 3px 7px; font-size: 11px; font-weight: 700; }
    .player-table { width: 100%; border-collapse: collapse; font-size: 11px; margin-top: 6px; }
    .player-table th { color: var(--muted); text-align: left; border-bottom: 1px solid var(--border); padding: 3px 4px; }
    .player-table td { padding: 4px; border-bottom: 1px solid #182236; }
    .two-col { display: grid; grid-template-columns: 1fr; gap: 8px; }
    @media (min-width: 760px) { .two-col { grid-template-columns: 1fr 1fr; } }
    .panel { background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 9px; }
    .panel.honmei { border-top: 3px solid var(--honmei); }
    .panel.ana { border-top: 3px solid var(--ana); }
    .panel-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 7px; font-weight: 800; font-size: 13px; }
    .bet-item {
      display: flex; align-items: center; justify-content: space-between; gap: 7px;
      background: var(--card2); border: 1px solid var(--border); border-radius: 8px;
      padding: 6px 8px; margin-bottom: 5px;
    }
    .balls { display: flex; align-items: center; gap: 3px; flex-shrink: 0; }
    .ball {
      width: 21px; height: 21px; border-radius: 50%; display: inline-flex; align-items: center;
      justify-content: center; font-size: 11px; font-weight: 800; color: #fff; background: #334155;
    }
    .c1 { background: #f8fafc; color: #0f172a; }
    .c2 { background: #1e293b; border: 1px solid #64748b; }
    .c3 { background: #dc2626; }
    .c4 { background: #2563eb; }
    .c5 { background: #eab308; color: #0f172a; }
    .c6 { background: #16a34a; }
    .c7 { background: #ea580c; }
    .c8 { background: #db2777; }
    .c9 { background: #7c3aed; }
    .reason { font-size: 11px; color: var(--muted); flex: 1; min-width: 0; }
    .ev-tag { display: inline-block; font-size: 10px; color: var(--accent); font-weight: 700; }
    .right-meta { text-align: right; flex-shrink: 0; font-size: 11px; }
    .odds { font-weight: 800; color: var(--warn); font-size: 12px; }
    .pay { font-weight: 800; color: var(--ok); font-size: 10px; }
    .muted { color: var(--muted); font-size: 11px; }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="top-bar">
      <div class="top-row">
        <div class="brand">🚴 競輪AI ENGINE <span class="badge" id="syncStatus">読込中</span></div>
        <div style="display:flex;gap:5px;">
          <button class="btn active" id="btnToday" onclick="switchDay('today')">本日</button>
          <button class="btn" id="btnTomorrow" onclick="switchDay('tomorrow')">翌日</button>
          <button class="btn" id="btnToggle" onclick="toggleHeader()">▲ 畳む</button>
        </div>
      </div>
      <div class="collapse-body" id="collapseBody">
        <div class="controls-grid">
          <label class="muted">予算: <input type="number" id="budgetInput" value="10000" step="100" min="600" style="width:84px;" onchange="renderAll()" /></label>
          <button class="btn honmei-active" id="modeHonmei" onclick="setMode('honmei')">本命のみ</button>
          <button class="btn" id="modeAna" onclick="setMode('ana')">穴のみ</button>
          <button class="btn" id="modeHybrid" onclick="setMode('hybrid')">両方配分</button>
          <button class="btn" onclick="loadAllData(true)">🔄 再取得</button>
        </div>
        <div class="controls-grid">
          <span class="muted">結果記録:</span>
          <input type="text" id="resInput" placeholder="1-2-4" style="width:74px;" />
          <input type="number" id="payoutInput" placeholder="払戻円" style="width:84px;" />
          <button class="btn" onclick="recordResult()">判定保存</button>
        </div>
      </div>
    </div>

    <div class="stats-strip">
      <div class="stat-box"><div class="stat-label">的中率</div><div class="stat-val" id="statHitRate">0%</div></div>
      <div class="stat-box"><div class="stat-label">回収率</div><div class="stat-val" id="statRoi">0%</div></div>
      <div class="stat-box"><div class="stat-label">本日収支</div><div class="stat-val" id="statProfit">¥0</div></div>
      <div class="stat-box"><div class="stat-label">最高配当</div><div class="stat-val" id="statMax">¥0</div></div>
    </div>

    <div class="race-bar" id="raceBar"></div>

    <div class="ai-box" id="aiAnalysisBox">
      <div class="ai-title">🧠 AI展開＆バンク解析レポート</div>
      <div id="aiSummaryText" class="muted">出走表データを解析中...</div>
      <div class="line-tags" id="lineTags"></div>
      <details>
        <summary class="muted" style="cursor:pointer;margin-top:4px;">出走表・競走得点・AI評価スコアを見る</summary>
        <table class="player-table">
          <thead><tr><th>車</th><th>選手名</th><th>脚</th><th>得点</th><th>B</th><th>AI指数</th></tr></thead>
          <tbody id="playerTbody"></tbody>
        </table>
      </details>
    </div>

    <div class="two-col">
      <div class="panel honmei">
        <div class="panel-head"><span>🎯 本命・EV重視（3連単）</span><span id="honmeiCountBadge" class="badge">0点</span></div>
        <div id="honmeiList"></div>
      </div>
      <div class="panel ana">
        <div class="panel-head"><span>🔥 穴・万車券狙い（3連単）</span><span id="anaCountBadge" class="badge">0点</span></div>
        <div id="anaList"></div>
      </div>
    </div>
  </div>

  <script>
    const BANKS = {
      "前橋": { len: 335, straight: 46.7, type: "33超高速・先行有利" },
      "松戸": { len: 333, straight: 38.2, type: "33直線短・逃げ粘り" },
      "小田原": { len: 333, straight: 36.1, type: "33カント急・先行天国" },
      "伊東": { len: 333, straight: 46.6, type: "33直線長め・番手差し" },
      "奈良": { len: 333, straight: 38.0, type: "33先行有利・捲り不発注意" },
      "富山": { len: 333, straight: 43.0, type: "33先行〜番手有利" },
      "防府": { len: 333, straight: 42.5, type: "33先行有利" },
      "宇都宮": { len: 500, straight: 63.3, type: "500直線長・差し強襲" },
      "大宮": { len: 500, straight: 66.7, type: "500超長直線・追い込み天国" },
      "高知": { len: 500, straight: 52.0, type: "500皿バンク・先行残る" },
      "立川": { len: 400, straight: 58.0, type: "400直線長・差し有利" },
      "弥彦": { len: 400, straight: 63.1, type: "400直線最長クラス・追込有利" },
      "武雄": { len: 400, straight: 64.4, type: "400直線超長・番手差し決着多" },
      "小倉": { len: 400, straight: 56.9, type: "ドーム無風・スピード捲り" },
      "川崎": { len: 400, straight: 58.0, type: "400軽バンク・差し捲り互角" },
      "平塚": { len: 400, straight: 54.2, type: "400高速標準バンク" },
      "四日市": { len: 400, straight: 62.4, type: "400直線長・外伸び注意" },
      "玉野": { len: 400, straight: 47.9, type: "400直線短め・先行番手" },
      "福井": { len: 400, straight: 52.8, type: "400標準クセなし" },
      "静岡": { len: 400, straight: 56.4, type: "400直線やや長・差し有利" },
      "松山": { len: 400, straight: 58.6, type: "400軽走路・捲り差し伸びる" },
      "西武園": { len: 400, straight: 47.6, type: "400みなし33・先行有利" }
    };

    const state = {
      day: "today",
      data: { today: { races: [] }, tomorrow: { races: [] } },
      selectedIdx: 0,
      mode: "honmei",
      records: JSON.parse(localStorage.getItem("keirin_ai_records_v2") || "[]")
    };

    function toggleHeader() {
      const body = document.getElementById("collapseBody");
      const btn = document.getElementById("btnToggle");
      body.classList.toggle("hidden");
      btn.textContent = body.classList.contains("hidden") ? "▼ 開く" : "▲ 畳む";
    }

    function setMode(m) {
      state.mode = m;
      document.getElementById("modeHonmei").className = "btn" + (m === "honmei" ? " honmei-active" : "");
      document.getElementById("modeAna").className = "btn" + (m === "ana" ? " ana-active" : "");
      document.getElementById("modeHybrid").className = "btn" + (m === "hybrid" ? " active" : "");
      renderAll();
    }

    function switchDay(d) {
      state.day = d;
      state.selectedIdx = 0;
      document.getElementById("btnToday").className = "btn" + (d === "today" ? " active" : "");
      document.getElementById("btnTomorrow").className = "btn" + (d === "tomorrow" ? " active" : "");
      renderAll();
    }

    async function loadAllData(force = false) {
      const statusEl = document.getElementById("syncStatus");
      statusEl.textContent = "同期中...";
      const q = force ? `?t=${Date.now()}` : "";
      for (const d of ["today", "tomorrow"]) {
        try {
          const res = await fetch(`./data/${d}.json${q}`, { cache: "no-store" });
          if (res.ok) state.data[d] = await res.json();
        } catch (e) {}
      }
      const cToday = state.data.today.races?.length || 0;
      const cTom = state.data.tomorrow.races?.length || 0;
      statusEl.textContent = (cToday + cTom) > 0 ? `本日${cToday}R / 翌日${cTom}R` : "データ未取得";
      renderAll();
    }

    function runKeirinAiEngine(race) {
      const bank = BANKS[race?.venue] || { len: 400, straight: 54.0, type: "400標準バンク" };
      const isShort = bank.len === 333 || bank.len === 335 || bank.straight < 48;
      const isLong = bank.len === 500 || bank.straight >= 58;

      const rawPlayers = race?.players?.length >= 5 ? race.players : [
        { car: 1, name: "サンプル軸", score: 94.5, style: "両", b: 4, line: 1, pos: 1 },
        { car: 2, name: "サンプル番手", score: 91.2, style: "追", b: 0, line: 1, pos: 2 },
        { car: 3, name: "サンプル三番", score: 86.0, style: "追", b: 0, line: 1, pos: 3 },
        { car: 4, name: "対抗先行", score: 89.8, style: "逃", b: 9, line: 2, pos: 1 },
        { car: 5, name: "対抗番手", score: 87.4, style: "追", b: 1, line: 2, pos: 2 },
        { car: 6, name: "単騎一発", score: 83.1, style: "両", b: 2, line: 0, pos: 1 },
        { car: 7, name: "穴追込", score: 80.5, style: "追", b: 0, line: 0, pos: 1 }
      ];

      // ライン構成整理
      const lineMap = {};
      rawPlayers.forEach(p => {
        if (p.line > 0) {
          if (!lineMap[p.line]) lineMap[p.line] = [];
          lineMap[p.line].push(p);
        }
      });
      Object.values(lineMap).forEach(arr => arr.sort((a, b) => a.pos - b.pos));
      const lineGroups = Object.values(lineMap);
      const escapeLines = lineGroups.filter(g => g[0]?.style === "逃" || (g[0]?.b || 0) >= 4);
      const isFumiai = escapeLines.length >= 2; // 先行2車以上の踏み合い判定

      // 各選手のAI能力値・展開補正スコアを算出
      const evaluated = rawPlayers.map(p => {
        let aiScore = p.score;
        const myLine = lineMap[p.line] || [p];
        const lineLen = myLine.length;

        // ライン人数ボーナス
        if (lineLen >= 3) aiScore += 2.8;
        else if (lineLen === 2) aiScore += 1.4;
        else aiScore -= 1.2;

        // ポジション＆バンク特性補正
        if (p.pos === 1) {
          aiScore += (p.b || 0) * 0.35;
          if (isShort && !isFumiai) aiScore += 3.2;
          if (isFumiai) aiScore -= 2.2;
        } else if (p.pos === 2) {
          const leader = myLine[0];
          if (leader && (leader.style === "逃" || (leader.b || 0) >= 3)) {
            aiScore += 3.5; // 番手絶好展開
            if (isLong) aiScore += 2.4; // 直線長いバンクで番手差し強化
          }
        } else if (p.pos >= 3) {
          if (isLong) aiScore += 1.5;
        }

        // 踏み合い時の単騎・捲り脚質ボーナス
        if (isFumiai && p.line === 0 && p.style === "両") {
          aiScore += 3.4;
        }

        return { ...p, aiScore: +aiScore.toFixed(2) };
      });

      evaluated.sort((a, b) => b.aiScore - a.aiScore);

      // ソフトマックス確率化
      const maxS = evaluated[0].aiScore;
      const exps = evaluated.map(p => Math.exp((p.aiScore - maxS) * 0.32));
      const sumExp = exps.reduce((a, b) => a + b, 0);
      evaluated.forEach((p, idx) => { p.prob = exps[idx] / sumExp; });

      // 混戦度から買い目点数を自動決定（6〜15点）
      const topGap = evaluated[0].aiScore - evaluated[3].aiScore;
      const numLines = lineGroups.length;
      let betCount = 9;
      if (topGap >= 6.5 && numLines <= 2 && !isFumiai) betCount = 6;
      else if (topGap >= 4.5 && !isFumiai) betCount = 8;
      else if (isFumiai || numLines >= 4 || topGap < 2.5) betCount = 14;
      else betCount = 11;

      // 全3連単組み合わせの期待値・シナリオ評価
      const allCombos = [];
      for (let i = 0; i < evaluated.length; i++) {
        for (let j = 0; j < evaluated.length; j++) {
          if (i === j) continue;
          for (let k = 0; k < evaluated.length; k++) {
            if (k === i || k === j) continue;
            const p1 = evaluated[i], p2 = evaluated[j], p3 = evaluated[k];
            const rem1 = Math.max(0.05, 1 - p1.prob);
            const rem2 = Math.max(0.05, rem1 - p2.prob);
            let trueProb = p1.prob * (p2.prob / rem1) * (p3.prob / rem2);

            const sameLine12 = p1.line > 0 && p1.line === p2.line;
            let tag = "実力上位決着";
            if (sameLine12 && p1.pos === 1 && p2.pos === 2) {
              trueProb *= 1.38;
              tag = "ラインワンツー";
            } else if (sameLine12 && p1.pos === 2 && p2.pos === 1) {
              trueProb *= isLong ? 1.45 : 1.28;
              tag = "番手差し切り";
            } else if (p1.line > 0 && p2.line > 0 && p1.line !== p2.line) {
              tag = "別線スジ違い";
            } else if (p1.line === 0) {
              trueProb *= isFumiai ? 1.35 : 0.92;
              tag = "単騎一発捲り";
            }

            // 市場想定オッズと期待値(EV)
            const marketProb = Math.max(0.0012, trueProb * (sameLine12 ? 1.18 : 0.72));
            const estOdds = +Math.min(999.9, Math.max(3.2, (0.75 / marketProb))).toFixed(1);
            const ev = +(trueProb * estOdds).toFixed(2);

            allCombos.push({
              combo: [p1.car, p2.car, p3.car],
              trueProb,
              odds: estOdds,
              ev,
              reason: tag
            });
          }
        }
      }

      // 本命買い目（的中確率×EVバランス重視）
      const honmei = [...allCombos]
        .filter(c => c.odds <= 95.0)
        .sort((a, b) => (b.trueProb * Math.sqrt(b.ev)) - (a.trueProb * Math.sqrt(a.ev)))
        .slice(0, betCount);

      // 穴・万車券買い目（35倍以上かつEVが高い別線・単騎・ヒモ荒れ重視）
      const ana = [...allCombos]
        .filter(c => c.odds >= 35.0 && !honmei.some(h => h.combo.join("-") === c.combo.join("-")))
        .sort((a, b) => b.ev - a.ev)
        .slice(0, betCount);

      const summary = `【${bank.type} / 直線${bank.straight}m】${isFumiai ? "先行型複数で踏み合い濃厚！番手差し＆単騎一発警戒。" : "主導権ライン明確。スジ決着を軸に3着ヒモ抜けをカバー。"} 混戦度判定により最適買い目「${betCount}点」を自動選出。`;

      return { evaluated, lineGroups, honmei, ana, betCount, summary };
    }

    function allocate(items, budget) {
      if (!items.length || budget <= 0) return [];
      const unit = 100;
      const totalUnits = Math.max(items.length, Math.floor(budget / unit));
      const weights = items.map(it => 1 / Math.max(1.5, it.odds));
      const wSum = weights.reduce((a, b) => a + b, 0);
      let amts = weights.map(w => Math.max(unit, Math.round((w / wSum) * totalUnits) * unit));
      let diff = totalUnits * unit - amts.reduce((a, b) => a + b, 0);
      let idx = 0;
      while (diff !== 0 && items.length > 0) {
        const step = diff > 0 ? unit : -unit;
        if (amts[idx] + step >= unit) {
          amts[idx] += step;
          diff -= step;
        }
        idx = (idx + 1) % items.length;
        if (idx === 0 && diff < 0 && amts.every(a => a <= unit)) break;
      }
      return items.map((it, i) => ({ ...it, amount: amts[i] }));
    }

    function renderBalls(combo) {
      return combo.map(n => `<span class="ball c${n}">${n}</span>`).join('<span class="muted">-</span>');
    }

    function recordResult() {
      const res = document.getElementById("resInput").value.trim();
      const payout = Number(document.getElementById("payoutInput").value || 0);
      const budget = Number(document.getElementById("budgetInput").value || 10000);
      if (!res) return;
      const race = (state.data[state.day]?.races || [])[state.selectedIdx];
      state.records.push({ title: race?.title || "レース", res, spend: budget, payout, hit: payout > 0 });
      localStorage.setItem("keirin_ai_records_v2", JSON.stringify(state.records));
      document.getElementById("resInput").value = "";
      document.getElementById("payoutInput").value = "";
      renderStats();
    }

    function renderStats() {
      const totalR = state.records.length;
      const hits = state.records.filter(r => r.hit).length;
      const spend = state.records.reduce((a, b) => a + b.spend, 0);
      const payout = state.records.reduce((a, b) => a + b.payout, 0);
      const maxPay = state.records.reduce((a, b) => Math.max(a, b.payout), 0);
      const profit = payout - spend;

      document.getElementById("statHitRate").textContent = totalR ? `${Math.round((hits / totalR) * 100)}%` : "0%";
      document.getElementById("statRoi").textContent = spend ? `${Math.round((payout / spend) * 100)}%` : "0%";
      document.getElementById("statProfit").textContent = `${profit >= 0 ? "+" : ""}¥${profit.toLocaleString()}`;
      document.getElementById("statMax").textContent = `¥${maxPay.toLocaleString()}`;
    }

    function renderAll() {
      renderStats();
      const races = state.data[state.day]?.races || [];
      const bar = document.getElementById("raceBar");

      if (!races.length) {
        bar.innerHTML = `<span class="muted">データ未取得です。GitHub Actionsを実行後「🔄 再取得」を押してください（下はAI計算デモ表示）。</span>`;
      } else {
        if (state.selectedIdx >= races.length) state.selectedIdx = 0;
        bar.innerHTML = races.map((r, i) =>
          `<button class="race-chip ${i === state.selectedIdx ? "active" : ""}" onclick="state.selectedIdx=${i};renderAll();">${r.title}</button>`
        ).join("");
      }

      const currentRace = races[state.selectedIdx] || { venue: "小倉", raceNum: 11, title: "サンプルレース" };
      const ai = runKeirinAiEngine(currentRace);

      document.getElementById("aiSummaryText").textContent = `${currentRace.title}｜${ai.summary}`;
      document.getElementById("lineTags").innerHTML = ai.lineGroups.map((grp, i) =>
        `<span class="line-tag">ライン${i + 1}: ${grp.map(p => `${p.car}${p.name}`).join(" - ")}</span>`
      ).join("");

      document.getElementById("playerTbody").innerHTML = ai.evaluated.map(p => `
        <tr>
          <td><span class="ball c${p.car}" style="width:18px;height:18px;font-size:10px;">${p.car}</span></td>
          <td>${p.name}</td>
          <td>${p.style}</td>
          <td>${p.score.toFixed(1)}</td>
          <td>${p.b || 0}</td>
          <td style="color:var(--accent);font-weight:700;">${p.aiScore}</td>
        </tr>
      `).join("");

      const budget = Math.max(600, Number(document.getElementById("budgetInput").value || 10000));
      let hBudget = 0, aBudget = 0;
      if (state.mode === "honmei") hBudget = budget;
      else if (state.mode === "ana") aBudget = budget;
      else { hBudget = Math.round(budget * 0.6); aBudget = budget - hBudget; }

      const hList = allocate(ai.honmei, hBudget);
      const aList = allocate(ai.ana, aBudget);

      document.getElementById("honmeiCountBadge").textContent = `${hList.length}点`;
      document.getElementById("anaCountBadge").textContent = `${aList.length}点`;

      const renderItem = b => `
        <div class="bet-item">
          <div class="balls">${renderBalls(b.combo)}</div>
          <div class="reason">${b.reason} <span class="ev-tag">EV:${b.ev}</span></div>
          <div class="right-meta">
            <div class="odds">${b.odds}倍</div>
            <div>¥${b.amount.toLocaleString()}</div>
            <div class="pay">戻¥${Math.round(b.amount * b.odds).toLocaleString()}</div>
          </div>
        </div>
      `;

      document.getElementById("honmeiList").innerHTML = hList.map(renderItem).join("");
      document.getElementById("anaList").innerHTML = aList.map(renderItem).join("");
    }

    loadAllData();
  </script>
</body>
</html>

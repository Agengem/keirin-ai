import json
import os
import re
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from urllib.parse import urljoin

JST = timezone(timedelta(hours=9))
now_jst = datetime.now(JST)

VENUES = {
    "11": "函館", "12": "青森", "13": "いわき平", "21": "弥彦", "22": "前橋",
    "23": "取手", "24": "宇都宮", "25": "大宮", "26": "西武園", "27": "京王閣",
    "28": "立川", "31": "松戸", "32": "千葉", "34": "川崎", "35": "平塚",
    "36": "小田原", "37": "伊東", "38": "静岡", "42": "名古屋", "43": "岐阜",
    "44": "大垣", "45": "豊橋", "46": "富山", "47": "松阪", "48": "四日市",
    "51": "福井", "53": "奈良", "54": "向日町", "55": "和歌山", "56": "岸和田",
    "61": "玉野", "62": "広島", "63": "防府", "71": "高松", "73": "小松島",
    "74": "高知", "75": "松山", "81": "小倉", "83": "久留米", "84": "武雄",
    "85": "佐世保", "86": "別府", "87": "熊本"
}


def fetch_http(url):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
            "Referer": "https://keirin.kdreams.jp/"
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=12) as res:
            raw = res.read()
            for enc in ("utf-8", "euc-jp", "shift_jis"):
                try:
                    return raw.decode(enc)
                except Exception:
                    continue
            return raw.decode("utf-8", errors="ignore")
    except Exception:
        return ""


def extract_rows_from_html(html):
    raw_rows = re.findall(r'<tr[^>]*>(.*?)</tr>', html, re.S)
    rows = []
    for r in raw_rows:
        cells = [re.sub(r'<[^>]+>', ' ', c) for c in re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', r, re.S)]
        if cells:
            rows.append(cells)
    return rows


def parse_players_from_html(html):
    players = []
    rows = extract_rows_from_html(html)

    for cells in rows:
        cells = [re.sub(r'\s+', ' ', str(c)).strip() for c in cells if str(c).strip()]
        if len(cells) < 3:
            continue

        # 車番（1〜9）の抽出：枠番・車番が並ぶため1〜2桁の数字から車番を特定
        car = None
        num_candidates = []
        for c in cells[:4]:
            if re.fullmatch(r'[1-9]', c):
                num_candidates.append(int(c))
        if len(num_candidates) >= 2:
            # 枠番・車番の2列がある場合は2番目が車番
            car = num_candidates[1]
        elif len(num_candidates) == 1:
            car = num_candidates[0]

        if not car or any(p["car"] == car for p in players):
            continue

        joined = " ".join(cells)

        # 選手名：漢字2〜5文字（スペース区切りの姓・名も結合して取得）
        name = ""
        for c in cells:
            if any(w in c for w in ["級", "班", "県", "府", "都", "道", "競輪", "車番", "選手", "得点", "脚質", "レース", "バンク", "予想", "平均", "勝率", "年齢", "期別"]):
                continue
            m_name = re.search(r'([\u4E00-\u9FFF]{1,4}\s*[\u4E00-\u9FFF]{1,4})', c)
            if m_name:
                cand = re.sub(r'\s+', '', m_name.group(1))
                if 2 <= len(cand) <= 7:
                    name = cand
                    break

        if not name:
            continue

        # 競走得点（例: 85.20, 102.45）
        sc_m = re.search(r'\b([5-9]\d\.\d{1,2}|1[0-2]\d\.\d{1,2})\b', joined)
        score = float(sc_m.group(1)) if sc_m else round(82.0 + (9 - car) * 0.4, 2)

        # 脚質（逃・両・追）
        style_m = re.search(r'(?:^|\s)(逃|両|追)(?:\s|$)', joined)
        style = style_m.group(1) if style_m else "両"

        # B回数
        b_cnt = 0
        for c in cells[4:]:
            if re.fullmatch(r'\d{1,2}', c) and int(c) <= 35:
                b_cnt = int(c)
                break

        players.append({
            "car": car,
            "name": name,
            "score": score,
            "style": style,
            "b": b_cnt,
            "line": 0,
            "pos": 1
        })

    players.sort(key=lambda x: x["car"])
    lines = []
    if len(players) >= 3:
        fronts = [p for p in players if p["style"] == "逃" or p["b"] >= 3]
        if not fronts:
            fronts = players[:2]
        backs = [p for p in players if p not in fronts]
        backs.sort(key=lambda x: x["score"], reverse=True)
        for idx, f in enumerate(fronts[:3]):
            grp = [f["car"]]
            if idx < len(backs):
                grp.append(backs[idx]["car"])
            lines.append(grp)
        for l_idx, grp in enumerate(lines):
            for p in players:
                if p["car"] in grp:
                    p["line"] = l_idx + 1
                    p["pos"] = grp.index(p["car"]) + 1

    return players, lines


def scrape_day_fast(target_dt, suffix):
    date_str = target_dt.strftime("%Y%m%d")
    disp_date = target_dt.strftime("%Y/%m/%d")
    races = []
    seen = set()
    venue_pages = set()
    base_urls = set()

    seeds = [
        "https://keirin.kdreams.jp/racecard/",
        f"https://keirin.kdreams.jp/schedule/{target_dt.strftime('%Y/%m')}/"
    ]
    for s in seeds:
        html = fetch_http(s)
        for h in re.findall(r'href=["\']([^"\']+)["\']', html):
            full = urljoin(s, h).split("#")[0].split("?")[0]
            if "/racecard/" in full and re.search(r'/racecard/\d{8,22}/?$', full):
                venue_pages.add(full)
                if date_str in full:
                    base_urls.add(full)

    # 全会場ページから対象日のURLを収集＋日付置換でも補完
    for vp in sorted(list(venue_pages))[:30]:
        # 会場スラッグと会場コードが取れれば対象日のベースURLも直接構築
        m_v = re.match(r'(https?://[^/]+/[^/]+/racecard/(\d{2}))\d{8}(\d{4,6})/?$', vp.rstrip("/"))
        if m_v:
            base_urls.add(f"{m_v.group(1)}{date_str}010001/")
            base_urls.add(f"{m_v.group(1)}{date_str}{m_v.group(3)}/")

        vh = fetch_http(vp)
        for h in re.findall(r'href=["\']([^"\']+)["\']', vh):
            full = urljoin(vp, h).split("#")[0].split("?")[0]
            if "/racecard/" in full and date_str in full and re.search(r'/racecard/\d{10,22}/?$', full):
                base_urls.add(full)

    # 見つかった全ベースURLから 01R〜12R を展開
    race_urls = set()
    for bu in base_urls:
        clean = bu.rstrip("/")
        m16 = re.match(r'(https?://[^/]+/[^/]+/racecard/\d{14})\d{2}$', clean)
        if m16:
            for r_no in range(1, 13):
                race_urls.add(f"{m16.group(1)}{r_no:02d}/")
        else:
            race_urls.add(clean + "/")

    def process_race(ru):
        r_html = fetch_http(ru)
        if not r_html:
            return None
        title_m = re.search(r'<title>(.*?)</title>', r_html, re.S)
        title = re.sub(r'\s+', ' ', title_m.group(1)).strip() if title_m else ""

        # 対象日以外のページを除外
        if disp_date not in title and f"{target_dt.month}月{target_dt.day}日" not in title:
            return None

        venue_name = next((v for v in VENUES.values() if v in title), None)
        if not venue_name:
            m_code = re.search(r'/racecard/(\d{2})\d{8,}', ru)
            venue_name = VENUES[m_code.group(1)] if (m_code and m_code.group(1) in VENUES) else "競輪"

        rnum_m = re.search(r'(\d{1,2})[RＲ]', title) or re.search(r'(\d{2})/?$', ru)
        race_num = int(rnum_m.group(1)) if rnum_m else 0
        if not (1 <= race_num <= 12):
            return None

        players, lines = parse_players_from_html(r_html)
        if len(players) < 4:
            return None
        return {
            "venue": venue_name,
            "raceNum": race_num,
            "title": f"{venue_name} {race_num}R",
            "lines": lines,
            "players": players
        }

    sorted_candidates = sorted(list(race_urls))[:160]
    with ThreadPoolExecutor(max_workers=16) as ex:
        futures = [ex.submit(process_race, u) for u in sorted_candidates]
        for fut in as_completed(futures):
            item = fut.result()
            if not item:
                continue
            key = f"{item['venue']}_{item['raceNum']}"
            if key in seen:
                continue
            seen.add(key)
            races.append({
                "id": f"{suffix}_{item['venue']}_{item['raceNum']}",
                "date": disp_date,
                "venue": item["venue"],
                "raceNum": item["raceNum"],
                "title": item["title"],
                "lines": item["lines"],
                "players": item["players"]
            })

    races.sort(key=lambda x: (x["venue"], x["raceNum"]))
    return {
        "date": disp_date,
        "updatedAt": now_jst.strftime("%Y-%m-%d %H:%M:%S JST"),
        "source": "live" if races else "empty",
        "count": len(races),
        "debug": [
            f"venues:{len(venue_pages)}",
            f"base:{len(base_urls)}",
            f"expanded:{len(sorted_candidates)}",
            f"parsed:{len(races)}"
        ],
        "races": races
    }


def main():
    os.makedirs("data", exist_ok=True)
    today_data = scrape_day_fast(now_jst, "today")
    tomorrow_data = scrape_day_fast(now_jst + timedelta(days=1), "tomorrow")

    with open("data/today.json", "w", encoding="utf-8") as f:
        json.dump(today_data, f, ensure_ascii=False, indent=2)

    with open("data/tomorrow.json", "w", encoding="utf-8") as f:
        json.dump(tomorrow_data, f, ensure_ascii=False, indent=2)

    print(f"Done: today={today_data['count']}, tomorrow={tomorrow_data['count']}")


if __name__ == "__main__":
    main()

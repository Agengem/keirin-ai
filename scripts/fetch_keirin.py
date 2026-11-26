import json
import os
import re
import urllib.request
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

def fetch_html(url):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
            "Referer": "https://keirin.kdreams.jp/"
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as res:
            raw = res.read()
            for enc in ("utf-8", "euc-jp", "shift_jis"):
                try:
                    return raw.decode(enc)
                except Exception:
                    continue
            return raw.decode("utf-8", errors="ignore")
    except Exception:
        return ""

def parse_players(html):
    players = []
    if not html:
        return players, []

    rows = re.findall(r'<tr[^>]*>(.*?)</tr>', html, re.S)
    for row in rows:
        cells = [
            re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', c)).strip()
            for c in re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', row, re.S)
        ]
        cells = [c for c in cells if c]
        if len(cells) < 3:
            continue

        car = None
        for c in cells[:3]:
            m_car = re.search(r'\b([1-9])\b', c)
            if m_car and len(c) <= 4:
                car = int(m_car.group(1))
                break
        if not car or any(p["car"] == car for p in players):
            continue

        name = ""
        score = 83.0
        style = "両"
        b_cnt = 0

        for idx, c in enumerate(cells):
            if not name and re.search(r'[\u4E00-\u9FFF]{2,}', c):
                if not any(w in c for w in ["級", "班", "県", "府", "都", "道", "競輪", "車番", "選手", "得点", "脚質", "レース", "バンク", "予想"]):
                    cleaned = re.sub(r'[0-9A-Za-z\(\)（）/・\s].*', '', c).strip()
                    if 2 <= len(cleaned) <= 8:
                        name = cleaned
            sc_m = re.search(r'\b([5-9]\d\.\d{1,2}|1[0-2]\d\.\d{1,2})\b', c)
            if sc_m:
                score = float(sc_m.group(1))
            if c in ["逃", "両", "追"]:
                style = c
            if idx >= 3 and re.fullmatch(r'\d{1,2}', c):
                val = int(c)
                if val <= 35 and b_cnt == 0:
                    b_cnt = val

        if name:
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
    if len(players) >= 5:
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

def scrape_kdreams(target_dt, suffix):
    date_str = target_dt.strftime("%Y%m%d")
    disp_date = target_dt.strftime("%Y/%m/%d")
    races = []

    top_url = "https://keirin.kdreams.jp/racecard/"
    top_html = fetch_html(top_url)

    # 1. トップから全開催場・全レースのリンク候補を広く収集
    candidate_pages = set()
    for h in re.findall(r'href=["\']([^"\']+)["\']', top_html):
        if "/racecard/" in h:
            full = urljoin(top_url, h).split("#")[0]
            if re.search(r'/racecard/\d{8,18}', full):
                candidate_pages.add(full)

    # 2. 各開催ページを開き、その日の全レース（1R〜12R）のURLをすべて展開
    race_urls = set()
    for cp in sorted(list(candidate_pages)):
        if date_str in cp and re.search(r'/racecard/\d{14,18}/?$', cp):
            race_urls.add(cp)
        ch = fetch_html(cp)
        for h in re.findall(r'href=["\']([^"\']+)["\']', ch):
            if "/racecard/" in h:
                full_r = urljoin(cp, h).split("#")[0]
                if date_str in full_r and re.search(r'/racecard/\d{12,18}/?$', full_r):
                    race_urls.add(full_r)

    # 3. 見つかったベースIDから1R〜12Rまで確実に補完
    base_prefixes = set()
    for ru in list(race_urls):
        m = re.match(r'(https://keirin\.kdreams\.jp/[a-z]+/racecard/\d{12,14})\d{2}/?$', ru)
        if m:
            base_prefixes.add(m.group(1))
    for bp in base_prefixes:
        for r_no in range(1, 13):
            race_urls.add(f"{bp}{r_no:02d}/")

    seen_keys = set()
    for r_url in sorted(list(race_urls)):
        r_html = fetch_html(r_url)
        if not r_html:
            continue
        title_m = re.search(r'<title>(.*?)</title>', r_html, re.S)
        title = re.sub(r'\s+', ' ', title_m.group(1)) if title_m else ""
        if disp_date not in title and date_str not in r_url:
            continue

        venue_name = next((v for v in VENUES.values() if v in title), None)
        if not venue_name:
            m_code = re.search(r'/racecard/(\d{2})\d{8,}', r_url)
            if m_code:
                venue_name = VENUES.get(m_code.group(1), "競輪")
            else:
                venue_name = "競輪"

        rnum_m = re.search(r'(\d{1,2})R', title) or re.search(r'(\d{2})/?$', r_url)
        race_num = int(rnum_m.group(1)) if rnum_m else 1
        key = f"{venue_name}_{race_num}"
        if key in seen_keys:
            continue

        players, lines = parse_players(r_html)
        if len(players) >= 5:
            seen_keys.add(key)
            races.append({
                "id": f"{suffix}_{venue_name}_{race_num}",
                "date": disp_date,
                "venue": venue_name,
                "raceNum": race_num,
                "title": f"{venue_name} {race_num}R",
                "lines": lines,
                "players": players
            })

    races.sort(key=lambda x: (x["venue"], x["raceNum"]))
    return {
        "date": disp_date,
        "updatedAt": now_jst.strftime("%Y-%m-%d %H:%M:%S JST"),
        "source": "live" if races else "empty",
        "count": len(races),
        "races": races
    }

def main():
    os.makedirs("data", exist_ok=True)
    today_data = scrape_kdreams(now_jst, "today")
    tomorrow_data = scrape_kdreams(now_jst + timedelta(days=1), "tomorrow")

    with open("data/today.json", "w", encoding="utf-8") as f:
        json.dump(today_data, f, ensure_ascii=False, indent=2)

    with open("data/tomorrow.json", "w", encoding="utf-8") as f:
        json.dump(tomorrow_data, f, ensure_ascii=False, indent=2)

    print(f"Done: today={today_data['count']}, tomorrow={tomorrow_data['count']}")

if __name__ == "__main__":
    main()

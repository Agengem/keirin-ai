import json
import os
import re
import urllib.request
from datetime import datetime, timedelta, timezone
from urllib.parse import urljoin

JST = timezone(timedelta(hours=9))
now_jst = datetime.now(JST)

VENUES = {
    "函館": 11, "青森": 12, "いわき平": 13, "弥彦": 21, "前橋": 22,
    "取手": 23, "宇都宮": 24, "大宮": 25, "西武園": 26, "京王閣": 27,
    "立川": 28, "松戸": 31, "千葉": 32, "川崎": 34, "平塚": 35,
    "小田原": 36, "伊東": 37, "静岡": 38, "名古屋": 42, "岐阜": 43,
    "大垣": 44, "豊橋": 45, "富山": 46, "松阪": 47, "四日市": 48,
    "福井": 51, "奈良": 53, "向日町": 54, "和歌山": 55, "岸和田": 56,
    "玉野": 61, "広島": 62, "防府": 63, "高松": 71, "小松島": 73,
    "高知": 74, "松山": 75, "小倉": 81, "久留米": 83, "武雄": 84,
    "佐世保": 85, "別府": 86, "熊本": 87
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

    # 開催場ページ（/venue/racecard/YYYYMMDD.../）をすべて収集
    venue_pages = set()
    for h in re.findall(r'href=["\']([^"\']+)["\']', top_html):
        if "/racecard/" in h:
            full = urljoin(top_url, h).split("#")[0].split("?")[0]
            if re.search(r'/[a-z]+/racecard/\d{8,14}/?$', full):
                venue_pages.add(full)

    # 各開催場ページからその日の全レース（1R〜12R）のURLを収集
    race_urls = set()
    for vp in sorted(list(venue_pages)):
        vh = fetch_html(vp)
        for h in re.findall(r'href=["\']([^"\']+)["\']', vh):
            if "/racecard/" in h:
                full_r = urljoin(vp, h).split("#")[0].split("?")[0]
                if date_str in full_r and re.search(r'/racecard/\d{12,16}/?$', full_r):
                    race_urls.add(full_r)

    for r_url in sorted(list(race_urls))[:80]:
        r_html = fetch_html(r_url)
        title_m = re.search(r'<title>(.*?)</title>', r_html, re.S)
        title = re.sub(r'\s+', ' ', title_m.group(1)) if title_m else ""
        venue_name = next((v for v in VENUES.keys() if v in title), "競輪")
        rnum_m = re.search(r'(\d{1,2})R', title)
        race_num = int(rnum_m.group(1)) if rnum_m else 1
        players, lines = parse_players(r_html)
        if len(players) >= 5:
            races.append({
                "id": f"{suffix}_{venue_name}_{race_num}_{len(races)}",
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

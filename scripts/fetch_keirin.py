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
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
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
    except Exception as e:
        return f"ERR:{e}"


def parse_players_flexible(html):
    players = []
    if not html or html.startswith("ERR:"):
        return players, []

    # 1. trタグベース抽出
    rows = re.findall(r'<tr[^>]*>(.*?)</tr>', html, re.S)
    for row in rows:
        cells = [
            re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', c)).strip()
            for c in re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', row, re.S)
        ]
        cells = [c for c in cells if c]
        if len(cells) < 2:
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
        score = 82.0
        style = "両"
        b_cnt = 0

        for idx, c in enumerate(cells):
            if not name and re.search(r'[\u4E00-\u9FFF]{2,}', c):
                if not any(w in c for w in ["級", "班", "県", "府", "都", "道", "競輪", "車番", "選手", "得点", "脚質", "レース", "バンク"]):
                    cleaned = re.sub(r'[0-9A-Za-z\(\)（）/・\s].*', '', c).strip()
                    if 2 <= len(cleaned) <= 8:
                        name = cleaned
            sc_m = re.search(r'\b(5\d\.\d{1,2}|6\d\.\d{1,2}|7\d\.\d{1,2}|8\d\.\d{1,2}|9\d\.\d{1,2}|1[0-2]\d\.\d{1,2})\b', c)
            if sc_m:
                score = float(sc_m.group(1))
            if c in ["逃", "両", "追"]:
                style = c
            if idx >= 3 and re.fullmatch(r'\d{1,2}', c):
                val = int(c)
                if val <= 30 and b_cnt == 0:
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

    # 2. フォールバック: テキスト全体から「車番 + 漢字氏名」を抽出
    if len(players) < 5:
        players = []
        plain = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', html))
        for m in re.finditer(r'(?:^|\s)([1-9])\s+([\u4E00-\u9FFF]{2,6})(?:\s|[/／(（A-S])', plain):
            car = int(m.group(1))
            name = m.group(2)
            if any(w in name for w in ["競輪", "開催", "決勝", "予選", "特選", "一般", "選抜", "レース"]):
                continue
            if not any(p["car"] == car for p in players):
                players.append({
                    "car": car,
                    "name": name,
                    "score": 82.0,
                    "style": "両",
                    "b": 0,
                    "line": 0,
                    "pos": 1
                })

    players.sort(key=lambda x: x["car"])
    lines = []
    if players:
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


def scrape_day(target_dt):
    date_str = target_dt.strftime("%Y%m%d")
    disp_date = target_dt.strftime("%Y/%m/%d")
    races = []
    debug_log = []

    top_url = "https://keirin.kdreams.jp/racecard/"
    top_html = fetch_html(top_url)

    raw_hrefs = re.findall(r'href=["\']([^"\']+)["\']', top_html)
    venue_urls = set()
    direct_race_urls = set()

    for h in raw_hrefs:
        if "/racecard/" not in h:
            continue
        full = urljoin(top_url, h).split("#")[0]
        if re.search(r'/racecard/\d{6,14}/?$', full):
            if date_str in full or len(re.findall(r'\d{8}', full)) == 0:
                venue_urls.add(full)
        if re.search(r'/r\d{1,2}/?$', full) or (date_str in full and re.search(r'\d{10,14}', full)):
            direct_race_urls.add(full)

    debug_log.append(f"venue_urls:{len(venue_urls)}")

    race_urls = set(direct_race_urls)
    for vu in sorted(list(venue_urls))[:12]:
        vh = fetch_html(vu)
        for h in re.findall(r'href=["\']([^"\']+)["\']', vh):
            if "/racecard/" in h:
                full_r = urljoin(vu, h).split("#")[0]
                if full_r != vu and ("/r" in full_r or re.search(r'\d{10,14}', full_r)):
                    race_urls.add(full_r)

    debug_log.append(f"race_urls:{len(race_urls)}")

    for r_url in sorted(list(race_urls))[:60]:
        r_html = fetch_html(r_url)
        title_m = re.search(r'<title>(.*?)</title>', r_html, re.S)
        title = re.sub(r'\s+', ' ', title_m.group(1)) if title_m else ""
        venue_name = next((v for v in VENUES.values() if v in title or v in r_url), "競輪")
        rnum_m = re.search(r'(\d{1,2})R', title) or re.search(r'/r(\d{1,2})/?$', r_url)
        race_num = int(rnum_m.group(1)) if rnum_m else 1
        players, lines = parse_players_flexible(r_html)
        if len(players) >= 5:
            races.append({
                "id": f"{date_str}_{venue_name}_{race_num}_{len(races)}",
                "date": disp_date,
                "venue": venue_name,
                "raceNum": race_num,
                "title": f"{venue_name} {race_num}R",
                "lines": lines,
                "players": players
            })

    debug_log.append(f"parsed_races:{len(races)}")

    return {
        "date": disp_date,
        "updatedAt": now_jst.strftime("%Y-%m-%d %H:%M:%S JST"),
        "count": len(races),
        "debug": debug_log,
        "races": races
    }


def main():
    os.makedirs("data", exist_ok=True)
    today_data = scrape_day(now_jst)
    tomorrow_data = scrape_day(now_jst + timedelta(days=1))

    with open("data/today.json", "w", encoding="utf-8") as f:
        json.dump(today_data, f, ensure_ascii=False, indent=2)

    with open("data/tomorrow.json", "w", encoding="utf-8") as f:
        json.dump(tomorrow_data, f, ensure_ascii=False, indent=2)

    print(f"Done: today={today_data['count']}, tomorrow={tomorrow_data['count']}, debug={today_data['debug']}")


if __name__ == "__main__":
    main()

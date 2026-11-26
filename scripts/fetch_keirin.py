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
    "11": ("函館", "hakodate"), "12": ("青森", "aomori"), "13": ("いわき平", "iwakitaira"),
    "21": ("弥彦", "yahiko"), "22": ("前橋", "maebashi"), "23": ("取手", "toride"),
    "24": ("宇都宮", "utsunomiya"), "25": ("大宮", "omiya"), "26": ("西武園", "seibuen"),
    "27": ("京王閣", "keiokaku"), "28": ("立川", "tachikawa"), "31": ("松戸", "matsudo"),
    "32": ("千葉", "chiba"), "34": ("川崎", "kawasaki"), "35": ("平塚", "hiratsuka"),
    "36": ("小田原", "odawara"), "37": ("伊東", "ito"), "38": ("静岡", "shizuoka"),
    "42": ("名古屋", "nagoya"), "43": ("岐阜", "gifu"), "44": ("大垣", "ogaki"),
    "45": ("豊橋", "toyohashi"), "46": ("富山", "toyama"), "47": ("松阪", "matsusaka"),
    "48": ("四日市", "yokkaichi"), "51": ("福井", "fukui"), "53": ("奈良", "nara"),
    "54": ("向日町", "mukomachi"), "55": ("和歌山", "wakayama"), "56": ("岸和田", "kishiwada"),
    "61": ("玉野", "tamano"), "62": ("広島", "hiroshima"), "63": ("防府", "hofu"),
    "71": ("高松", "takamatsu"), "73": ("小松島", "komatsushima"), "74": ("高知", "kochi"),
    "75": ("松山", "matsuyama"), "81": ("小倉", "kokura"), "83": ("久留米", "kurume"),
    "84": ("武雄", "takeo"), "85": ("佐世保", "sasebo"), "86": ("別府", "beppu"),
    "87": ("熊本", "kumamoto")
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
        score = None
        style = "両"
        b_cnt = 0

        row_joined = " ".join(cells)
        sc_all = re.findall(r'\b([6-9]\d\.\d{2}|1[0-2]\d\.\d{2})\b', row_joined)
        if sc_all:
            score = float(sc_all[0])

        for idx, c in enumerate(cells):
            if not name and re.search(r'[\u4E00-\u9FFF]{2,}', c):
                if not any(w in c for w in ["級", "班", "県", "府", "都", "道", "競輪", "車番", "選手", "得点", "脚質", "レース", "バンク", "予想", "平均"]):
                    cleaned = re.sub(r'[0-9A-Za-z\(\)（）/・\s].*', '', c).strip()
                    if 2 <= len(cleaned) <= 8:
                        name = cleaned
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
                "score": score if score is not None else round(82.0 + (9 - car) * 0.4, 2),
                "style": style,
                "b": b_cnt,
                "line": 0,
                "pos": 1
            })

    players.sort(key=lambda x: x["car"])
    lines = []
    if len(players) >= 5:
        # ページ内のライン予想テキスト（例: 147 25 36 や ← 1 4 7）を優先抽出
        line_sec = re.search(r'(?:並び予想|ライン予想|周回予想).*?(<div[^>]*>.*?</div>|<table[^>]*>.*?</table>|<ul[^>]*>.*?</ul>)', html, re.S)
        if line_sec:
            txt = re.sub(r'<[^>]+>', ' ', line_sec.group(1))
            for grp_str in re.findall(r'(?:[1-9]\s*){2,5}', txt):
                nums = [int(d) for d in re.findall(r'[1-9]', grp_str)]
                if len(nums) >= 2 and len(set(nums)) == len(nums):
                    if not any(n in sum(lines, []) for n in nums):
                        lines.append(nums)

        if not lines:
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

def discover_all_race_urls(target_dt):
    date_str = target_dt.strftime("%Y%m%d")
    race_urls = set()
    venue_pages = set()

    # 1. トップページと開催日程ページから全開催場リンクを収集
    for entry in [
        "https://keirin.kdreams.jp/racecard/",
        f"https://keirin.kdreams.jp/schedule/{target_dt.strftime('%Y/%m')}/"
    ]:
        html = fetch_html(entry)
        for h in re.findall(r'href=["\']([^"\']+)["\']', html):
            if "/racecard/" in h:
                full = urljoin(entry, h).split("#")[0].split("?")[0]
                if re.search(r'/racecard/\d{8,18}/?$', full):
                    venue_pages.add(full)

    # 2. 各開催ページを開き、その中のリンクをすべて展開
    def scan_page(url):
        h = fetch_html(url)
        found = set()
        for lk in re.findall(r'href=["\']([^"\']+)["\']', h):
            if "/racecard/" in lk:
                full = urljoin(url, lk).split("#")[0].split("?")[0]
                if re.search(r'/racecard/\d{10,18}/?$', full):
                    found.add(full)
        return found

    with ThreadPoolExecutor(max_workers=10) as ex:
        for res in ex.map(scan_page, list(venue_pages)):
            for u in res:
                if date_str in u:
                    race_urls.add(u)
                else:
                    venue_pages.add(u)

    # 3. 見つかった全開催プレフィックスから 01R〜12R を完全展開
    prefixes = set()
    for u in list(race_urls) + list(venue_pages):
        m = re.match(r'(https://keirin\.kdreams\.jp/[a-z]+/racecard/\d{12,14})\d{2}/?$', u)
        if m:
            prefixes.add(m.group(1))
        m2 = re.match(r'(https://keirin\.kdreams\.jp/[a-z]+/racecard/\d{12,14})/?$', u)
        if m2:
            prefixes.add(m2.group(1))

    # 初日開催（YYYYMMDD01）のプレフィックスも補完
    for code, slug in VENUES.items():
        prefixes.add(f"https://keirin.kdreams.jp/{slug}/racecard/{code}{date_str}01")

    for p in prefixes:
        for r_no in range(1, 13):
            race_urls.add(f"{p}{r_no:02d}/")

    return sorted(list(race_urls))

def scrape_day(target_dt, suffix):
    date_str = target_dt.strftime("%Y%m%d")
    disp_date = target_dt.strftime("%Y/%m/%d")
    candidate_urls = discover_all_race_urls(target_dt)

    races = []
    seen_keys = set()

    def fetch_and_parse(r_url):
        r_html = fetch_html(r_url)
        if not r_html or "出走表" not in r_html:
            return None
        title_m = re.search(r'<title>(.*?)</title>', r_html, re.S)
        title = re.sub(r'\s+', ' ', title_m.group(1)) if title_m else ""
        if disp_date not in title and f"{target_dt.month}月{target_dt.day}日" not in title:
            return None

        venue_name = next((v[0] for v in VENUES.values() if v[0] in title), None)
        if not venue_name:
            m_code = re.search(r'/racecard/(\d{2})\d{8,}', r_url)
            venue_name = VENUES[m_code.group(1)][0] if (m_code and m_code.group(1) in VENUES) else "競輪"

        rnum_m = re.search(r'(\d{1,2})R', title) or re.search(r'(\d{2})/?$', r_url)
        race_num = int(rnum_m.group(1)) if rnum_m else 1
        players, lines = parse_players(r_html)
        if len(players) < 5:
            return None
        return {
            "venue": venue_name,
            "raceNum": race_num,
            "title": f"{venue_name} {race_num}R",
            "lines": lines,
            "players": players
        }

    with ThreadPoolExecutor(max_workers=12) as ex:
        futures = [ex.submit(fetch_and_parse, u) for u in candidate_urls]
        for fut in as_completed(futures):
            item = fut.result()
            if not item:
                continue
            key = f"{item['venue']}_{item['raceNum']}"
            if key in seen_keys:
                continue
            seen_keys.add(key)
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
        "races": races
    }

def main():
    os.makedirs("data", exist_ok=True)
    today_data = scrape_day(now_jst, "today")
    tomorrow_data = scrape_day(now_jst + timedelta(days=1), "tomorrow")

    with open("data/today.json", "w", encoding="utf-8") as f:
        json.dump(today_data, f, ensure_ascii=False, indent=2)

    with open("data/tomorrow.json", "w", encoding="utf-8") as f:
        json.dump(tomorrow_data, f, ensure_ascii=False, indent=2)

    print(f"Done: today={today_data['count']}, tomorrow={tomorrow_data['count']}")

if __name__ == "__main__":
    main()

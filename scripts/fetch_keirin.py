import json
import os
import re
import urllib.request
from datetime import datetime, timedelta, timezone

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
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept-Language": "ja,en-US;q=0.9,en;q=0.8"
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as res:
            raw = res.read()
            for enc in ("utf-8", "euc-jp", "shift_jis"):
                try:
                    return raw.decode(enc)
                except Exception:
                    continue
            return raw.decode("utf-8", errors="ignore")
    except Exception:
        return ""


def extract_lines_and_players(html):
    players = []
    if not html:
        return players, []

    lines = []
    line_blocks = re.findall(r'(?:並び予想|ライン予想|周回予想).*?</div>', html, re.S)
    for blk in line_blocks:
        clean_blk = re.sub(r'<[^>]+>', ' ', blk)
        groups = re.findall(r'(?:[1-9]\s*){2,5}', clean_blk)
        for g in groups:
            nums = [int(x) for x in re.findall(r'[1-9]', g)]
            if len(nums) >= 2 and len(set(nums)) == len(nums):
                lines.append(nums)
        if lines:
            break

    rows = re.findall(r'<tr[^>]*>(.*?)</tr>', html, re.S)
    for row in rows:
        cells = [re.sub(r'<[^>]+>', ' ', c) for c in re.findall(r'<td[^>]*>(.*?)</td>', row, re.S)]
        cells = [re.sub(r'\s+', ' ', c).strip() for c in cells if c.strip()]
        if len(cells) < 4:
            continue

        car = None
        for c in cells[:3]:
            if re.fullmatch(r'[1-9]', c):
                car = int(c)
                break
        if not car or any(p["car"] == car for p in players):
            continue

        name = ""
        score = 80.0
        style = "両"
        b_cnt = 0

        for idx, c in enumerate(cells):
            if not name and re.search(r'[\u4E00-\u9FFF]{2,}', c) and not any(w in c for w in ["級", "班", "県", "府", "都", "道", "競輪", "逃", "捲", "差", "マ"]):
                cleaned = re.sub(r'[0-9A-Za-z\(\)（）/・].*', '', c).strip()
                if 2 <= len(cleaned) <= 8:
                    name = cleaned
            sc_m = re.search(r'\b(6\d\.\d{2}|7\d\.\d{2}|8\d\.\d{2}|9\d\.\d{2}|1[0-2]\d\.\d{2})\b', c)
            if sc_m:
                score = float(sc_m.group(1))
            if c in ["逃", "両", "追"]:
                style = c
            if idx >= 5 and re.fullmatch(r'\d{1,2}', c):
                val = int(c)
                if val <= 30 and b_cnt == 0:
                    b_cnt = val

        if name:
            line_id = 0
            line_pos = 1
            for l_idx, grp in enumerate(lines):
                if car in grp:
                    line_id = l_idx + 1
                    line_pos = grp.index(car) + 1
                    break
            players.append({
                "car": car,
                "name": name,
                "score": score,
                "style": style,
                "b": b_cnt,
                "line": line_id,
                "pos": line_pos
            })

    players.sort(key=lambda x: x["car"])
    if not lines and players:
        fronts = [p for p in players if p["style"] == "逃" or p["b"] >= 3]
        backs = [p for p in players if p not in fronts]
        backs.sort(key=lambda x: x["score"], reverse=True)
        auto_lines = []
        for idx, f in enumerate(fronts[:3]):
            grp = [f["car"]]
            if idx < len(backs):
                grp.append(backs[idx]["car"])
            auto_lines.append(grp)
        lines = auto_lines
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

    nk_html = fetch_html(f"https://keirin.netkeiba.com/race/list.html?kaisai_date={date_str}")
    nk_ids = sorted(list(set(re.findall(r'race_id=(\d{12})', nk_html))))

    for rid in nk_ids[:60]:
        v_code = rid[4:6]
        venue_name = VENUES.get(v_code, "競輪")
        race_num = int(rid[10:12])
        r_html = fetch_html(f"https://keirin.netkeiba.com/race/entry.html?race_id={rid}")
        players, lines = extract_lines_and_players(r_html)
        if len(players) >= 5:
            races.append({
                "id": rid,
                "date": disp_date,
                "venue": venue_name,
                "raceNum": race_num,
                "title": f"{venue_name} {race_num}R",
                "lines": lines,
                "players": players
            })

    if not races:
        top_html = fetch_html("https://keirin.kdreams.jp/racecard/")
        v_links = set(re.findall(r'href="((?:https://keirin\.kdreams\.jp)?/[a-z]+/racecard/\d+/)"', top_html))
        race_urls = set()
        for vl in v_links:
            full_vl = vl if vl.startswith("http") else "https://keirin.kdreams.jp" + vl
            if date_str in full_vl:
                vh = fetch_html(full_vl)
                for m in re.findall(r'href="((?:https://keirin\.kdreams\.jp)?/[a-z]+/racecard/' + date_str + r'\d{4,6}/)"', vh):
                    race_urls.add(m if m.startswith("http") else "https://keirin.kdreams.jp" + m)
        for r_url in sorted(list(race_urls))[:60]:
            r_html = fetch_html(r_url)
            title_m = re.search(r'<title>(.*?)</title>', r_html, re.S)
            title = title_m.group(1) if title_m else ""
            venue_name = next((v for v in VENUES.values() if v in title), "競輪")
            rnum_m = re.search(r'(\d{1,2})R', title)
            race_num = int(rnum_m.group(1)) if rnum_m else 1
            players, lines = extract_lines_and_players(r_html)
            if len(players) >= 5:
                races.append({
                    "id": f"{date_str}_{venue_name}_{race_num}",
                    "date": disp_date,
                    "venue": venue_name,
                    "raceNum": race_num,
                    "title": f"{venue_name} {race_num}R",
                    "lines": lines,
                    "players": players
                })

    return {
        "date": disp_date,
        "updatedAt": now_jst.strftime("%Y-%m-%d %H:%M:%S JST"),
        "count": len(races),
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

    print(f"Done: today={today_data['count']}, tomorrow={tomorrow_data['count']}")


if __name__ == "__main__":
    main()

import json
import os
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import urljoin
from playwright.sync_api import sync_playwright

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


def parse_players_from_page(page):
    rows = page.evaluate("""() => {
        return Array.from(document.querySelectorAll('tr')).map(tr =>
            Array.from(tr.querySelectorAll('td, th')).map(el => el.innerText.replace(/\\s+/g, ' ').trim())
        );
    }""")
    players = []
    for cells in rows:
        cells = [c for c in cells if c]
        if len(cells) < 3:
            continue
        car = None
        for c in cells[:3]:
            if re.fullmatch(r'[1-9]', c):
                car = int(c)
                break
        if not car or any(p["car"] == car for p in players):
            continue

        joined = " ".join(cells)
        sc_m = re.search(r'\b([6-9]\d\.\d{2}|1[0-2]\d\.\d{2})\b', joined)
        score = float(sc_m.group(1)) if sc_m else round(82.0 + (9 - car) * 0.4, 2)
        style = next((c for c in cells if c in ["逃", "両", "追"]), "両")
        b_cnt = 0
        for c in cells[3:]:
            if re.fullmatch(r'\d{1,2}', c) and int(c) <= 35:
                b_cnt = int(c)
                break

        name = ""
        for c in cells:
            if re.search(r'[\u4E00-\u9FFF]{2,}', c):
                if not any(w in c for w in ["級", "班", "県", "府", "都", "道", "競輪", "車番", "選手", "得点", "脚質", "レース", "バンク", "予想", "平均"]):
                    cleaned = re.sub(r'[0-9A-Za-z\(\)（）/・\s].*', '', c).strip()
                    if 2 <= len(cleaned) <= 8:
                        name = cleaned
                        break
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


def collect_race_urls(page, target_dt):
    date_str = target_dt.strftime("%Y%m%d")
    race_urls = set()
    seeds = [
        f"https://keirin.jp/pc/top?date={date_str}",
        "https://keirin.kdreams.jp/racecard/",
        f"https://keirin.kdreams.jp/schedule/{target_dt.strftime('%Y/%m')}/"
    ]

    for seed in seeds:
        try:
            page.goto(seed, timeout=25000, wait_until="domcontentloaded")
            page.wait_for_timeout(1500)
            hrefs = page.evaluate("""() => Array.from(document.querySelectorAll('a')).map(a => a.href)""")
            for h in hrefs:
                clean = h.split("#")[0]
                if "keirin.jp" in clean and ("syutsuba" in clean or "race" in clean) and date_str in clean:
                    race_urls.add(clean)
                elif "/racecard/" in clean and re.search(r'/racecard/\d{8,18}/?$', clean.split("?")[0]):
                    base = clean.split("?")[0]
                    if date_str in base:
                        race_urls.add(base)
                    else:
                        try:
                            page.goto(base, timeout=20000, wait_until="domcontentloaded")
                            page.wait_for_timeout(700)
                            sub = page.evaluate("""() => Array.from(document.querySelectorAll('a')).map(a => a.href)""")
                            for sh in sub:
                                sc = sh.split("#")[0]
                                if "/racecard/" in sc and date_str in sc:
                                    race_urls.add(sc)
                        except Exception:
                            pass
        except Exception:
            continue

    return sorted(list(race_urls))


def scrape_day(browser, target_dt, suffix):
    disp_date = target_dt.strftime("%Y/%m/%d")
    page = browser.new_page()
    races = []
    seen = set()

    try:
        urls = collect_race_urls(page, target_dt)
        for ru in urls[:120]:
            try:
                page.goto(ru, timeout=20000, wait_until="domcontentloaded")
                page.wait_for_timeout(600)
                title = page.title()
                venue_name = next((v for v in VENUES.values() if v in title), None)
                if not venue_name:
                    m_code = re.search(r'(?:jorncd=|/racecard/)(\d{2})', ru)
                    if m_code and m_code.group(1) in VENUES:
                        venue_name = VENUES[m_code.group(1)]
                    else:
                        venue_name = "競輪"

                rnum_m = re.search(r'(\d{1,2})R', title) or re.search(r'(?:raceno=|r)(\d{1,2})', ru, re.I)
                race_num = int(rnum_m.group(1)) if rnum_m else 0
                if not (1 <= race_num <= 12):
                    continue

                key = f"{venue_name}_{race_num}"
                if key in seen:
                    continue

                players, lines = parse_players_from_page(page)
                if len(players) >= 5:
                    seen.add(key)
                    races.append({
                        "id": f"{suffix}_{venue_name}_{race_num}",
                        "date": disp_date,
                        "venue": venue_name,
                        "raceNum": race_num,
                        "title": f"{venue_name} {race_num}R",
                        "lines": lines,
                        "players": players
                    })
            except Exception:
                continue
    finally:
        page.close()

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
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        today_data = scrape_day(browser, now_jst, "today")
        tomorrow_data = scrape_day(browser, now_jst + timedelta(days=1), "tomorrow")
        browser.close()

    with open("data/today.json", "w", encoding="utf-8") as f:
        json.dump(today_data, f, ensure_ascii=False, indent=2)

    with open("data/tomorrow.json", "w", encoding="utf-8") as f:
        json.dump(tomorrow_data, f, ensure_ascii=False, indent=2)

    print(f"Done: today={today_data['count']}, tomorrow={tomorrow_data['count']}")


if __name__ == "__main__":
    main()

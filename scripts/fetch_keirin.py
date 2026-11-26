import json
import os
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import urljoin
from playwright.sync_api import sync_playwright

JST = timezone(timedelta(hours=9))
now_jst = datetime.now(JST)

VENUES = [
    "函館", "青森", "いわき平", "弥彦", "前橋", "取手", "宇都宮", "大宮", "西武園",
    "京王閣", "立川", "松戸", "千葉", "川崎", "平塚", "小田原", "伊東", "静岡",
    "名古屋", "岐阜", "大垣", "豊橋", "富山", "松阪", "四日市", "福井", "奈良",
    "向日町", "和歌山", "岸和田", "玉野", "広島", "防府", "高松", "小松島",
    "高知", "松山", "小倉", "久留米", "武雄", "佐世保", "別府", "熊本"
]


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


def scrape_with_browser(browser, target_dt, suffix):
    date_str = target_dt.strftime("%Y%m%d")
    disp_date = target_dt.strftime("%Y/%m/%d")
    page = browser.new_page()
    races = []
    seen = set()

    try:
        page.goto("https://keirin.kdreams.jp/racecard/", timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(1500)

        hrefs = page.evaluate("""() => Array.from(document.querySelectorAll('a')).map(a => a.href)""")
        venue_urls = sorted(list({
            u.split("#")[0].split("?")[0]
            for u in hrefs
            if "/racecard/" in u and re.search(r'/[a-z]+/racecard/\d{8,18}/?$', u.split("#")[0].split("?")[0])
        }))

        race_urls = set()
        for vu in venue_urls:
            try:
                page.goto(vu, timeout=20000, wait_until="domcontentloaded")
                page.wait_for_timeout(800)
                sub_hrefs = page.evaluate("""() => Array.from(document.querySelectorAll('a')).map(a => a.href)""")
                for su in sub_hrefs:
                    clean = su.split("#")[0].split("?")[0]
                    if "/racecard/" in clean and date_str in clean and re.search(r'/racecard/\d{12,18}/?$', clean):
                        race_urls.add(clean)
            except Exception:
                continue

        for ru in sorted(list(race_urls)):
            try:
                page.goto(ru, timeout=20000, wait_until="domcontentloaded")
                page.wait_for_timeout(600)
                title = page.title()
                venue_name = next((v for v in VENUES if v in title), "競輪")
                rnum_m = re.search(r'(\d{1,2})R', title)
                race_num = int(rnum_m.group(1)) if rnum_m else 0
                if race_num == 0:
                    m_end = re.search(r'(\d{2})/?$', ru)
                    if m_end and 1 <= int(m_end.group(1)) <= 12:
                        race_num = int(m_end.group(1))
                if race_num == 0:
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
        today_data = scrape_with_browser(browser, now_jst, "today")
        tomorrow_data = scrape_with_browser(browser, now_jst + timedelta(days=1), "tomorrow")
        browser.close()

    with open("data/today.json", "w", encoding="utf-8") as f:
        json.dump(today_data, f, ensure_ascii=False, indent=2)

    with open("data/tomorrow.json", "w", encoding="utf-8") as f:
        json.dump(tomorrow_data, f, ensure_ascii=False, indent=2)

    print(f"Done: today={today_data['count']}, tomorrow={tomorrow_data['count']}")


if __name__ == "__main__":
    main()

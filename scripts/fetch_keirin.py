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
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15"
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=12) as res:
            return res.read().decode("utf-8", errors="ignore")
    except Exception:
        return ""

def scrape_day(target_dt):
    date_str = target_dt.strftime("%Y%m%d")
    disp_date = target_dt.strftime("%Y/%m/%d")
    url = f"https://keirin.kdreams.jp/racecard/{target_dt.strftime('%Y/%m/%d')}/"
    html = fetch_html(url)

    races = []
    # 開催場とレースリンクを抽出
    links = re.findall(r'href="(/[a-z]+/racecard/' + date_str + r'\d{6}/)"', html)
    unique_links = sorted(list(set(links)))

    for path in unique_links[:60]:  # 最大60レース取得
        race_url = "https://keirin.kdreams.jp" + path
        r_html = fetch_html(race_url)
        if not r_html:
            continue

        title_m = re.search(r'<title>(.*?)</title>', r_html, re.S)
        title = title_m.group(1).strip() if title_m else ""
        venue_name = "競輪"
        for v in VENUES.values():
            if v in title:
                venue_name = v
                break

        rnum_m = re.search(r'(\d{1,2})R', title)
        race_num = int(rnum_m.group(1)) if rnum_m else 1

        # 選手テーブル抽出
        rows = re.findall(r'<tr[^>]*>(.*?)</tr>', r_html, re.S)
        players = []
        for row in rows:
            cells = [re.sub(r'<[^>]+>', '', c).strip() for c in re.findall(r'<td[^>]*>(.*?)</td>', row, re.S)]
            cells = [re.sub(r'\s+', ' ', c) for c in cells if c]
            if len(cells) >= 5:
                car_m = re.match(r'^([1-9])$', cells[0])
                if not car_m and len(cells) > 1:
                    car_m = re.match(r'^([1-9])$', cells[1])
                if car_m:
                    car = int(car_m.group(1))
                    if any(p["car"] == car for p in players):
                        continue
                    name = ""
                    score = 80.0
                    style = "両"
                    b_cnt = 0
                    for c in cells:
                        if re.search(r'[\u4E00-\u9FFF]{2,}', c) and not name and "級" not in c and "班" not in c:
                            name = re.sub(r'[0-9A-Za-z\(\)（）/].*', '', c).strip()
                        sc_m = re.search(r'\b(6\d\.\d{2}|7\d\.\d{2}|8\d\.\d{2}|9\d\.\d{2}|1[0-2]\d\.\d{2})\b', c)
                        if sc_m:
                            score = float(sc_m.group(1))
                        if c in ["逃", "両", "追"]:
                            style = c
                    if name:
                        players.append({
                            "car": car,
                            "name": name,
                            "score": score,
                            "style": style,
                            "b": b_cnt,
                            "line": (car - 1) // 3 + 1,
                            "pos": (car - 1) % 3 + 1
                        })

        if len(players) >= 5:
            players.sort(key=lambda x: x["car"])
            races.append({
                "id": f"{date_str}_{venue_name}_{race_num}",
                "date": disp_date,
                "venue": venue_name,
                "raceNum": race_num,
                "title": f"{venue_name} {race_num}R",
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

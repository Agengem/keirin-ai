import json
import re
from datetime import datetime, timezone, timedelta
import requests
from bs4 import BeautifulSoup

JST = timezone(timedelta(hours=9))
now = datetime.now(JST)
today_str = now.strftime("%Y%m%d")
display_date = now.strftime("%Y年%m月%d日(%a)")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
}

VENUES_MASTER = {
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

def fetch_kdreams_today():
    """楽天Kドリームスの開催一覧・結果ページから本日の全開催場・全レース状態を取得"""
    url = f"https://keirin.kdreams.jp/racecard/{now.strftime('%Y/%m/%d')}/"
    res = requests.get(url, headers=HEADERS, timeout=15)
    res.encoding = res.apparent_encoding
    soup = BeautifulSoup(res.text, "lxml")

    venues = []
    # 開催場リンクの抽出
    seen_codes = set()
    for a in soup.find_all("a", href=True):
        m = re.search(r"/([a-z]+)/racecard/(\d{2})" + today_str, a["href"])
        if m:
            slug, code = m.group(1), m.group(2)
            if code in seen_codes:
                continue
            seen_codes.add(code)
            name = VENUES_MASTER.get(code, a.get_text(strip=True) or code)
            venues.append({
                "code": code,
                "slug": slug,
                "name": name,
                "races": fetch_venue_races(slug, code)
            })
    return venues

def fetch_venue_races(slug, code):
    """各開催場の1R〜12Rの一覧と確定結果を取得"""
    races = []
    list_url = f"https://keirin.kdreams.jp/{slug}/racecard/{code}{today_str}/"
    try:
        r = requests.get(list_url, headers=HEADERS, timeout=15)
        r.encoding = r.apparent_encoding
        soup = BeautifulSoup(r.text, "lxml")

        for r_num in range(1, 13):
            r_str = f"{r_num:02d}"
            race_id = f"{code}{today_str}{r_str}"
            status = "発売中"
            result_3tan = ""
            payout = ""
            start_time = ""

            # 該当レース行のテキスト探索
            row_link = soup.find("a", href=re.compile(race_id))
            if row_link:
                tr = row_link.find_parent("tr")
                if tr:
                    txt = tr.get_text(" ", strip=True)
                    t_m = re.search(r"(\d{1,2}:\d{2})", txt)
                    if t_m:
                        start_time = t_m.group(1)
                    # 3連単結果パターン (例: 1-7-5 1,230円)
                    res_m = re.search(r"([1-9]-[1-9]-[1-9])\s*([\d,]+円)", txt)
                    if res_m:
                        status = "確定済"
                        result_3tan = res_m.group(1)
                        payout = res_m.group(2)

            races.append({
                "r": r_num,
                "race_id": race_id,
                "start_time": start_time,
                "status": status,
                "result_3tan": result_3tan,
                "payout": payout
            })
    except Exception as e:
        print(f"Error fetching {slug}: {e}")
    return races

def main():
    output = {
        "updated_at": now.strftime("%Y-%m-%d %H:%M:%S JST"),
        "display_date": display_date,
        "status": "ok",
        "venues": []
    }
    try:
        venues = fetch_kdreams_today()
        output["venues"] = venues
        if not venues:
            output["status"] = "no_venues_found"
    except Exception as e:
        output["status"] = f"error: {str(e)}"

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(output['venues'])} venues at {output['updated_at']}")

if __name__ == "__main__":
    main()

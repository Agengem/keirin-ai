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
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/129.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
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
    "85": "佐世保", "86": "別府", "87": "熊本",
}


def fetch_html(url: str) -> str:
    r = requests.get(url, headers=HEADERS, timeout=15)
    r.raise_for_status()
    r.encoding = r.apparent_encoding or "utf-8"
    return r.text


def get_venues_today() -> list:
    """開催一覧ページ（＋必要なら結果一覧ページ）から本日の開催場を抽出"""
    urls = [
        f"https://keirin.kdreams.jp/racecard/{now.strftime('%Y/%m/%d')}/",
        f"https://keirin.kdreams.jp/result/{now.strftime('%Y/%m/%d')}/",
    ]
    venues_map = {}

    for u in urls:
        try:
            html = fetch_html(u)
            soup = BeautifulSoup(html, "lxml")
            for a in soup.find_all("a", href=True):
                m = re.search(r"/([a-z]+)/(?:racecard|result)/(\d{2})" + today_str, a["href"])
                if m:
                    slug, code = m.group(1), m.group(2)
                    if code not in venues_map:
                        name = VENUES_MASTER.get(code)
                        if not name:
                            txt = a.get_text(" ", strip=True)
                            name = re.sub(r"(競輪|モーニング|ナイター|ミッドナイト|\s+).*", "", txt) or code
                        venues_map[code] = {
                            "code": code,
                            "slug": slug,
                            "name": name,
                            "races": [],
                        }
        except Exception as e:
            print(f"Venue list fetch warning ({u}): {e}")

    return list(venues_map.values())


def parse_result_from_soup(soup: BeautifulSoup):
    """結果ページや行テキストから3連単と払戻金を抽出"""
    text = soup.get_text(" ", strip=True)
    # 3連単パターン（例: 1-7-5 1,420円）
    m3 = re.search(r"3連単[^0-9]*([1-9])\s*[-－=]\s*([1-9])\s*[-－=]\s*([1-9])\s*([0-9,]+)\s*円", text)
    if m3:
        combo = f"{m3.group(1)}-{m3.group(2)}-{m3.group(3)}"
        payout = f"{m3.group(4)}円"
        return combo, payout

    m3_alt = re.search(r"\b([1-9]-[1-9]-[1-9])\b\s*([0-9,]+)\s*円", text)
    if m3_alt:
        return m3_alt.group(1), f"{m3_alt.group(2)}円"

    return "", ""


def parse_players_from_soup(soup: BeautifulSoup) -> list:
    """出走表ページから車番・選手名・得点/脚質を可能な範囲で抽出"""
    players = []
    for tr in soup.find_all("tr"):
        cells = [c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"]) if c.get_text(" ", strip=True)]
        if len(cells) < 2:
            continue
        # 先頭または2列目に1〜9の車番がある行を探す
        car_num = None
        for idx in (0, 1):
            if idx < len(cells) and re.fullmatch(r"[1-9]", cells[idx]):
                car_num = int(cells[idx])
                break
        if car_num is None or any(p["car"] == car_num for p in players):
            continue

        row_str = " ".join(cells)
        name_match = re.search(r"([一-龠々ぁ-んァ-ヶ・]{2,12})", " ".join(cells[1:4]))
        name = name_match.group(1) if name_match else f"{car_num}番車"

        score_match = re.search(r"\b(\d{2,3}\.\d{2})\b", row_str)
        score = float(score_match.group(1)) if score_match else 80.0

        style = "追"
        if "逃" in row_str:
            style = "逃"
        elif "両" in row_str:
            style = "両"

        players.append({
            "car": car_num,
            "name": name,
            "score": score,
            "style": style,
        })

    players.sort(key=lambda x: x["car"])
    return players[:9]


def fetch_venue_races(slug: str, code: str) -> list:
    """各場の1R〜12Rについて発走時刻・確定結果・出走表を取得"""
    races = []
    list_url = f"https://keirin.kdreams.jp/{slug}/racecard/{code}{today_str}/"
    list_soup = None
    try:
        list_soup = BeautifulSoup(fetch_html(list_url), "lxml")
    except Exception as e:
        print(f"Racecard list error ({slug}): {e}")

    for r_num in range(1, 13):
        r_str = f"{r_num:02d}"
        race_id = f"{code}{today_str}{r_str}"
        start_time = ""
        status = "発売中"
        result_3tan = ""
        payout = ""
        players = []

        # 一覧から発走時刻や確定情報を拾う
        if list_soup:
            link = list_soup.find("a", href=re.compile(race_id))
            if link:
                container = link.find_parent(["tr", "li", "div"])
                if container:
                    ctxt = container.get_text(" ", strip=True)
                    tm = re.search(r"\b([012]?\d:\d{2})\b", ctxt)
                    if tm:
                        start_time = tm.group(1)

        # 結果ページを確認（確定していれば3連単と払戻を取得）
        res_url = f"https://keirin.kdreams.jp/{slug}/result/{race_id}/"
        try:
            res_soup = BeautifulSoup(fetch_html(res_url), "lxml")
            combo, pay = parse_result_from_soup(res_soup)
            if combo:
                status = "確定済"
                result_3tan = combo
                payout = pay
        except Exception:
            pass

        # 出走表ページから選手情報を取得
        rc_url = f"https://keirin.kdreams.jp/{slug}/racecard/{race_id}/"
        try:
            rc_soup = BeautifulSoup(fetch_html(rc_url), "lxml")
            if not start_time:
                tm = re.search(r"発走[^\d]*([012]?\d:\d{2})", rc_soup.get_text(" ", strip=True))
                if tm:
                    start_time = tm.group(1)
            players = parse_players_from_soup(rc_soup)
        except Exception:
            pass

        races.append({
            "r": r_num,
            "race_id": race_id,
            "start_time": start_time,
            "status": status,
            "result_3tan": result_3tan,
            "payout": payout,
            "players": players,
        })

    return races


def main():
    output = {
        "updated_at": now.strftime("%Y-%m-%d %H:%M:%S JST"),
        "display_date": display_date,
        "status": "ok",
        "venues": [],
    }
    try:
        venues = get_venues_today()
        for v in venues:
            v["races"] = fetch_venue_races(v["slug"], v["code"])
        output["venues"] = venues
        if not venues:
            output["status"] = "no_venues_found"
    except Exception as e:
        output["status"] = f"error: {e}"

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"Done: {len(output['venues'])} venues at {output['updated_at']}")


if __name__ == "__main__":
    main()

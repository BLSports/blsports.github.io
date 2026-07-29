#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Premium-Datenquellen (aktivieren sich automatisch, wenn Keys gesetzt sind):

- MatchStat Tennis API (RapidAPI): tiefe Rankings, vollstaendige Spielplaene
  inkl. Challenger, Belag & Runde.
- API-Football: Verletzte, Tabellen, Torschuetzen, Buchmacher-Quoten.

Keys (Repo-Secrets -> Workflow-Env):
  RAPIDAPI_KEY      ein Key fuer beide Dienste (RapidAPI-Abos), ODER
  TENNIS_API_KEY    nur Tennis via RapidAPI
  FOOTBALL_API_KEY  API-Football-Direktkunde (x-apisports-key)
"""

import json
import os
import sys
import time
from urllib.request import Request, urlopen

RAPID_KEY = (os.environ.get("RAPIDAPI_KEY") or os.environ.get("TENNIS_API_KEY") or "").strip()
FOOT_DIRECT_KEY = (os.environ.get("FOOTBALL_API_KEY") or "").strip()
TENNIS_HOST = "tennis-api-atp-wta-itf.p.rapidapi.com"
FOOT_RAPID_HOST = "api-football-v1.p.rapidapi.com"

TENNIS_ENABLED = bool(RAPID_KEY)
FOOT_ENABLED = bool(FOOT_DIRECT_KEY or os.environ.get("RAPIDAPI_KEY"))

# API-Football Liga-IDs (beim ersten Live-Lauf per /leagues gegenpruefbar)
FOOT_IDS = {
    "us1": 253, "br1": 71, "no1": 103, "se1": 113, "dk1": 119, "ie1": 357,
    "bl1": 78, "bl2": 79, "bl3": 80, "pl": 39, "sa": 135, "ll1": 140, "ll2": 141,
    "fr1": 61, "fr2": 62, "nl1": 88, "nl2": 89, "be1": 144, "be2": 145,
    "cl": 2, "el": 3, "ecl": 848, "wm": 1, "em": 4,
    "pt1": 94, "tr1": 203, "at1": 218, "ch1": 207, "sc1": 179,
}

_calls = {"tennis": 0, "foot": 0}
TENNIS_CALL_CAP = 120   # pro Lauf
FOOT_CALL_CAP = 500


def _get(url, headers, timeout=25, retries=2):
    from urllib.error import HTTPError
    last = ""
    headers = dict(headers)
    headers.setdefault("User-Agent",
                       "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
    headers.setdefault("Accept", "application/json")
    for attempt in range(retries):
        try:
            with urlopen(Request(url, headers=headers), timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8", "replace"))
        except HTTPError as e:
            try:
                body = e.read().decode("utf-8", "replace")[:200]
            except Exception:
                body = ""
            last = f"HTTP {e.code}: {body}"
            if e.code in (401, 403, 404):
                break  # kein Retry bei Auth-/Pfadfehlern
            time.sleep(1.0 + attempt)
        except Exception as e:
            last = str(e)[:200]
            time.sleep(1.0 + attempt)
    print(f"  WARN premium: {url.split('?')[0]} -> {last}", file=sys.stderr)
    return None


def tennis_get(path):
    if not TENNIS_ENABLED or _calls["tennis"] >= TENNIS_CALL_CAP:
        return None
    _calls["tennis"] += 1
    return _get(f"https://{TENNIS_HOST}{path}",
                {"X-RapidAPI-Key": RAPID_KEY, "X-RapidAPI-Host": TENNIS_HOST})


def foot_get(path):
    if not FOOT_ENABLED or _calls["foot"] >= FOOT_CALL_CAP:
        return None
    _calls["foot"] += 1
    if FOOT_DIRECT_KEY:
        d = _get(f"https://v3.football.api-sports.io{path}",
                 {"x-apisports-key": FOOT_DIRECT_KEY})
    else:
        d = _get(f"https://{FOOT_RAPID_HOST}/v3{path}",
                 {"X-RapidAPI-Key": os.environ.get("RAPIDAPI_KEY", ""),
                  "X-RapidAPI-Host": FOOT_RAPID_HOST})
    if d and d.get("errors") and not d.get("response"):
        print(f"  WARN api-football {path.split('?')[0]}: {d['errors']}", file=sys.stderr)
    return (d or {}).get("response") or []


def _get_text(url, timeout=20):
    try:
        req = Request(url, headers={"User-Agent": "Mozilla/5.0 (SportRadar RSS Reader)"})
        with urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8", "replace")
    except Exception as e:
        print(f"  WARN rss: {url} -> {str(e)[:120]}", file=sys.stderr)
        return ""


KICKER_FEEDS = [
    "https://newsfeed.kicker.de/news/fussball",
    "https://newsfeed.kicker.de/news/bundesliga",
]


def kicker_news(max_items=80):
    """Aktuelle Kicker-Schlagzeilen (offizielle RSS-Feeds): [(titel, link)]."""
    import re as _re
    items, seen = [], set()
    for u in KICKER_FEEDS:
        raw = _get_text(u)
        for m in _re.finditer(r"<item>(.*?)</item>", raw, _re.S):
            block = m.group(1)
            t = _re.search(r"<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>", block, _re.S)
            l = _re.search(r"<link>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</link>", block, _re.S)
            if not t or not l:
                continue
            title = t.group(1).strip()
            if title in seen:
                continue
            seen.add(title)
            items.append((title, l.group(1).strip()))
            if len(items) >= max_items:
                break
    print(f"  Kicker-News: {len(items)} Schlagzeilen geladen")
    return items


def foot_lineups(fixture_id):
    """Offizielle Aufstellungen (verfuegbar ~20-40 Min vor Anpfiff)."""
    out = {}
    for e in foot_get(f"/fixtures/lineups?fixture={fixture_id}"):
        try:
            out[e["team"]["name"]] = {
                "formation": e.get("formation") or "",
                "xi": [p["player"]["name"] for p in (e.get("startXI") or [])[:11]],
            }
        except (KeyError, TypeError):
            continue
    return out


def _rows(payload):
    """MatchStat verpackt Listen mal direkt, mal unter data - beides abfangen."""
    if payload is None:
        return []
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for k in ("data", "results", "items"):
            if isinstance(payload.get(k), list):
                return payload[k]
    return []


# ---------------------------------------------------------------------------
# Tennis
# ---------------------------------------------------------------------------

RANKING_PATHS = [
    "/tennis/v2/{tour}/ranking/singles?pageSize={ps}&pageNo={pg}",
    "/tennis/v2/{tour}/rankings/singles?pageSize={ps}&pageNo={pg}",
    "/tennis/v2/{tour}/ranking/singles",
    "/tennis/v2/ms-api/{tour}/ranking/singles?pageSize={ps}&pageNo={pg}",
]


def tennis_rankings_deep(tour, key_fn, max_pages=2, page_size=500):
    """Weltrangliste weit ueber Top 150 hinaus: {player_key: position}."""
    out = {}
    template = None
    for cand in RANKING_PATHS:
        d = tennis_get(cand.format(tour=tour, ps=page_size, pg=1))
        if _rows(d):
            template = cand
            break
    if template is None:
        return out
    for page in range(1, max_pages + 1):
        d = tennis_get(template.format(tour=tour, ps=page_size, pg=page))
        rows = _rows(d)
        got = 0
        for r in rows:
            try:
                pos = r.get("position") or r.get("currentRank")
                pl = r.get("player") or r
                nm = pl.get("name") or ""
                if pos and nm:
                    out[key_fn(nm)] = int(pos)
                    got += 1
            except (ValueError, TypeError, AttributeError):
                continue
        if got == 0 and d is not None and page == 1:
            print(f"  DEBUG premium rankings {tour}: Antwortstruktur = "
                  f"{json.dumps(d)[:400]}", file=sys.stderr)
        if got < page_size:
            break
    return out


COURT_SURFACE = {1: "Hard", 2: "Clay", 3: "Hard", 4: "Carpet", 5: "Grass", 6: "Hard"}
ROUND_NAMES = {1: "Finale", 2: "Halbfinale", 3: "Viertelfinale", 4: "Achtelfinale",
               5: "2. Runde", 6: "1. Runde", 7: "1. Runde", 8: "Qualifikation"}


def tennis_fixtures_day(tour, day_iso):
    """Vollstaendiger Tagesspielplan (inkl. kleiner Turniere/Challenger-Bestand).

    Rueckgabe: Liste roher Fixture-Dicts mit tournament/court-Infos."""
    d = tennis_get(f"/tennis/v2/{tour}/fixtures/{day_iso}"
                   f"?include=tournament,tournament.court,round&pageSize=200"
                   f"&filter=PlayerGroup:singles")
    return _rows(d)


def tennis_h2h_info(tour, p1_id, p2_id):
    return tennis_get(f"/tennis/v2/{tour}/h2h/info/{p1_id}/{p2_id}")


# ---------------------------------------------------------------------------
# Fussball
# ---------------------------------------------------------------------------

ROUND_DE_FOOT = (("1st Qualifying Round", "1. Quali-Runde"),
                 ("2nd Qualifying Round", "2. Quali-Runde"),
                 ("3rd Qualifying Round", "3. Quali-Runde"),
                 ("Play-offs", "Play-offs"), ("Qualifying", "Qualifikation"))


def foot_fixtures_window(lg_id, season, date_list):
    """Anstehende Spiele (Status NS/TBD) einer Liga fuer konkrete Tage."""
    lid = FOOT_IDS.get(lg_id)
    if not FOOT_ENABLED or not lid:
        return []
    out = []
    for d in date_list:
        for fx in foot_get(f"/fixtures?league={lid}&season={season}&date={d}"
                           f"&timezone=Europe/Berlin"):
            try:
                if fx["fixture"]["status"]["short"] not in ("NS", "TBD"):
                    continue
                rnd = (fx.get("league") or {}).get("round") or ""
                for en, de in ROUND_DE_FOOT:
                    rnd = rnd.replace(en, de)
                out.append({"dt": fx["fixture"]["date"],
                            "home": fx["teams"]["home"]["name"],
                            "away": fx["teams"]["away"]["name"],
                            "round": rnd})
            except (KeyError, TypeError):
                continue
    return out


def football_enrich(lg_id, season, matches, norm_team, team_match):
    """Reichert die Spiele einer Liga an: Verletzte, Tabellenplatz, Quoten,
    Torschuetzen. Mutiert die Match-Dicts in-place."""
    if not FOOT_ENABLED or not matches:
        return
    lid = FOOT_IDS.get(lg_id)
    if not lid:
        return

    # Verletzte je Team
    inj_by_team = {}
    for e in foot_get(f"/injuries?league={lid}&season={season}"):
        try:
            tn = norm_team(e["team"]["name"])
            inj_by_team.setdefault(tn, [])
            entry = {"name": e["player"]["name"],
                     "reason": e["player"].get("reason") or e["player"].get("type") or ""}
            if entry["name"] not in [x["name"] for x in inj_by_team[tn]]:
                inj_by_team[tn].append(entry)
        except (KeyError, TypeError):
            continue

    # Tabelle
    ranks = {}
    st = foot_get(f"/standings?league={lid}&season={season}")
    try:
        for group in st[0]["league"]["standings"]:
            for row in group:
                ranks[norm_team(row["team"]["name"])] = row["rank"]
    except (IndexError, KeyError, TypeError):
        pass

    # Torschuetzen
    scorers = {}
    for e in foot_get(f"/players/topscorers?league={lid}&season={season}"):
        try:
            stat = e["statistics"][0]
            tn = norm_team(stat["team"]["name"])
            scorers.setdefault(tn, []).append(
                {"name": e["player"]["name"], "goals": stat["goals"]["total"] or 0})
        except (KeyError, IndexError, TypeError):
            continue

    def lookup(table, name):
        n = norm_team(name)
        if n in table:
            return table[n]
        for k, v in table.items():
            if team_match(n, k):
                return v
        return None

    # Fixture-IDs der Spiele im Fenster (fuer Quoten + Team-IDs fuer Fallback)
    fixture_ids = {}
    _fixture_cache[lg_id] = []
    dates = sorted({m["kickoff"][:10] for m in matches})
    for d in dates[:3]:
        for fx in foot_get(f"/fixtures?league={lid}&season={season}&date={d}"
                           f"&timezone=Europe/Berlin"):
            try:
                key = (norm_team(fx["teams"]["home"]["name"]),
                       norm_team(fx["teams"]["away"]["name"]))
                fixture_ids[key] = fx["fixture"]["id"]
                _fixture_cache[lg_id].append({
                    "hk": key[0], "ak": key[1],
                    "hid": fx["teams"]["home"]["id"], "aid": fx["teams"]["away"]["id"],
                })
            except (KeyError, TypeError):
                continue

    for m in matches:
        hk, ak = norm_team(m["home"]), norm_team(m["away"])
        inj_h = lookup(inj_by_team, m["home"]) or []
        inj_a = lookup(inj_by_team, m["away"]) or []
        if inj_h:
            m["injuriesHome"] = inj_h[:6]
        if inj_a:
            m["injuriesAway"] = inj_a[:6]
        rh, ra = lookup(ranks, m["home"]), lookup(ranks, m["away"])
        if rh:
            m["posHome"] = rh
        if ra:
            m["posAway"] = ra
        sc_h, sc_a = lookup(scorers, m["home"]), lookup(scorers, m["away"])
        if sc_h and not m.get("scorersHome"):
            m["scorersHome"] = sc_h[:3]
            m["scorersPeriod"] = "Saison"
        if sc_a and not m.get("scorersAway"):
            m["scorersAway"] = sc_a[:3]
            m["scorersPeriod"] = "Saison"
        # Quoten je Fixture (Markt "Match Winner"); Teamnamen fuzzy matchen
        fid = fixture_ids.get((hk, ak))
        if not fid:
            for (fh, fa), v in fixture_ids.items():
                if team_match(hk, fh) and team_match(ak, fa):
                    fid = v
                    break
        if fid and not m.get("odds"):
            for o in foot_get(f"/odds?fixture={fid}"):
                found = None
                for bm in o.get("bookmakers", []):
                    for bet in bm.get("bets", []):
                        if bet.get("name") != "Match Winner":
                            continue
                        vals = {v.get("value"): v.get("odd") for v in bet.get("values", [])}
                        if vals.get("Home") and vals.get("Draw") and vals.get("Away"):
                            try:
                                found = {"h": float(vals["Home"]), "d": float(vals["Draw"]),
                                         "a": float(vals["Away"]), "src": bm.get("name", "")}
                            except (ValueError, TypeError):
                                found = None
                        if found:
                            break
                    if found:
                        break
                if found:
                    m["odds"] = found
                    break
        # Offizielle Aufstellungen kurz vor Anpfiff
        try:
            from datetime import datetime as _dt, timezone as _tz
            ko = _dt.fromisoformat(m["kickoff"])
            hours = (ko - _dt.now(_tz.utc)).total_seconds() / 3600.0
            if fid and 0 <= hours <= 6 and not m.get("lineups"):
                lu = foot_lineups(fid)
                if lu:
                    def _pick(name):
                        n = norm_team(name)
                        for k, v in lu.items():
                            if team_match(n, norm_team(k)):
                                return v
                        return None
                    lh, la = _pick(m["home"]), _pick(m["away"])
                    if lh or la:
                        m["lineups"] = {"home": lh, "away": la}
                        forms = [x["formation"] for x in (lh, la) if x and x.get("formation")]
                        if forms:
                            m["analysis"] = (m.get("analysis") or "") +                                 f" Die Aufstellungen sind offiziell ({' gegen '.join(forms)})."
        except Exception as _e:
            print(f"  WARN lineups: {_e}", file=sys.stderr)

        # Verletzten-Hinweis in den Analysetext
        bits = []
        if inj_h:
            bits.append(f'{m["home"]} fehlen {len(inj_h)} Spieler '
                        f'(u.a. {inj_h[0]["name"]})')
        if inj_a:
            bits.append(f'{m["away"]} fehlen {len(inj_a)} Spieler '
                        f'(u.a. {inj_a[0]["name"]})')
        if bits and "Personal:" not in (m.get("analysis") or ""):
            m["analysis"] = (m.get("analysis") or "") + " Personal: " + "; ".join(bits) + "."


_fixture_cache = {}
_team_stats_cache = {}
FINISHED = ("FT", "AET", "PEN")


def _team_recent(team_id, n=12):
    """Letzte n beendete Spiele eines Teams (alle Wettbewerbe): Toere, Form."""
    if team_id in _team_stats_cache:
        return _team_stats_cache[team_id]
    gf = ga = cnt = 0
    form = []
    for fx in foot_get(f"/fixtures?team={team_id}&last={n}"):
        try:
            if fx["fixture"]["status"]["short"] not in FINISHED:
                continue
            is_home = fx["teams"]["home"]["id"] == team_id
            g_own = fx["goals"]["home" if is_home else "away"]
            g_opp = fx["goals"]["away" if is_home else "home"]
            if g_own is None or g_opp is None:
                continue
            gf += g_own
            ga += g_opp
            cnt += 1
            form.append("S" if g_own > g_opp else ("U" if g_own == g_opp else "N"))
        except (KeyError, TypeError):
            continue
    res = None
    if cnt >= 4:
        form.reverse()  # aeltestes zuerst (API liefert neueste zuerst)
        res = {"gf": gf / cnt, "ga": ga / cnt, "n": cnt, "form": form[-5:]}
    _team_stats_cache[team_id] = res
    return res


def foot_fallback_data(lg_id, home, away, norm_team, team_match):
    """Team-Staerken + H2H aus der API, wenn die Liga-Historie nichts hergibt."""
    hk, ak = norm_team(home), norm_team(away)
    hid = aid = None
    for e in _fixture_cache.get(lg_id, []):
        if team_match(hk, e["hk"]) and team_match(ak, e["ak"]):
            hid, aid = e["hid"], e["aid"]
            break
    if not hid or not aid:
        return None
    sh, sa = _team_recent(hid), _team_recent(aid)
    if not sh or not sa:
        return None
    h2h = []
    for fx in foot_get(f"/fixtures/headtohead?h2h={hid}-{aid}&last=5"):
        try:
            if fx["fixture"]["status"]["short"] not in FINISHED:
                continue
            h2h.append({
                "date": fx["fixture"]["date"][:10],
                "home": fx["teams"]["home"]["name"],
                "away": fx["teams"]["away"]["name"],
                "score": f'{fx["goals"]["home"]}:{fx["goals"]["away"]}',
            })
        except (KeyError, TypeError):
            continue
    return {"h": sh, "a": sa, "h2h": h2h}


def report():
    print(f"  Premium-Abrufe: Tennis {_calls['tennis']}, Fussball {_calls['foot']} "
          f"(Tennis {'AKTIV' if TENNIS_ENABLED else 'inaktiv'}, "
          f"Fussball {'AKTIV' if FOOT_ENABLED else 'inaktiv'})")

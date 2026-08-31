#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Schnell-Lauf fuer laufende Spiele: Live-Staende, Live-Quoten (API-Football)
und In-Play-Value (Restzeit-Poisson vs. Live-Quote). Schreibt data/live.json."""

import json
import math
import os
import re
import sys
import unicodedata
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))
from premium import foot_get, FOOT_IDS, FOOT_ENABLED  # noqa: E402

BASE = os.path.join(os.path.dirname(__file__), "..")
LIVE_ODDS_CAP = 18
LEAGUE_BY_ID = {v: k for k, v in FOOT_IDS.items()}


def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z ]", " ", s.lower())).strip()


def fuzzy_get(table, name):
    n = norm(name)
    if n in table:
        return table[n]
    for k, v in table.items():
        if n and k and (n in k or k in n) and min(len(n), len(k)) >= 5:
            return v
    return None


def load_prematch_mus():
    """(home,away) -> (mu_h, mu_a) aus den Vorab-Prognosen des Haupt-Laufs."""
    mus = {}
    try:
        with open(os.path.join(BASE, "data", "data.json"), encoding="utf-8") as f:
            d = json.load(f)
        for lg in d.get("football", []):
            for m in lg.get("matches", []):
                p = m.get("prediction")
                if p:
                    mus[(norm(m["home"]), norm(m["away"]))] = (p["xgHome"], p["xgAway"])
    except Exception as e:
        print(f"WARN data.json: {e}", file=sys.stderr)
    return mus


def pois(mu, k):
    return math.exp(-mu) * mu ** k / math.factorial(k)


def inplay_probs(mu_h, mu_a, goals_h, goals_a, elapsed):
    """P(Endstand-1X2) gegeben Spielstand + Restzeit (Poisson-Rest)."""
    rem = max(0.0, (95.0 - min(elapsed, 95.0)) / 90.0)
    mh, ma = max(0.03, mu_h * rem), max(0.03, mu_a * rem)
    p_h = p_d = p_a = 0.0
    for i in range(7):
        for j in range(7):
            p = pois(mh, i) * pois(ma, j)
            th, ta = goals_h + i, goals_a + j
            if th > ta:
                p_h += p
            elif th == ta:
                p_d += p
            else:
                p_a += p
    return p_h, p_d, p_a


def parse_live_odds(fixture_id):
    """1X2-Live-Quoten aus /odds/live (Struktur defensiv geparst)."""
    for entry in foot_get(f"/odds/live?fixture={fixture_id}"):
        for bet in (entry.get("odds") or []):
            name = (bet.get("name") or "").lower()
            if not any(x in name for x in ("fulltime result", "match winner", "1x2",
                                           "full time result")):
                continue
            vals = {}
            for v in (bet.get("values") or []):
                if v.get("suspended"):
                    continue
                label = str(v.get("value") or "").lower()
                try:
                    odd = float(v.get("odd"))
                except (TypeError, ValueError):
                    continue
                if label in ("home", "1"):
                    vals["h"] = odd
                elif label in ("draw", "x"):
                    vals["d"] = odd
                elif label in ("away", "2"):
                    vals["a"] = odd
            if len(vals) == 3:
                return vals
    return None


def main():
    out = {"updated": datetime.now(timezone.utc).isoformat(),
           "football": [], "tennis": []}

    if FOOT_ENABLED:
        mus = load_prematch_mus()
        live = [fx for fx in foot_get("/fixtures?live=all")
                if (fx.get("league") or {}).get("id") in LEAGUE_BY_ID]
        print(f"Live-Fussball in unseren Ligen: {len(live)}")
        for fx in live[:25]:
            try:
                home = fx["teams"]["home"]["name"]
                away = fx["teams"]["away"]["name"]
                gh = fx["goals"]["home"] or 0
                ga = fx["goals"]["away"] or 0
                elapsed = fx["fixture"]["status"].get("elapsed") or 0
                entry = {
                    "league": fx["league"]["name"],
                    "home": home, "away": away,
                    "score": f"{gh}:{ga}", "minute": elapsed,
                    "status": fx["fixture"]["status"].get("short", ""),
                }
                if len(out["football"]) < LIVE_ODDS_CAP:
                    odds = parse_live_odds(fx["fixture"]["id"])
                    if odds:
                        entry["odds"] = odds
                    mu = fuzzy_get({k[0] + "|" + k[1]: v for k, v in mus.items()},
                                   norm(home) + "|" + norm(away))
                    if mu and odds:
                        p_h, p_d, p_a = inplay_probs(mu[0], mu[1], gh, ga, elapsed)
                        entry["model"] = {"h": round(p_h, 3), "d": round(p_d, 3),
                                          "a": round(p_a, 3)}
                        inv = [1 / odds["h"], 1 / odds["d"], 1 / odds["a"]]
                        s = sum(inv)
                        imp = [x / s for x in inv]
                        diffs = [p_h - imp[0], p_d - imp[1], p_a - imp[2]]
                        best = max(range(3), key=lambda i: diffs[i])
                        p_best = [p_h, p_d, p_a][best]
                        o_best = [odds["h"], odds["d"], odds["a"]][best]
                        # hoehere Schwelle in-play + realistische Eintritts-
                        # wahrscheinlichkeit + Quoten-Deckel (keine Longshots)
                        if diffs[best] >= 0.07 and p_best >= 0.30 and o_best <= 4.5:
                            entry["value"] = {
                                "outcome": ["1", "X", "2"][best],
                                "name": [home, "Unentschieden", away][best],
                                "edge": round(diffs[best], 3),
                                "odds": [odds["h"], odds["d"], odds["a"]][best],
                            }
                out["football"].append(entry)
            except (KeyError, TypeError) as e:
                print(f"WARN live-fixture: {e}", file=sys.stderr)

    # Tennis: laufende Matches via ESPN (nur Anzeige, kein In-Play-Modell)
    try:
        from urllib.request import Request, urlopen
        seen_pairs = set()
        for tour in ("atp", "wta"):
            url = (f"https://site.api.espn.com/apis/site/v2/sports/tennis/{tour}/scoreboard")
            with urlopen(Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36", "Accept": "application/json, text/plain, */*", "Referer": "https://www.espn.com/"}), timeout=20) as r:
                d = json.loads(r.read().decode("utf-8", "replace"))
            for ev in d.get("events", []):
                comps = []
                for g in (ev.get("groupings") or []):
                    gname = ((g.get("grouping") or {}).get("displayName", "")).lower()
                    if "doubles" in gname:
                        continue
                    # Kombinierte Turniere (z.B. DC Open): der WTA-Feed enthaelt
                    # auch Herren-Matches (und umgekehrt) - nur passende Tour zeigen
                    gender = "W" if "women" in gname else ("M" if "men" in gname else None)
                    if (tour == "atp" and gender == "W") or (tour == "wta" and gender == "M"):
                        continue
                    comps.extend(g.get("competitions") or [])
                if not ev.get("groupings"):
                    comps = ev.get("competitions") or []
                for c in comps:
                    if (c.get("status") or {}).get("type", {}).get("state") != "in":
                        continue
                    names, scores = [], []
                    for comp in (c.get("competitors") or []):
                        ath = comp.get("athlete") or {}
                        names.append(ath.get("displayName")
                                     or (comp.get("roster") or {}).get("displayName") or "?")
                        sets = [str(int(ls.get("value") or 0))
                                for ls in (comp.get("linescores") or [])]
                        scores.append("-".join(sets) if sets else "")
                    if len(names) == 2:
                        pk = frozenset(n.lower() for n in names)
                        if pk in seen_pairs:
                            continue  # gleiches Match aus beiden Feeds nur 1x
                        seen_pairs.add(pk)
                        out["tennis"].append({
                            "tour": tour.upper(),
                            "tournament": ev.get("name", ""),
                            "p1": names[0], "p2": names[1],
                            "sets": f"{scores[0]} | {scores[1]}",
                        })
    except Exception as e:
        print(f"WARN tennis-live: {e}", file=sys.stderr)

    print(f"Live: {len(out['football'])} Fussball, {len(out['tennis'])} Tennis")
    with open(os.path.join(BASE, "data", "live.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False)


if __name__ == "__main__":
    main()

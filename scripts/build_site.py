#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rendert data/data.json -> index.html (komplett eigenstaendige Seite)."""

import hashlib
import html
import json
import os
from datetime import datetime, date, timedelta

BASE = os.path.join(os.path.dirname(__file__), "..")
WEEKDAYS = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
MONTHS = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli",
          "August", "September", "Oktober", "November", "Dezember"]

# Wahrscheinlichkeits-Klassen fuer die Kalibrierung ("Wenn das Modell X % sagt ...")
BUCKETS = [(0.00, 0.45, "unter 45 %"), (0.45, 0.55, "45–55 %"), (0.55, 0.65, "55–65 %"),
           (0.65, 0.75, "65–75 %"), (0.75, 0.85, "75–85 %"), (0.85, 1.01, "über 85 %")]


def esc(s):
    return html.escape(str(s)) if s is not None else ""


def de_num(x, digits=1):
    return f"{x:.{digits}f}".replace(".", ",")


def pct(x):
    return round(x * 100)


def fmt_day_label(iso, idx):
    d = date.fromisoformat(iso)
    wd = WEEKDAYS[d.weekday()][:2]
    if idx == 0:
        return "Heute", f"{wd} {d.day:02d}.{d.month:02d}."
    if idx == 1:
        return "Morgen", f"{wd} {d.day:02d}.{d.month:02d}."
    return WEEKDAYS[d.weekday()], f"{d.day:02d}.{d.month:02d}."


def fmt_dt_long(iso):
    dt = datetime.fromisoformat(iso)
    return f"{WEEKDAYS[dt.weekday()]}, {dt.day}. {MONTHS[dt.month-1]} {dt.year}, {dt:%H:%M} Uhr"


def fmt_time(iso):
    return datetime.fromisoformat(iso).strftime("%H:%M")


def bucket_of(p):
    for i, (lo, hi, _) in enumerate(BUCKETS):
        if lo <= p < hi:
            return i
    return len(BUCKETS) - 1


# ---------------------------------------------------------------- Bausteine

def form_badges(form):
    if not form:
        return '<span class="muted tiny">–</span>'
    out = []
    for f in form:
        cls = {"S": "w", "U": "d", "N": "l"}.get(f, "d")
        out.append(f'<span class="fb {cls}">{f}</span>')
    return f'<span class="form">{"".join(out)}</span>'


def prob_bar(p_home, p_draw, p_away):
    ph, pd, pa = pct(p_home), pct(p_draw), pct(p_away)
    diff = 100 - (ph + pd + pa)
    m = max((ph, "h"), (pd, "d"), (pa, "a"))
    if m[1] == "h": ph += diff
    elif m[1] == "d": pd += diff
    else: pa += diff
    seg = lambda cls, v, label: (
        f'<div class="seg {cls}" style="width:{v}%">'
        f'{f"<span>{label} {v}%</span>" if v >= 15 else ""}</div>')
    return (f'<div class="pbar" role="img" aria-label="Heimsieg {ph}%, Unentschieden {pd}%, Auswärtssieg {pa}%">'
            f'{seg("ph", ph, "1")}{seg("pd", pd, "X")}{seg("pa", pa, "2")}</div>')


def tennis_bar(p1, name1, name2):
    v1 = pct(p1)
    v2 = 100 - v1
    return (f'<div class="pbar" role="img" aria-label="{esc(name1)} {v1}%, {esc(name2)} {v2}%">'
            f'<div class="seg ph" style="width:{v1}%">{f"<span>{v1}%</span>" if v1 >= 12 else ""}</div>'
            f'<div class="seg pa" style="width:{v2}%">{f"<span>{v2}%</span>" if v2 >= 12 else ""}</div></div>')


def odds_chips(odds, value):
    if not odds:
        return '<span class="muted tiny">Quoten liegen noch nicht vor</span>'
    chips = []
    for key, label in (("h", "1"), ("d", "X"), ("a", "2")):
        v = odds.get(key)
        if v is None:
            continue
        hot = ' hot' if value and value.get("outcome") == label else ''
        chips.append(f'<span class="chip{hot}"><b>{label}</b>{de_num(v, 2)}</span>')
    src = esc(odds.get("src", ""))
    return "".join(chips) + (f'<span class="muted tiny src">{src}</span>' if src else "")


def value_note(label, odds, edge):
    return (f'<div class="value-note"><span class="gem">💎</span><div>Modell sieht <b>{esc(label)}</b> '
            f'bei Quote {de_num(odds, 2)} um <b>+{pct(edge)} Prozentpunkte</b> wahrscheinlicher '
            f'als der Markt.</div></div>')


def card_id(*parts):
    return "c_" + hashlib.md5("|".join(str(p) for p in parts).encode()).hexdigest()[:10]


def live_btn(sport, slug, kickoff, a, b):
    if not slug:
        return ""
    d = kickoff[:10].replace("-", "")
    return (f'<button class="livebtn" data-sport="{sport}" data-slug="{esc(slug)}" '
            f'data-date="{d}" data-a="{esc(a)}" data-b="{esc(b)}" title="Live-Stand bei ESPN abfragen">'
            f'📡 Live</button>')


def crest(url, name):
    initials = "".join(w[0] for w in str(name).split()[:2]).upper() or "?"
    if url:
        return (f'<span class="crest"><img src="{esc(url)}" alt="" loading="lazy" '
                f'onerror="this.parentNode.textContent=\'{esc(initials)}\'"></span>')
    return f'<span class="crest">{esc(initials)}</span>'


def star(name):
    return (f'<button class="star" data-name="{esc(name.lower())}" '
            f'aria-label="{esc(name)} als Favorit markieren" title="Als Favorit markieren">☆</button>')


def side_row(icon_html, name, meta_html, p, is_tip):
    p_html = f'<span class="rp{" tip" if is_tip else ""}">{p}%</span>' if p is not None else ""
    return (f'<div class="side">{icon_html}<div class="sname"><span class="tname">{esc(name)}</span>'
            f'{star(name)}</div><div class="smeta">{meta_html}</div>{p_html}</div>')


# ---------------------------------------------------------------- Karten

def match_card(m, league):
    pred = m.get("prediction")
    v = m.get("value")
    ph = pa = None
    tip_side = None
    if pred:
        ph, pa = pct(pred["pHome"]), pct(pred["pAway"])
        probs = [pred["pHome"], pred["pDraw"], pred["pAway"]]
        tip_side = ["h", "d", "a"][max(range(3), key=lambda i: probs[i])]
    pos_h = f'<span class="pos">{m["posHome"]}.</span>' if m.get("posHome") else ""
    pos_a = f'<span class="pos">{m["posAway"]}.</span>' if m.get("posAway") else ""
    rows = (side_row(crest(m.get("homeIcon"), m["home"]), m["home"],
                     pos_h + form_badges(m.get("formHome")), ph, tip_side == "h") +
            side_row(crest(m.get("awayIcon"), m["away"]), m["away"],
                     pos_a + form_badges(m.get("formAway")), pa, tip_side == "a"))

    pred_html = '<div class="muted tiny nopred">Zu wenig Daten für eine Vorhersage</div>'
    if pred:
        stats = [f'<span class="kv"><i>Tipp</i><b>{esc(pred["tipScore"])}</b></span>',
                 f'<span class="kv"><i>xG</i><b>{de_num(pred["xgHome"])} : {de_num(pred["xgAway"])}</b></span>',
                 f'<span class="kv"><i>Ü 2,5</i><b>{pct(pred["pOver25"])}%</b></span>']
        if pred.get("pBtts") is not None:
            stats.append(f'<span class="kv"><i>Beide tr.</i><b>{pct(pred["pBtts"])}%</b></span>')
        conf = pred.get("confidence") or ""
        stats.append(f'<span class="kv conf c-{esc(conf)}"><i>Daten</i><b>{esc(conf)}</b></span>')
        pred_html = prob_bar(pred["pHome"], pred["pDraw"], pred["pAway"]) + \
            f'<div class="kvs">{"".join(stats)}</div>'

    # Details (aufklappbar)
    det = []
    if m.get("analysis"):
        det.append(f'<p class="analysis">{esc(m["analysis"])}</p>')
    if v:
        tip_lbl = {"1": m["home"], "2": m["away"]}.get(v["outcome"], "Unentschieden")
        det.append(value_note(f'Tipp {v["outcome"]} ({tip_lbl})', v["odds"], v["edge"]))
    inj_h, inj_a = m.get("injuriesHome") or [], m.get("injuriesAway") or []
    if inj_h or inj_a:
        fmt_inj = lambda lst: ", ".join(
            f'{esc(x["name"])}' + (f' ({esc(x["reason"])})' if x.get("reason") else "")
            for x in lst[:4]) + (" …" if len(lst) > 4 else "") or "–"
        det.append(f'<div class="info"><b>🚑 Verletzt/fehlend</b><span><i>{esc(m["home"])}:</i> {fmt_inj(inj_h)}</span>'
                   f'<span><i>{esc(m["away"])}:</i> {fmt_inj(inj_a)}</span></div>')
    sc_h, sc_a = m.get("scorersHome") or [], m.get("scorersAway") or []
    if sc_h or sc_a:
        fmt_sc = lambda lst: ", ".join(f'{esc(s["name"])} ({s["goals"]})' for s in lst[:2]) or "–"
        period = f' <span class="muted tiny">({esc(m["scorersPeriod"])})</span>' if m.get("scorersPeriod") else ""
        det.append(f'<div class="info"><b>⚽ Top-Torschützen{period}</b><span><i>{esc(m["home"])}:</i> {fmt_sc(sc_h)}</span>'
                   f'<span><i>{esc(m["away"])}:</i> {fmt_sc(sc_a)}</span></div>')
    if m.get("news"):
        links = "".join(f'<a href="{esc(n["link"])}" target="_blank" rel="noopener">{esc(n["title"])}</a>'
                        for n in m["news"][:2])
        det.append(f'<div class="info"><b>📰 Vereins-News</b>{links}</div>')
    lu = m.get("lineups") or {}
    if lu.get("home") or lu.get("away"):
        parts = []
        for side, label in (("home", m["home"]), ("away", m["away"])):
            x = lu.get(side)
            if x:
                parts.append(f'<span><i>{esc(label)} ({esc(x.get("formation") or "?")}):</i> '
                             + ", ".join(esc(p) for p in x.get("xi", [])) + '</span>')
        det.append(f'<div class="info"><b>📋 Offizielle Aufstellungen</b>{"".join(parts)}</div>')
    if m.get("h2h"):
        rows_h = "".join(
            f'<tr><td>{esc(x["date"])}</td><td>{esc(x["home"])} – {esc(x["away"])}</td>'
            f'<td class="num">{esc(x["score"])}</td></tr>' for x in m["h2h"])
        det.append(f'<div class="info"><b>🔁 Direkter Vergleich</b><table class="mini">{rows_h}</table></div>')
    if m.get("basis"):
        det.append(f'<p class="basis">{esc(m["basis"])}</p>')
    has_lineup = bool(lu.get("home") or lu.get("away"))
    details = ""
    if det:
        badges = (' <span class="dot">Aufstellung</span>' if has_lineup else "") + \
                 (' <span class="dot">Ausfälle</span>' if (inj_h or inj_a) else "")
        details = (f'<details class="more"><summary>Analyse &amp; Details{badges}</summary>'
                   f'{"".join(det)}</details>')

    if m.get("matchday"):
        md = f'{m["matchday"]}. Spieltag'
    else:
        md = m.get("roundName") or ""
    cid = card_id(league["id"], m["kickoff"], m["home"], m["away"])
    lb = live_btn("fb", league.get("espn"), m["kickoff"], m["home"], m["away"])
    vpill = f'<span class="vpill" title="Value-Signal">💎 +{pct(v["edge"])}</span>' if v else ""
    names = f'{m["home"]}|{m["away"]}'.lower()
    search = f'{m["home"]} {m["away"]} {league["name"]}'.lower()
    return f"""
  <article class="card{' has-value' if v else ''}" id="{cid}" data-sport="fb" data-ko="{esc(m["kickoff"])}"
    data-names="{esc(names)}" data-search="{esc(search)}">
    <div class="cardtop"><span class="ko">{fmt_time(m["kickoff"])}</span><span class="state"></span>
      <span class="md">{esc(md)}</span>{vpill}{lb}</div>
    <div class="sides">{rows}</div>
    {pred_html}
    <div class="oddsrow">{odds_chips(m.get("odds"), v)}</div>
    {details}
  </article>"""


def _player_meta(p, surface):
    r = f'<span class="pos">#{p["rank"]}</span>' if p.get("rank") else '<span class="pos unk">o. R.</span>'
    if p.get("form"):
        r += form_badges(p["form"])
    extra = []
    b = p.get("onSurface")
    if b and surface:
        extra.append(f'{esc(surface)}: {pct(b["pct"])}% ({b["w"]}:{b["l"]})')
    if p.get("favSurface"):
        extra.append(f'Lieblingsbelag: {esc(p["favSurface"])}')
    if p.get("elo"):
        extra.append(f'Elo {p["elo"]}')
    if p.get("last7", 0) >= 3:
        extra.append(f'⚠️ {p["last7"]} Matches/7 Tage')
    return r, " · ".join(extra)


def tennis_card(m):
    surface = m.get("surface")
    r1, x1 = _player_meta(m["p1"], surface)
    r2, x2 = _player_meta(m["p2"], surface)
    p1 = p2 = None
    if m.get("pP1") is not None:
        p1 = pct(m["pP1"])
        p2 = 100 - p1
    flag = lambda n: f'<span class="crest tn">{esc("".join(w[0] for w in n.split()[:2]).upper())}</span>'
    rows = (side_row(flag(m["p1"]["name"]), m["p1"]["name"], r1, p1, p1 is not None and p1 >= 50) +
            side_row(flag(m["p2"]["name"]), m["p2"]["name"], r2, p2, p2 is not None and p2 > 50))
    bar = ""
    if m.get("pP1") is not None:
        basis = "Elo-Formmodell" if (m.get("model") or {}).get("pElo") is not None else "Weltrangliste"
        bar = tennis_bar(m["pP1"], m["p1"]["name"], m["p2"]["name"]) + \
            f'<div class="kvs"><span class="kv"><i>Basis</i><b>{basis}</b></span></div>'
    meta = []
    if m.get("round"):
        meta.append(esc(m["round"]))
    if m.get("doubles"):
        meta.append("Doppel")
    if surface:
        meta.append(esc(surface))
    unc = ('<div class="unc">⚠️ Ansetzung unbestätigt – finaler Spielplan erscheint meist erst am Vorabend</div>'
           if m.get("unconfirmed") else "")
    ko = "offen" if m.get("timeTBD") else fmt_time(m["start"])

    det = []
    if m.get("analysis"):
        det.append(f'<p class="analysis">{esc(m["analysis"])}</p>')
    v = m.get("value")
    if v:
        det.append(value_note(v["name"], v["odds"], v["edge"]))
    if x1 or x2:
        det.append(f'<div class="info"><b>📈 Spielerprofil</b>'
                   f'<span><i>{esc(m["p1"]["name"])}:</i> {x1 or "–"}</span>'
                   f'<span><i>{esc(m["p2"]["name"])}:</i> {x2 or "–"}</span></div>')
    if m.get("h2h"):
        rows_h = "".join(
            f'<tr><td>{esc(x["year"])}</td><td>{esc(x["tourney"])} ({esc(x["surface"])})</td>'
            f'<td>{esc(x["winner"])}</td><td class="num">{esc(x["score"])}</td></tr>' for x in m["h2h"])
        det.append(f'<div class="info"><b>🔁 Direkte Duelle ({len(m["h2h"])})</b><table class="mini">{rows_h}</table></div>')
    if m.get("basis"):
        det.append(f'<p class="basis">{esc(m["basis"])}</p>')
    details = (f'<details class="more"><summary>Analyse &amp; Details</summary>{"".join(det)}</details>'
               if det else "")

    odds_html = ""
    o = m.get("odds")
    if o:
        short = lambda nm: (nm.split() or [nm])[-1]
        hot1 = ' hot' if v and v["name"] == m["p1"]["name"] else ''
        hot2 = ' hot' if v and v["name"] == m["p2"]["name"] else ''
        odds_html = (f'<div class="oddsrow">'
                     f'<span class="chip{hot1}"><b>{esc(short(m["p1"]["name"]))}</b>{de_num(o["p1"], 2)}</span>'
                     f'<span class="chip{hot2}"><b>{esc(short(m["p2"]["name"]))}</b>{de_num(o["p2"], 2)}</span>'
                     f'<span class="muted tiny src">{esc(o.get("src", ""))}</span></div>')
    cid = card_id(m["tour"], m["start"], m["p1"]["name"], m["p2"]["name"])
    lb = "" if (m.get("doubles") or m["tour"] == "Challenger") else \
        live_btn("tn", m["tour"].lower(), m["start"], m["p1"]["name"], m["p2"]["name"])
    vpill = f'<span class="vpill" title="Value-Signal">💎 +{pct(v["edge"])}</span>' if v else ""
    names = f'{m["p1"]["name"]}|{m["p2"]["name"]}'.lower()
    search = f'{m["p1"]["name"]} {m["p2"]["name"]} {m["tournament"]} {m["tour"]}'.lower()
    ko_attr = "" if m.get("timeTBD") else f' data-ko="{esc(m["start"])}"'
    return f"""
  <article class="card{' has-value' if v else ''}" id="{cid}" data-sport="tn"{ko_attr}
    data-names="{esc(names)}" data-search="{esc(search)}">
    <div class="cardtop"><span class="ko">{ko}</span><span class="state"></span>
      <span class="md">{" · ".join(meta)}</span>{vpill}{lb}</div>
    {unc}
    <div class="sides">{rows}</div>
    {bar}
    {odds_html}
    {details}
  </article>"""


# ---------------------------------------------------------------- Auswertung Tipp-Log

def load_log(data_path):
    p = os.path.join(os.path.dirname(os.path.abspath(data_path)), "predictions_log.json")
    try:
        with open(p, encoding="utf-8") as f:
            return list(json.load(f).get("entries", {}).values())
    except Exception:
        return []


def calibration(entries):
    """Je Sportart und Wahrscheinlichkeits-Klasse: n, richtig."""
    cal = {"fb": [[0, 0] for _ in BUCKETS], "tn": [[0, 0] for _ in BUCKETS]}
    for e in entries:
        if e.get("status") not in ("correct", "wrong") or e.get("sport") not in cal:
            continue
        b = cal[e["sport"]][bucket_of(e["prob"])]
        b[0] += 1
        b[1] += 1 if e["correct"] else 0
    return cal


def recent_rate(entries, today, days):
    lim = (today - timedelta(days=days)).isoformat()
    items = [e for e in entries if e.get("status") in ("correct", "wrong") and e["date"] >= lim]
    return {"n": len(items), "correct": sum(1 for e in items if e["correct"])}


def daily_trend(entries, today, days=21):
    out = []
    for i in range(days, 0, -1):
        d = (today - timedelta(days=i)).isoformat()
        items = [e for e in entries if e.get("status") in ("correct", "wrong") and e["date"] == d]
        out.append((d, len(items), sum(1 for e in items if e["correct"])))
    return out


def hist_rate(cal, sport, p):
    n, c = cal[sport][bucket_of(p)]
    return (c / n, n) if n >= 20 else (None, n)


# ---------------------------------------------------------------- Seite

def build(data_path=None, out_path=None):
    data_path = data_path or os.path.join(BASE, "data", "data.json")
    out_path = out_path or os.path.join(BASE, "index.html")
    with open(data_path, encoding="utf-8") as f:
        data = json.load(f)

    gen = datetime.fromisoformat(data["generatedAt"])
    stand = f"{gen.day:02d}.{gen.month:02d}., {gen:%H:%M} Uhr"
    season = data.get("meta", {}).get("season", "")
    log = load_log(data_path)
    cal = calibration(log)

    # ---- Tipps je Tag sammeln (fuer Highlights & Tab-Zaehler)
    per_day = {d: {"tips": [], "values": [], "goals": [], "n": 0} for d in data["days"]}
    for lg in data["football"]:
        for m in lg["matches"]:
            d = m["kickoff"][:10]
            if d not in per_day:
                continue
            per_day[d]["n"] += 1
            cid = card_id(lg["id"], m["kickoff"], m["home"], m["away"])
            pred = m.get("prediction")
            label = f'{m["home"]} – {m["away"]}'
            if pred and pred.get("confidence") != "niedrig":
                probs = [pred["pHome"], pred["pDraw"], pred["pAway"]]
                bi = max(range(3), key=lambda i: probs[i])
                per_day[d]["tips"].append({
                    "sport": "fb", "p": probs[bi], "cid": cid, "time": fmt_time(m["kickoff"]),
                    "label": label, "comp": f'{lg["flag"]} {lg["name"]}',
                    "tip": [m["home"], "Unentschieden", m["away"]][bi]})
                per_day[d]["goals"].append({"p": pred["pOver25"], "cid": cid, "label": label,
                                            "time": fmt_time(m["kickoff"]),
                                            "xg": pred["xgHome"] + pred["xgAway"]})
            if m.get("value"):
                v = m["value"]
                per_day[d]["values"].append({"cid": cid, "label": label, "edge": v["edge"],
                                             "time": fmt_time(m["kickoff"]), "odds": v["odds"],
                                             "tip": {"1": m["home"], "2": m["away"]}.get(v["outcome"], "Unentschieden")})
    for t in data["tennis"]:
        d = t["start"][:10]
        if d not in per_day:
            continue
        per_day[d]["n"] += 1
        cid = card_id(t["tour"], t["start"], t["p1"]["name"], t["p2"]["name"])
        label = f'{t["p1"]["name"]} – {t["p2"]["name"]}'
        tm = "offen" if t.get("timeTBD") else fmt_time(t["start"])
        if t.get("pP1") is not None and not t.get("unconfirmed") and not t.get("doubles"):
            p1 = t["pP1"]
            per_day[d]["tips"].append({
                "sport": "tn", "p": max(p1, 1 - p1), "cid": cid, "time": tm, "label": label,
                "comp": f'🎾 {t["tour"]} · {t["tournament"]}',
                "tip": t["p1"]["name"] if p1 >= 0.5 else t["p2"]["name"]})
        if t.get("value"):
            v = t["value"]
            per_day[d]["values"].append({"cid": cid, "label": label, "edge": v["edge"],
                                         "time": tm, "odds": v["odds"], "tip": v["name"]})

    def highlights(d):
        info = per_day[d]
        if not info["n"]:
            return ""
        blocks = []
        tips = sorted(info["tips"], key=lambda x: -x["p"])[:5]
        if tips:
            li = ""
            for x in tips:
                hr, hn = hist_rate(cal, x["sport"], x["p"])
                hist = (f'<span class="hist" title="So oft lagen bisherige {"Fußball" if x["sport"] == "fb" else "Tennis"}-Tipps '
                        f'dieser Sicherheitsklasse richtig ({hn} ausgewertet)">bisher {pct(hr)}% ✓</span>'
                        if hr is not None else "")
                li += (f'<li class="jump" data-cid="{x["cid"]}"><span class="hl-p">{pct(x["p"])}%</span>'
                       f'<span class="hl-main"><b>{esc(x["tip"])}</b><span class="muted tiny">{x["time"]} · '
                       f'{esc(x["label"])}</span></span>{hist}</li>')
            blocks.append(f'<div class="hl"><h3>🎯 Sicherste Tipps</h3><ul>{li}</ul></div>')
        vals = sorted(info["values"], key=lambda x: -x["edge"])[:5]
        if vals:
            li = "".join(
                f'<li class="jump" data-cid="{x["cid"]}"><span class="hl-p gold">+{pct(x["edge"])}</span>'
                f'<span class="hl-main"><b>{esc(x["tip"])}</b><span class="muted tiny">{x["time"]} · '
                f'{esc(x["label"])} · Quote {de_num(x["odds"], 2)}</span></span></li>' for x in vals)
            more = len(info["values"]) - len(vals)
            more_html = f'<div class="muted tiny" style="padding:4px 2px 0">+ {more} weitere in der Value-Liste</div>' if more > 0 else ""
            blocks.append(f'<div class="hl"><h3>💎 Größte Value-Signale</h3><ul>{li}</ul>{more_html}</div>')
        goals = [x for x in sorted(info["goals"], key=lambda x: -x["p"]) if x["p"] >= 0.5][:4]
        if goals:
            li = "".join(
                f'<li class="jump" data-cid="{x["cid"]}"><span class="hl-p green">{pct(x["p"])}%</span>'
                f'<span class="hl-main"><b>{esc(x["label"])}</b><span class="muted tiny">{x["time"]} · '
                f'xG gesamt {de_num(x["xg"])}</span></span></li>' for x in goals)
            blocks.append(f'<div class="hl"><h3>🔥 Torreichste Spiele <span class="muted tiny">(Über 2,5)</span></h3><ul>{li}</ul></div>')
        if not blocks:
            return ""
        return f'<section class="highlights">{"".join(blocks)}</section>'

    # ---- Tages-Tabs & Panels
    tabs, panels = [], []
    for i, day_iso in enumerate(data["days"]):
        label, sub = fmt_day_label(day_iso, i)
        info = per_day[day_iso]
        nv = len(info["values"])
        cnt = f'<span class="tabcnt">{info["n"]} Spiele{f" · 💎 {nv}" if nv else ""}</span>'
        tabs.append(f'<button class="tab{" active" if i == 0 else ""}" data-day="{i}">'
                    f'<span class="tablab">{label} <span class="tabsub">{sub}</span></span>{cnt}</button>')

        fb_sections = []
        for lg in data["football"]:
            day_matches = sorted((m for m in lg["matches"] if m["kickoff"][:10] == day_iso),
                                 key=lambda m: m["kickoff"])
            if not day_matches:
                continue
            cards = "".join(match_card(m, lg) for m in day_matches)
            fb_sections.append(
                f'<details class="league" data-cat="fussball" open>'
                f'<summary><h2><span class="lgflag">{lg["flag"]}</span>{esc(lg["name"])}'
                f'<span class="cnt">{len(day_matches)}</span></h2></summary>'
                f'<div class="grid">{cards}</div></details>')

        tn_by_tour = {}
        for m in data["tennis"]:
            if m["start"][:10] != day_iso:
                continue
            tn_by_tour.setdefault((m["tour"], m["tournament"]), []).append(m)
        tn_sections = []
        for k, ((tour, tournament), ms) in enumerate(sorted(tn_by_tour.items())):
            cards = "".join(tennis_card(m) for m in sorted(ms, key=lambda x: x["start"]))
            srf = next((x.get("surface") for x in ms if x.get("surface")), None)
            srf_html = f'<span class="surf s-{esc(srf)}">{esc(srf)}</span>' if srf else ""
            tn_sections.append(
                f'<details class="league" data-cat="tennis"{" open" if k < 2 else ""}>'
                f'<summary><h2><span class="lgflag">🎾</span>{esc(tour)} · {esc(tournament)}{srf_html}'
                f'<span class="cnt">{len(ms)}</span></h2></summary>'
                f'<div class="grid">{cards}</div></details>')

        body = "".join(fb_sections) + "".join(tn_sections)
        if i == 0 and data.get("tennisFinished"):
            rows = ""
            for f in sorted(data["tennisFinished"], key=lambda f: (f["tour"], f["tournament"])):
                score = f' {esc(f["score"])}' if f.get("score") else ""
                rows += (f'<tr><td>{esc(f["tour"])} · {esc(f["tournament"])}</td>'
                         f'<td>{esc(f["p1"])} – {esc(f["p2"])}</td>'
                         f'<td class="num"><b>{esc(f["winner"])}</b>{score}</td></tr>')
            body += (f'<details class="league" data-cat="tennis">'
                     f'<summary><h2><span class="lgflag">✅</span>Heute bereits gespielt'
                     f'<span class="cnt">{len(data["tennisFinished"])}</span></h2></summary>'
                     f'<div class="tablewrap"><table class="tbl"><thead><tr><th>Turnier</th>'
                     f'<th>Match</th><th>Sieger &amp; Ergebnis</th></tr></thead>'
                     f'<tbody>{rows}</tbody></table></div></details>')
        if not body:
            body = '<div class="empty">Für diesen Tag sind (noch) keine Partien angesetzt.</div>'
        body += '<div class="empty nohit" hidden>Keine Partien passen zu Suche/Filter.</div>'
        panels.append(f'<div class="daypanel{" active" if i == 0 else ""}" data-day="{i}">'
                      f'{highlights(day_iso)}{body}</div>')

    # ---- Ligen ohne Spiele
    pause_rows = []
    for lg in data["football"]:
        if lg["matches"]:
            continue
        nm = lg.get("nextMatch")
        if lg.get("isCup") and not nm:
            continue
        if nm:
            md = f' · {nm["matchday"]}. Spieltag' if nm.get("matchday") else ""
            pause_rows.append(
                f'<tr><td>{lg["flag"]} {esc(lg["name"])}</td>'
                f'<td>{fmt_dt_long(nm["kickoff"])}{md}</td>'
                f'<td>{esc(nm["home"])} – {esc(nm["away"])}</td></tr>')
        else:
            pause_rows.append(
                f'<tr><td>{lg["flag"]} {esc(lg["name"])}</td>'
                f'<td colspan="2" class="muted">Kein Termin gefunden – vermutlich Saisonpause</td></tr>')
    pause_html = ""
    if pause_rows:
        pause_html = (
            '<details class="block"><summary><h2>⏸️ Ligen ohne Spiele in den nächsten 3 Tagen '
            f'<span class="cnt">{len(pause_rows)}</span></h2></summary>'
            '<div class="tablewrap"><table class="tbl"><thead><tr><th>Liga</th><th>Nächstes Spiel</th>'
            f'<th>Partie</th></tr></thead><tbody>{"".join(pause_rows)}</tbody></table></div></details>')

    # ---- Bilanz & Kalibrierung
    stats_html = ""
    st = data.get("stats")
    if st:
        today = gen.date()

        def tile(label, s, sub_extra="", big=None):
            if not s or not s.get("n"):
                return f'<div class="tile"><div class="tval muted">–</div><div class="tlab">{label}</div></div>'
            val = big if big is not None else f'{round(s["correct"] / s["n"] * 100)}<span class="tunit">%</span>'
            return (f'<div class="tile"><div class="tval">{val}</div><div class="tlab">{label}</div>'
                    f'<div class="tsub">{s["correct"]} von {s["n"]} richtig{sub_extra}</div></div>')
        r7 = recent_rate(log, today, 7) if log else None
        tiles = (tile("Alle Tipps", st.get("overall")) +
                 tile("Letzte 7 Tage", r7) +
                 tile("Fußball (1X2)", st.get("football")) +
                 tile("Tennis (Sieger)", st.get("tennis")) +
                 tile("Exaktes Ergebnis", st.get("exact")))
        vs = st.get("value")
        if vs and vs.get("n"):
            u = vs["units"]
            tiles += (f'<div class="tile gold"><div class="tval">{"+" if u >= 0 else ""}{de_num(u, 1)}'
                      f'<span class="tunit"> E.</span></div><div class="tlab">Value-Signale</div>'
                      f'<div class="tsub">{vs["correct"]} von {vs["n"]} getroffen · Ø Quote '
                      f'{de_num(vs["avgOdds"], 2)} · hypothetisch 1 Einheit je Signal</div></div>')

        # Kalibrierung
        cal_html = ""
        if log:
            rows = ""
            for bi, (lo, hi, lab) in enumerate(BUCKETS):
                cells = ""
                for sp in ("fb", "tn"):
                    n, c = cal[sp][bi]
                    if n < 10:
                        cells += '<td class="calcell"><span class="muted tiny">zu wenig Daten</span></td>'
                        continue
                    r = c / n
                    mid = min(max((lo + min(hi, 1.0)) / 2, 0.35), 0.93)
                    diff = r - mid
                    tone = "ok" if abs(diff) <= 0.05 else ("over" if diff > 0 else "under")
                    cells += (f'<td class="calcell"><div class="calbar"><div class="calfill {tone}" '
                              f'style="width:{pct(r)}%"></div><div class="calmark" style="left:{pct(mid)}%"></div></div>'
                              f'<span class="calnum"><b>{pct(r)}%</b> <span class="muted tiny">n={n}</span></span></td>')
                rows += f'<tr><th>{lab}</th>{cells}</tr>'
            cal_html = (
                '<div class="calwrap"><h3>Wie verlässlich sind die Prozentangaben?</h3>'
                '<p class="muted small">Für jede Sicherheitsklasse: Wie oft lag der Tipp tatsächlich richtig? '
                'Der Strich markiert die Mitte der Klasse – liegt der Balken ungefähr dort, sind die '
                'Prozente ehrlich kalibriert. <span class="lg l-ok">passt</span> '
                '<span class="lg l-over">besser als angegeben</span> <span class="lg l-under">schlechter als angegeben</span></p>'
                '<div class="tablewrap"><table class="caltbl"><thead><tr><th>Modell sagt</th><th>⚽ Fußball – tatsächlich</th>'
                f'<th>🎾 Tennis – tatsächlich</th></tr></thead><tbody>{rows}</tbody></table></div></div>')

        # Verlauf letzte 3 Wochen
        trend_html = ""
        if log:
            tr = daily_trend(log, today)
            bars = ""
            for d, n, c in tr:
                dd = date.fromisoformat(d)
                lab = f'{WEEKDAYS[dd.weekday()][:2]} {dd.day:02d}.{dd.month:02d}.'
                if n:
                    h = max(4, pct(c / n))
                    bars += (f'<div class="tb" title="{lab}: {c} von {n} richtig ({pct(c / n)}%)">'
                             f'<div class="tbf" style="height:{h}%"></div><span>{dd.day}</span></div>')
                else:
                    bars += f'<div class="tb empty" title="{lab}: keine Auswertung"><span>{dd.day}</span></div>'
            trend_html = (f'<div class="calwrap"><h3>Trefferquote pro Tag <span class="muted tiny">'
                          f'(letzte 3 Wochen, Linie = 50 %)</span></h3><div class="trend">{bars}</div></div>')

        rows = ""
        for r in st.get("recent", []):
            mark = '<span class="ok">✓</span>' if r["correct"] else '<span class="bad">✗</span>'
            icon = "⚽" if r["sport"] == "fb" else "🎾"
            rows += (f'<tr><td>{mark}</td><td>{esc(r["date"][8:10])}.{esc(r["date"][5:7])}.</td>'
                     f'<td>{icon} {esc(r["label"])}</td>'
                     f'<td>{esc(r["tipName"])} <span class="muted">({pct(r["prob"])}%)</span></td>'
                     f'<td class="num">{esc(r.get("result") or "–")}</td></tr>')
        recent_tbl = (f'<details class="sub"><summary>Zuletzt ausgewertete Tipps ({len(st.get("recent", []))})</summary>'
                      f'<div class="tablewrap"><table class="tbl">{rows}</table></div></details>') if rows else ""
        stats_html = (f'<section class="block" id="bilanz"><h2>📊 Bilanz des Modells '
                      f'<span class="cnt">{st.get("open", 0)} offen</span></h2>'
                      f'<div class="tiles">{tiles}</div>{trend_html}{cal_html}{recent_tbl}</section>')

    # ---- Value-Bets-Liste
    value_rows = []
    for lg in data["football"]:
        for m in lg["matches"]:
            v = m.get("value")
            if not v:
                continue
            value_rows.append({
                "when": m["kickoff"], "comp": f'{lg["flag"]} {lg["name"]}',
                "label": f'{m["home"]} – {m["away"]}',
                "tip": f'{v["outcome"]} · ' + {"1": m["home"], "2": m["away"]}.get(v["outcome"], "Unentschieden"),
                "modelP": v["modelP"], "odds": v["odds"], "edge": v["edge"],
                "cid": card_id(lg["id"], m["kickoff"], m["home"], m["away"]),
            })
    for t in data["tennis"]:
        v = t.get("value")
        if not v:
            continue
        value_rows.append({
            "when": t["start"], "comp": f'🎾 {t["tour"]} · {t["tournament"]}',
            "label": f'{t["p1"]["name"]} – {t["p2"]["name"]}', "tip": v["name"],
            "modelP": v["modelP"], "odds": v["odds"], "edge": v["edge"],
            "cid": card_id(t["tour"], t["start"], t["p1"]["name"], t["p2"]["name"]),
        })
    value_rows.sort(key=lambda r: r["when"])
    value_html = ""
    if value_rows:
        rows = ""
        for r in value_rows[:40]:
            dt = datetime.fromisoformat(r["when"])
            imp = 1.0 / r["odds"] if r["odds"] else 0
            try:
                day_idx = data["days"].index(r["when"][:10])
            except ValueError:
                day_idx = 0
            w = min(100, pct(r["edge"]) * 4)
            rows += (f'<tr class="vrow jump" data-day="{day_idx}" data-cid="{r["cid"]}" data-ko="{esc(r["when"])}" '
                     f'title="Zur Analyse springen">'
                     f'<td class="nowrap">{WEEKDAYS[dt.weekday()][:2]} {dt:%H:%M}</td>'
                     f'<td><b>{esc(r["tip"])}</b><div class="muted tiny">{esc(r["label"])} · {esc(r["comp"])}</div></td>'
                     f'<td class="num">{pct(r["modelP"])}%</td>'
                     f'<td class="num">{pct(imp)}%</td>'
                     f'<td class="num">{de_num(r["odds"], 2)}</td>'
                     f'<td class="num edge"><span class="edgebar" style="width:{w}%"></span><b>+{pct(r["edge"])}</b></td></tr>')
        value_html = (
            '<details class="block" id="valuebets" open><summary><h2>💎 Value-Liste '
            f'<span class="cnt">{len(value_rows)}</span></h2></summary>'
            '<p class="muted small">Partien, bei denen das Modell ein Ergebnis deutlich wahrscheinlicher sieht als die '
            'Buchmacher-Quote. Nur realistische Signale: Modell-Wahrscheinlichkeit ≥ 30 % (Tennis 38 %), '
            'Quote gedeckelt, solide Datenlage. Zeile antippen = zur Analyse.</p>'
            '<div class="tablewrap"><table class="tbl vtbl"><thead><tr><th>Anstoß</th><th>Tipp</th>'
            '<th class="num">Modell</th><th class="num">Markt</th><th class="num">Quote</th>'
            f'<th class="num">Edge</th></tr></thead><tbody>{rows}</tbody></table></div>'
            '<div class="muted tiny" style="margin-top:6px">Statistische Signale mit Unsicherheit – keine '
            'Wettempfehlung. Edge = Modell- minus Markt-Wahrscheinlichkeit in Prozentpunkten.</div></details>')

    n_fb = sum(len(l["matches"]) for l in data["football"])
    n_tn = len(data["tennis"])
    ov = (st or {}).get("overall") or {}
    hit = f'{round(ov["correct"] / ov["n"] * 100)} %' if ov.get("n") else "–"

    banner = ""
    if data.get("meta", {}).get("demo"):
        banner = ('<div class="banner">🧪 <b>Demo-Ansicht mit Beispieldaten:</b> Formkurven, '
                  'Wahrscheinlichkeiten und Quoten sind hier nur illustrative Beispiele.</div>')
    elif data.get("meta", {}).get("preview"):
        banner = ('<div class="banner">👋 <b>Vorschau:</b> Tennis-Rankings, exakte Anstoßzeiten und Quoten '
                  'werden ab dem ersten automatischen Update vollständig befüllt.</div>')

    header = f"""
<header class="hero">
  <div class="heroin">
    <div class="brand"><span class="logo">⚽</span><div><h1>Sport-Radar</h1>
      <div class="sub">Spiele &amp; Modell-Analysen der nächsten 3 Tage{f" · Saison {esc(season)}" if season else ""}</div></div></div>
    <div class="kpis">
      <div class="kpi"><b>{n_fb}</b><span>Fußball</span></div>
      <div class="kpi"><b>{n_tn}</b><span>Tennis</span></div>
      <div class="kpi"><b>{len(value_rows)}</b><span>Value</span></div>
      <a class="kpi" href="#bilanz"><b>{hit}</b><span>Trefferquote</span></a>
    </div>
  </div>
  <div class="heroin stand">Stand: <b>{stand}</b> <span id="age"></span></div>
</header>
<nav class="bar">
  <div class="barin">
    <div class="tabs">{"".join(tabs)}</div>
    <div class="tools">
      <div class="filters">
        <button class="flt active" data-f="alle">Alle</button>
        <button class="flt" data-f="fussball">⚽ Fußball</button>
        <button class="flt" data-f="tennis">🎾 Tennis</button>
        <button class="flt" data-f="value">💎 Nur Value</button>
        <button class="flt" data-f="fav">★ Favoriten</button>
      </div>
      <label class="search"><span aria-hidden="true">🔍</span>
        <input id="q" type="search" placeholder="Team, Spieler, Liga …" autocomplete="off" aria-label="Suchen"></label>
    </div>
  </div>
</nav>"""

    html_doc = (HEAD + header + f"""
<main>
{banner}
<section class="block" id="livebox" hidden><h2><span class="livedot"></span>Jetzt live
  <span class="muted tiny" id="liveinfo"></span></h2><div id="livebody" class="livegrid"></div></section>
{"".join(panels)}
{value_html}
{stats_html}
{pause_html}
</main>
<footer>
  <details>
    <summary>Wie funktionieren die Vorhersagen?</summary>
    <p><b>Fußball:</b> Poisson-Modell auf Basis der Ergebnisse der letzten zwei Saisons (neuere Spiele
    zählen stärker), inkl. Heimvorteil. Daraus ergeben sich Wahrscheinlichkeiten für 1/X/2,
    erwartete Tore (xG) und ein wahrscheinlichstes Ergebnis. „Value“ markiert Fälle, in denen das
    Modell ein Ergebnis deutlich wahrscheinlicher einschätzt als die Buchmacher-Quote.</p>
    <p><b>Tennis:</b> Elo-Formmodell aus rund 24.000 Tour-Matches der letzten fünf Jahre, mit eigenem
    Rating je Belag, direktem Vergleich und der Weltrangliste als Absicherung bei dünner Datenlage
    („o. R.“ = ohne Top-Ranking).</p>
    <p><b>„bisher X % ✓“</b> bei den sichersten Tipps zeigt, wie oft frühere Tipps derselben
    Sicherheitsklasse tatsächlich richtig lagen. Alle Angaben sind statistische Schätzungen ohne Gewähr.</p>
  </details>
  <div>Datenquellen: OpenLigaDB, ESPN, football-data.co.uk,
  <a href="http://www.tennis-data.co.uk">tennis-data.co.uk</a>, TheSportsDB. Privates, nicht-kommerzielles Projekt.
  · <a href="https://github.com/BLSports/blsports.github.io/actions/workflows/update.yml" target="_blank" rel="noopener">🔁 Update anstoßen</a>
  <span class="tiny">(nur Betreiber)</span></div>
  <div class="disclaimer">Keine Wettempfehlung. Quoten dienen nur dem Vergleich mit dem Modell. Glücksspiel kann
  süchtig machen (18+) – Hilfe: <a href="https://www.bundesweit-gegen-gluecksspielsucht.de">bundesweit-gegen-gluecksspielsucht.de</a>.</div>
</footer>
<script>
const GEN = {json.dumps(data["generatedAt"])};
""" + SCRIPT + "</script>\n</body>\n</html>")

    out_dir = os.path.dirname(out_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html_doc)
    print(f"OK -> {out_path}  ({len(html_doc)//1024} kB)")


# ---------------------------------------------------------------- Statische Teile

HEAD = r"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<meta name="theme-color" content="#0e3b2c">
<title>Sport-Radar · Spiele & Analysen der nächsten 3 Tage</title>
<link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>⚽</text></svg>">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@600;700&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
:root {
  color-scheme: light;
  --page:#f3f4f1; --surface:#ffffff; --surface2:#f7f8f5; --ink:#101512; --ink2:#4b524d;
  --muted:#868d88; --grid:#e3e6e1; --border:rgba(16,21,18,.09);
  --home:#2563c9; --away:#e0662f; --draw:#e7e9e4; --draw-ink:#4b524d;
  --good:#17a34a; --bad:#dc3d3d; --accent:#11875d; --gold:#c98a04; --gold-bg:#fff6dc;
  --brand:#0e3b2c; --brand2:#145c43;
  --shadow:0 1px 2px rgba(16,21,18,.05),0 4px 14px rgba(16,21,18,.05);
  --num:"Barlow Condensed",system-ui,sans-serif;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    color-scheme: dark;
    --page:#0b0f0d; --surface:#151a17; --surface2:#1b211e; --ink:#eef2ee; --ink2:#b4bdb6;
    --muted:#7d877f; --grid:#262e29; --border:rgba(255,255,255,.08);
    --home:#4c8bf0; --away:#ee7a45; --draw:#2f3632; --draw-ink:#b4bdb6;
    --good:#22c55e; --bad:#ef5b5b; --accent:#2fbf86; --gold:#f2b632; --gold-bg:#2c2412;
    --brand:#0a2a20; --brand2:#0f3d2e;
    --shadow:0 1px 2px rgba(0,0,0,.4);
  }
}
* { box-sizing:border-box; }
html { scroll-padding-top:150px; }
body { margin:0; background:var(--page); color:var(--ink);
  font:14.5px/1.45 Inter,system-ui,-apple-system,"Segoe UI",sans-serif; -webkit-font-smoothing:antialiased; }
a { color:var(--accent); }
h1,h2,h3 { margin:0; }
[hidden] { display:none !important; }

/* Kopfbereich */
.hero { background:radial-gradient(120% 140% at 85% -20%, var(--brand2) 0%, var(--brand) 55%);
  color:#fff; padding:20px 16px 12px; position:relative; overflow:hidden; }
.hero::after { content:""; position:absolute; right:-70px; top:-70px; width:260px; height:260px;
  border:2px solid rgba(255,255,255,.07); border-radius:50%; box-shadow:0 0 0 60px rgba(255,255,255,.025); }
.heroin { max-width:1180px; margin:0 auto; display:flex; gap:16px; align-items:center;
  justify-content:space-between; flex-wrap:wrap; position:relative; z-index:1; }
.brand { display:flex; gap:12px; align-items:center; }
.logo { width:44px; height:44px; border-radius:12px; background:rgba(255,255,255,.1);
  display:grid; place-items:center; font-size:24px; }
h1 { font-family:var(--num); font-size:30px; letter-spacing:.5px; text-transform:uppercase; line-height:1; }
.sub { color:rgba(255,255,255,.72); font-size:13px; margin-top:3px; }
.kpis { display:flex; gap:8px; }
.kpi { background:rgba(255,255,255,.08); border:1px solid rgba(255,255,255,.1); border-radius:10px;
  padding:6px 12px; min-width:72px; text-align:center; color:#fff; text-decoration:none; }
.kpi b { display:block; font-family:var(--num); font-size:22px; line-height:1.1; }
.kpi span { font-size:11px; color:rgba(255,255,255,.7); }
.stand { font-size:12px; color:rgba(255,255,255,.65); margin-top:10px; justify-content:flex-start; }
.stand b { color:#fff; font-weight:600; }

/* Sticky-Leiste */
.bar { position:sticky; top:0; z-index:20; background:color-mix(in srgb, var(--page) 88%, transparent);
  backdrop-filter:saturate(1.4) blur(10px); -webkit-backdrop-filter:saturate(1.4) blur(10px);
  border-bottom:1px solid var(--border); }
.barin { max-width:1180px; margin:0 auto; padding:10px 16px 8px; }
.tabs { display:grid; grid-template-columns:repeat(3,1fr); gap:6px; }
.tab { background:var(--surface); border:1px solid var(--border); border-radius:10px; padding:7px 10px;
  font:inherit; color:var(--ink2); cursor:pointer; text-align:left; display:flex; flex-direction:column; gap:1px; }
.tab .tablab { font-weight:700; font-size:14px; }
.tab .tabsub { font-weight:500; color:var(--muted); font-size:12px; }
.tab .tabcnt { font-size:11.5px; color:var(--muted); }
.tab.active { color:var(--ink); border-color:var(--accent); box-shadow:inset 0 -3px 0 var(--accent); }
.tools { display:flex; gap:8px; margin-top:8px; align-items:center; flex-wrap:wrap; }
.filters { display:flex; gap:6px; overflow-x:auto; scrollbar-width:none; flex:1 1 auto; }
.filters::-webkit-scrollbar { display:none; }
.flt { background:var(--surface); border:1px solid var(--border); border-radius:999px; padding:5px 12px;
  font:inherit; font-size:13px; color:var(--ink2); cursor:pointer; white-space:nowrap; }
.flt.active { background:var(--ink); color:var(--page); border-color:var(--ink); font-weight:600; }
.search { display:flex; align-items:center; gap:6px; background:var(--surface); border:1px solid var(--border);
  border-radius:999px; padding:0 12px; flex:0 1 260px; min-width:180px; }
.search input { border:0; background:none; font:inherit; color:var(--ink); padding:6px 0; width:100%; outline:none; }

main { max-width:1180px; margin:0 auto; padding:6px 16px 40px; }

/* Highlights */
.highlights { display:grid; grid-template-columns:repeat(auto-fit,minmax(290px,1fr)); gap:10px; margin:14px 0 6px; }
.hl { background:var(--surface); border:1px solid var(--border); border-radius:14px; padding:12px 12px 8px; box-shadow:var(--shadow); }
.hl h3 { font-size:13px; text-transform:uppercase; letter-spacing:.4px; color:var(--ink2); margin:0 0 6px; }
.hl ul { list-style:none; margin:0; padding:0; }
.hl li { display:flex; align-items:center; gap:10px; padding:6px 4px; border-top:1px solid var(--grid); cursor:pointer; border-radius:6px; }
.hl li:first-child { border-top:0; }
.hl li:hover { background:var(--surface2); }
.hl-p { font-family:var(--num); font-weight:700; font-size:19px; min-width:46px; color:var(--accent); }
.hl-p.gold { color:var(--gold); } .hl-p.green { color:var(--good); }
.hl-main { display:flex; flex-direction:column; min-width:0; flex:1; }
.hl-main b { font-weight:600; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.hl-main .tiny { white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.hist { font-size:11px; color:var(--ink2); background:var(--surface2); border:1px solid var(--grid);
  border-radius:999px; padding:1px 7px; white-space:nowrap; }

/* Ligen */
.daypanel { display:none; } .daypanel.active { display:block; }
.league { margin-top:18px; }
.league > summary, .block > summary { cursor:pointer; list-style:none; }
.league > summary::-webkit-details-marker, .block > summary::-webkit-details-marker { display:none; }
.league h2, .block h2 { font-size:15px; font-weight:700; display:flex; align-items:center; gap:8px;
  padding:6px 0 8px; border-bottom:2px solid var(--grid); }
.league > summary h2::after, details.block > summary h2::after { content:"⌄"; margin-left:auto; color:var(--muted);
  transition:transform .2s; font-size:18px; line-height:1; }
.league:not([open]) > summary h2::after, details.block:not([open]) > summary h2::after { transform:rotate(-90deg); }
.lgflag { font-size:17px; }
.cnt { font-size:11.5px; font-weight:600; color:var(--ink2); background:var(--surface); border:1px solid var(--border);
  border-radius:999px; padding:0 8px; }
.surf { font-size:11px; font-weight:600; border-radius:999px; padding:1px 8px; color:#fff; background:#888; }
.surf.s-Sand { background:#c8642d; } .surf.s-Hartplatz { background:#2f6fcf; } .surf.s-Rasen { background:#2f9a4c; }
.grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(340px,1fr)); gap:10px; margin-top:10px; }

/* Karten */
.card { background:var(--surface); border:1px solid var(--border); border-radius:14px; padding:12px 14px;
  box-shadow:var(--shadow); position:relative; transition:opacity .2s, outline-color .3s; }
.card.has-value { border-color:color-mix(in srgb, var(--gold) 45%, var(--border)); }
.card.has-value::before { content:""; position:absolute; left:-1px; top:14px; bottom:14px; width:3px;
  border-radius:0 3px 3px 0; background:var(--gold); }
.card.over { opacity:.55; }
.card.flash { outline:2px solid var(--accent); }
.cardtop { display:flex; align-items:center; gap:8px; margin-bottom:8px; font-size:12px; }
.ko { font-family:var(--num); font-weight:700; font-size:18px; line-height:1; }
.state { font-size:11px; font-weight:600; border-radius:999px; padding:1px 7px; }
.state:empty { display:none; }
.state.soon { background:var(--surface2); color:var(--ink2); border:1px solid var(--grid); }
.state.live { background:var(--bad); color:#fff; }
.state.done { background:var(--draw); color:var(--draw-ink); }
.md { color:var(--muted); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; min-width:0; flex:1; }
.vpill { font-size:11.5px; font-weight:700; color:var(--gold); background:var(--gold-bg); border-radius:999px; padding:1px 8px; white-space:nowrap; }
.livebtn { background:none; border:1px solid var(--border); border-radius:999px; padding:2px 9px; font:inherit;
  font-size:11px; color:var(--ink2); cursor:pointer; white-space:nowrap; }
.sides { display:flex; flex-direction:column; gap:6px; margin-bottom:10px; }
.side { display:grid; grid-template-columns:30px 1fr auto; grid-template-rows:auto auto; column-gap:10px; align-items:center; }
.crest { grid-row:1 / 3; width:30px; height:30px; border-radius:8px; background:var(--surface2); border:1px solid var(--grid);
  display:grid; place-items:center; overflow:hidden; font-size:11px; font-weight:700; color:var(--ink2); }
.crest img { width:24px; height:24px; object-fit:contain; }
.crest.tn { border-radius:50%; font-size:10.5px; }
.sname { display:flex; align-items:center; gap:4px; min-width:0; }
.tname { font-weight:650; font-size:15px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.smeta { display:flex; gap:6px; align-items:center; grid-column:2; }
.rp { grid-row:1 / 3; grid-column:3; font-family:var(--num); font-weight:700; font-size:20px; color:var(--muted); }
.rp.tip { color:var(--ink); }
.star { background:none; border:0; padding:0 2px; cursor:pointer; color:var(--muted); font-size:14px; line-height:1; opacity:.55; }
.star:hover { opacity:1; }
.star.on { color:var(--gold); opacity:1; }
.pos { font-size:11px; font-weight:600; color:var(--ink2); background:var(--surface2); border:1px solid var(--grid);
  border-radius:5px; padding:0 5px; }
.pos.unk { border-style:dashed; color:var(--muted); }
.form { display:inline-flex; gap:2px; }
.fb { display:inline-block; width:16px; height:16px; border-radius:4px; font-size:10px; font-weight:700;
  text-align:center; line-height:16px; color:#fff; }
.fb.w { background:var(--good); } .fb.l { background:var(--bad); }
.fb.d { background:var(--draw); color:var(--draw-ink); }
.pbar { display:flex; height:24px; border-radius:7px; overflow:hidden; gap:2px; }
.seg { display:flex; align-items:center; justify-content:center; font-size:11.5px; font-weight:700;
  color:#fff; min-width:0; white-space:nowrap; overflow:hidden; }
.seg.ph { background:var(--home); } .seg.pa { background:var(--away); }
.seg.pd { background:var(--draw); color:var(--draw-ink); }
.kvs { display:flex; gap:6px; flex-wrap:wrap; margin-top:8px; }
.kv { display:inline-flex; align-items:baseline; gap:5px; background:var(--surface2); border-radius:7px; padding:3px 8px; font-size:12.5px; }
.kv i { font-style:normal; color:var(--muted); font-size:11px; }
.kv b { font-weight:600; }
.kv.c-hoch b { color:var(--good); } .kv.c-niedrig b { color:var(--bad); }
.nopred { padding:6px 0; }
.oddsrow { display:flex; gap:6px; align-items:center; margin-top:8px; flex-wrap:wrap; }
.chip { border:1px solid var(--grid); border-radius:7px; padding:2px 9px; font-size:12.5px; font-variant-numeric:tabular-nums; }
.chip b { color:var(--muted); margin-right:5px; font-weight:600; }
.chip.hot { border-color:var(--gold); background:var(--gold-bg); font-weight:700; }
.src { margin-left:auto; }
.more { margin-top:10px; border-top:1px dashed var(--grid); padding-top:8px; }
.more > summary { cursor:pointer; font-size:12.5px; font-weight:600; color:var(--accent); list-style:none; }
.more > summary::-webkit-details-marker { display:none; }
.more > summary::before { content:"＋ "; }
.more[open] > summary::before { content:"－ "; }
.dot { font-size:10.5px; font-weight:600; color:var(--ink2); background:var(--surface2); border:1px solid var(--grid);
  border-radius:999px; padding:0 6px; margin-left:4px; }
.analysis { font-size:13px; color:var(--ink2); line-height:1.55; margin:8px 0 0; }
.basis { font-size:11px; color:var(--muted); margin:8px 0 0; line-height:1.45; }
.info { font-size:12.5px; color:var(--ink2); margin-top:8px; display:flex; flex-direction:column; gap:2px; }
.info b { color:var(--ink); font-weight:600; }
.info i { font-style:normal; color:var(--muted); }
.info a { display:block; }
.value-note { display:flex; gap:8px; margin-top:8px; font-size:12.5px; background:var(--gold-bg);
  border-radius:9px; padding:7px 10px; color:var(--ink2); }
.unc { font-size:11.5px; color:var(--ink2); border:1px dashed var(--border); border-radius:7px; padding:4px 8px; margin-bottom:8px; }
table.mini { width:100%; border-collapse:collapse; margin-top:2px; }
table.mini td { padding:3px 4px; border-top:1px solid var(--grid); }
.num { text-align:right; font-variant-numeric:tabular-nums; }
.nowrap { white-space:nowrap; }

/* Bloecke & Tabellen */
.block { margin-top:28px; }
.block > p { margin:8px 0; }
.tablewrap { overflow-x:auto; margin-top:10px; border-radius:12px; border:1px solid var(--border); background:var(--surface); }
.tbl { width:100%; border-collapse:collapse; font-size:13px; }
.tbl th { text-align:left; padding:8px 10px; color:var(--muted); font-weight:600; font-size:11.5px;
  text-transform:uppercase; letter-spacing:.3px; border-bottom:1px solid var(--grid); white-space:nowrap; }
.tbl th.num { text-align:right; }
.tbl td { padding:8px 10px; border-bottom:1px solid var(--grid); vertical-align:top; }
.tbl tr:last-child td { border-bottom:0; }
.vrow { cursor:pointer; } .vrow:hover td { background:var(--surface2); }
.vrow.over { opacity:.5; }
.edge { position:relative; min-width:64px; }
.edgebar { position:absolute; right:10px; bottom:6px; height:3px; border-radius:2px; background:var(--gold); opacity:.7; }
.empty { margin:22px 0; color:var(--muted); text-align:center; padding:30px; border:1px dashed var(--border); border-radius:14px; }

/* Bilanz */
.tiles { display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:10px; margin:12px 0; }
.tile { background:var(--surface); border:1px solid var(--border); border-radius:14px; padding:12px 14px; box-shadow:var(--shadow); }
.tile.gold { background:var(--gold-bg); }
.tval { font-family:var(--num); font-size:34px; font-weight:700; line-height:1; }
.tunit { font-size:18px; color:var(--ink2); }
.tlab { font-size:12.5px; font-weight:600; margin-top:4px; }
.tsub { font-size:11.5px; color:var(--muted); margin-top:1px; }
.calwrap { background:var(--surface); border:1px solid var(--border); border-radius:14px; padding:12px 14px; margin-top:10px; }
.calwrap h3 { font-size:14px; }
.calwrap .tablewrap { border:0; }
.caltbl { width:100%; border-collapse:collapse; font-size:13px; }
.caltbl th { text-align:left; font-weight:600; padding:6px 8px; white-space:nowrap; color:var(--ink2); font-size:12.5px; }
.caltbl thead th { color:var(--muted); font-size:11.5px; text-transform:uppercase; }
.calcell { padding:6px 8px; min-width:170px; }
.calbar { position:relative; height:10px; background:var(--surface2); border-radius:5px; }
.calfill { height:100%; border-radius:5px; }
.calfill.ok { background:var(--accent); } .calfill.over { background:var(--home); } .calfill.under { background:var(--bad); }
.calmark { position:absolute; top:-3px; bottom:-3px; width:2px; background:var(--ink); border-radius:1px; }
.calnum { font-size:12.5px; }
.lg { display:inline-block; font-size:11px; padding:0 6px; border-radius:999px; color:#fff; margin-left:4px; }
.lg.l-ok { background:var(--accent); } .lg.l-over { background:var(--home); } .lg.l-under { background:var(--bad); }
.trend { display:flex; gap:4px; height:110px; align-items:flex-end; margin-top:10px; position:relative; padding-bottom:16px; }
.trend::before { content:""; position:absolute; left:0; right:0; bottom:calc(16px + 47px); border-top:1px dashed var(--muted); z-index:1; opacity:.6; }
.tb { flex:1; height:94px; display:flex; flex-direction:column; justify-content:flex-end; position:relative; }
.tbf { background:var(--accent); border-radius:4px 4px 0 0; min-height:3px; }
.tb span { position:absolute; bottom:-16px; left:0; right:0; text-align:center; font-size:10px; color:var(--muted); }
.tb.empty .tbf { display:none; }
details.sub { margin-top:10px; } details.sub > summary { cursor:pointer; color:var(--accent); font-weight:600; font-size:13px; }
.ok { color:var(--good); font-weight:700; } .bad { color:var(--bad); font-weight:700; }

/* Live */
.livedot { width:9px; height:9px; border-radius:50%; background:var(--bad); box-shadow:0 0 0 0 var(--bad); animation:pulse 1.6s infinite; }
@keyframes pulse { 0% { box-shadow:0 0 0 0 rgba(220,61,61,.6);} 70% { box-shadow:0 0 0 8px rgba(220,61,61,0);} 100% { box-shadow:0 0 0 0 rgba(220,61,61,0);} }
.livegrid { display:grid; grid-template-columns:repeat(auto-fill,minmax(300px,1fr)); gap:8px; margin-top:10px; }
.liveitem { background:var(--surface); border:1px solid var(--border); border-radius:12px; padding:8px 12px; font-size:13px; }
.banner { background:var(--surface); border:1px solid var(--accent); border-radius:12px; padding:9px 13px;
  font-size:13px; color:var(--ink2); margin:14px 0 0; }
.banner.click { cursor:pointer; }

footer { max-width:1180px; margin:0 auto; padding:18px 16px 30px; color:var(--muted); font-size:12px; }
footer details { margin-bottom:10px; color:var(--ink2); }
footer summary { cursor:pointer; font-weight:600; }
.disclaimer { border-top:1px solid var(--grid); padding-top:10px; margin-top:10px; }
.muted { color:var(--muted); } .small { font-size:12.5px; } .tiny { font-size:11.5px; }

@media (max-width: 640px) {
  .hero { padding:14px 14px 10px; }
  h1 { font-size:24px; }
  .logo { width:36px; height:36px; font-size:20px; }
  .kpis { width:100%; }
  .kpi { flex:1; min-width:0; padding:5px 4px; }
  .kpi b { font-size:19px; }
  .barin { padding:8px 12px 6px; }
  .tab { padding:6px 8px; }
  .tab .tabsub { display:none; }
  .search { flex:1 1 100%; }
  main { padding:4px 12px 30px; }
  .grid { grid-template-columns:1fr; }
  .card { padding:11px 12px; }
  html { scroll-padding-top:190px; }
}
</style>
</head>
<body>"""


SCRIPT = r"""
const $ = (s, el) => (el || document).querySelector(s);
const $$ = (s, el) => [...(el || document).querySelectorAll(s)];
const store = {
  get(k, d) { try { const v = localStorage.getItem('sr_' + k); return v === null ? d : JSON.parse(v); } catch (e) { return d; } },
  set(k, v) { try { localStorage.setItem('sr_' + k, JSON.stringify(v)); } catch (e) {} }
};

// ---- Alter des Datenstands
(function () {
  const min = Math.round((Date.now() - new Date(GEN).getTime()) / 60000);
  const el = $('#age');
  if (!el || isNaN(min) || min < 0) return;
  el.textContent = min < 60 ? '(vor ' + min + ' Min.)' :
    min < 48 * 60 ? '(vor ' + Math.round(min / 60) + ' Std.)' : '(vor ' + Math.round(min / 1440) + ' Tagen)';
})();

// ---- Anstoß-Status (in X Std. / läuft / beendet)
function zeitStatus() {
  const now = Date.now();
  $$('.card[data-ko]').forEach(c => {
    const ko = new Date(c.dataset.ko).getTime();
    const st = $('.state', c);
    const mins = (ko - now) / 60000;
    const dur = c.dataset.sport === 'fb' ? 115 : 150;
    c.classList.remove('over');
    st.className = 'state';
    if (mins > 0 && mins < 60) { st.textContent = 'in ' + Math.round(mins) + ' Min.'; st.classList.add('soon'); }
    else if (mins >= 60 && mins < 12 * 60) { st.textContent = 'in ' + Math.round(mins / 60) + ' Std.'; st.classList.add('soon'); }
    else if (mins <= 0 && mins > -dur) { st.textContent = c.dataset.sport === 'fb' ? 'läuft' : 'begonnen'; st.classList.add('live'); }
    else if (mins <= -dur) { st.textContent = 'vorbei'; st.classList.add('done'); c.classList.add('over'); }
    else st.textContent = '';
  });
  $$('.vrow[data-ko]').forEach(r => r.classList.toggle('over', new Date(r.dataset.ko).getTime() < now));
}
zeitStatus();
setInterval(zeitStatus, 60000);

// ---- Favoriten (Teams/Spieler)
let favs = new Set(store.get('favs', []));
function favRender() {
  $$('.star').forEach(b => { const on = favs.has(b.dataset.name); b.classList.toggle('on', on); b.textContent = on ? '★' : '☆'; });
  $$('.card').forEach(c => c.classList.toggle('fav', c.dataset.names.split('|').some(n => favs.has(n))));
  const fb = $('.flt[data-f="fav"]');
  if (fb) fb.textContent = '★ Favoriten' + (favs.size ? ' (' + $$('.daypanel.active .card.fav').length + ')' : '');
}
$$('.star').forEach(b => b.addEventListener('click', e => {
  e.stopPropagation();
  const n = b.dataset.name;
  favs.has(n) ? favs.delete(n) : favs.add(n);
  store.set('favs', [...favs]);
  favRender(); anwenden();
}));

// ---- Filter & Suche
let filt = store.get('filter', 'alle');
function anwenden() {
  const q = ($('#q').value || '').trim().toLowerCase();
  $$('.daypanel').forEach(p => {
    let sichtbar = 0;
    $$('.league', p).forEach(sec => {
      const catOk = filt === 'alle' || filt === 'value' || filt === 'fav' || sec.dataset.cat === filt;
      let n = 0;
      const cards = $$('.card', sec);
      cards.forEach(c => {
        const ok = catOk && (!q || c.dataset.search.includes(q)) &&
          (filt !== 'value' || c.classList.contains('has-value')) &&
          (filt !== 'fav' || c.classList.contains('fav'));
        c.hidden = !ok; if (ok) n++;
      });
      const showSec = cards.length ? n > 0 : (catOk && !q && filt !== 'value' && filt !== 'fav');
      sec.hidden = !showSec;
      if (showSec) { sichtbar++; if (q || filt === 'value' || filt === 'fav') sec.open = true; }
    });
    const hl = $('.highlights', p); if (hl) hl.hidden = !!q || filt === 'fav';
    const nohit = $('.nohit', p); if (nohit) nohit.hidden = sichtbar > 0 || !$$('.league', p).length;
  });
  $$('.flt[data-f]').forEach(x => x.classList.toggle('active', x.dataset.f === filt));
}
$$('.flt[data-f]').forEach(b => b.addEventListener('click', () => {
  filt = b.dataset.f; store.set('filter', filt); anwenden();
}));
$('#q').addEventListener('input', anwenden);

// ---- Tage
function zeigeTag(i) {
  $$('.tab').forEach(x => x.classList.toggle('active', x.dataset.day === String(i)));
  $$('.daypanel').forEach(x => x.classList.toggle('active', x.dataset.day === String(i)));
  favRender();
}
$$('.tab').forEach(t => t.addEventListener('click', () => zeigeTag(t.dataset.day)));

// ---- Sprung zur Karte (Highlights & Value-Liste)
function springe(cid, day) {
  const el = document.getElementById(cid);
  if (!el) return;
  const panel = el.closest('.daypanel');
  zeigeTag(day != null ? day : panel.dataset.day);
  if (el.hidden) { filt = 'alle'; $('#q').value = ''; anwenden(); }
  const sec = el.closest('details.league'); if (sec) sec.open = true;
  el.scrollIntoView({ behavior: 'smooth', block: 'center' });
  el.classList.add('flash'); setTimeout(() => el.classList.remove('flash'), 2500);
}
$$('.jump').forEach(r => r.addEventListener('click', () => springe(r.dataset.cid, r.dataset.day)));

favRender();
anwenden();

// ---- Neuere Version verfügbar?
fetch('https://raw.githubusercontent.com/BLSports/blsports.github.io/main/data/data.json', { cache: 'no-store' })
  .then(r => r.json())
  .then(d => {
    if (d.generatedAt && d.generatedAt > GEN) {
      const b = document.createElement('div');
      b.className = 'banner click';
      b.innerHTML = '🔄 <b>Neuere Daten verfügbar</b> – hier tippen zum Aktualisieren';
      b.onclick = () => location.replace(location.pathname + '?v=' + Date.now());
      $('main').prepend(b);
    }
  }).catch(() => {});

// ---- Live-Box
const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
async function ladeLive() {
  try {
    const r = await fetch('https://raw.githubusercontent.com/BLSports/blsports.github.io/main/data/live.json?v=' + Date.now(), { cache: 'no-store' });
    if (!r.ok) return;
    const d = await r.json();
    const box = $('#livebox'), body = $('#livebody');
    const alterMin = (Date.now() - new Date(d.updated).getTime()) / 60000;
    if (!d.updated || alterMin > 40) { box.hidden = true; return; }
    const rows = [];
    for (const m of (d.football || [])) {
      const odds = m.odds ? `<div class="oddsrow"><span class="chip"><b>1</b>${m.odds.h.toFixed(2)}</span>` +
        `<span class="chip"><b>X</b>${m.odds.d.toFixed(2)}</span><span class="chip"><b>2</b>${m.odds.a.toFixed(2)}</span></div>` : '';
      const val = m.value ? `<div class="value-note"><span class="gem">💎</span><div>Live-Value: <b>${esc(m.value.name)}</b> ` +
        `(Quote ${m.value.odds.toFixed(2)}, +${Math.round(m.value.edge * 100)} Pp.)</div></div>` : '';
      rows.push(`<div class="liveitem"><span class="muted tiny">⚽ ${esc(m.league)} · <b class="bad">${esc(m.minute)}′</b></span>` +
        `<div><b>${esc(m.home)} ${esc(m.score)} ${esc(m.away)}</b></div>${odds}${val}</div>`);
    }
    for (const t of (d.tennis || []).slice(0, 20)) {
      rows.push(`<div class="liveitem"><span class="muted tiny">🎾 ${esc(t.tour)} · ${esc(t.tournament)}</span>` +
        `<div><b>${esc(t.p1)} – ${esc(t.p2)}</b> <span class="muted">Sätze: ${esc(t.sets)}</span></div></div>`);
    }
    if (rows.length) {
      body.innerHTML = rows.join('');
      const upd = new Date(d.updated);
      $('#liveinfo').textContent = '(' + rows.length + ' laufend · Stand ' +
        upd.toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' }) + ' Uhr)';
      box.hidden = false;
    } else box.hidden = true;
  } catch (e) {}
}
ladeLive();
setInterval(ladeLive, 90000);

// ---- Live-Status je Spiel (ESPN)
$$('.livebtn').forEach(btn => btn.addEventListener('click', async e => {
  e.stopPropagation();
  const s = btn.dataset;
  const base = s.sport === 'fb' ? 'soccer/' + s.slug : 'tennis/' + s.slug;
  btn.textContent = '⏳';
  try {
    const r = await fetch('https://site.api.espn.com/apis/site/v2/sports/' + base + '/scoreboard?dates=' + s.date, { cache: 'no-store' });
    const d = await r.json();
    const la = s.a.toLowerCase().split(' ').pop(), lb = s.b.toLowerCase().split(' ').pop();
    let hit = null;
    for (const ev of (d.events || [])) {
      const comps = [...(ev.competitions || [])];
      (ev.groupings || []).forEach(g => comps.push(...(g.competitions || [])));
      for (const c of comps) {
        const txt = JSON.stringify(c.competitors || []).toLowerCase();
        if (txt.includes(la) && txt.includes(lb)) { hit = c; break; }
      }
      if (hit) break;
    }
    if (!hit) { btn.textContent = '📡 kein Eintrag'; return; }
    const st = (hit.status && hit.status.type && (hit.status.type.shortDetail || hit.status.type.description)) || '?';
    let sc = (hit.competitors || []).map(c => c.score != null ? c.score : '').join(':');
    if (sc === ':' || sc === '') sc = '';
    btn.textContent = '📡 ' + st + (sc ? ' · ' + sc : '');
  } catch (err) { btn.textContent = '📡 nicht abrufbar'; }
}));
"""


if __name__ == "__main__":
    import sys
    build(sys.argv[1] if len(sys.argv) > 1 else None,
          sys.argv[2] if len(sys.argv) > 2 else None)

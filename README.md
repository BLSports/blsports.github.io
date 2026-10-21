# ⚽ Sport-Radar 🎾

Ein selbst gehostetes Analyse-Dashboard: zeigt **alle Spiele der nächsten 3 Tage** mit
Formkurven, Tabellenplätzen, Modell-Vorhersagen (Poisson), Quoten-Vergleich und
Tennis-Einschätzungen — **täglich automatisch aktualisiert, komplett kostenlos**.

## Abgedeckte Wettbewerbe

| Fußball | Tennis |
|---|---|
| 1. Bundesliga, 2. Bundesliga, 3. Liga | ATP Tour |
| Serie A, Premier League | WTA Tour |
| La Liga, La Liga 2 (Segunda División) | |

## Wie es funktioniert

```
scripts/fetch_data.py   holt Spielpläne, Ergebnisse, Quoten, Rankings  ->  data/data.json
scripts/build_site.py   rendert daraus das Dashboard                  ->  docs/index.html
.github/workflows/update.yml   führt beides täglich um ~06:00 Uhr aus und pusht das Ergebnis
```

GitHub Pages liefert `index.html` (Repo-Wurzel) als öffentliche Website aus — der Link ist mit
Freunden teilbar.

**Datenquellen (alle gratis):** OpenLigaDB (1.–3. Bundesliga), ESPN (PL, Serie A, La Liga 1+2,
Tennis-Matches & Weltranglisten), football-data.co.uk (Quoten + Ergebnis-Historie),
TheSportsDB (Tennis-Ergänzung). Keine API-Keys nötig.

**Optional:** Ein kostenloser API-Key von [The Odds API](https://the-odds-api.com)
(500 Credits/Monat) ergänzt Quoten für die 3. Liga und Tennis. Dazu im Repo unter
*Settings → Secrets and variables → Actions* ein Secret `ODDS_API_KEY` anlegen — mehr nicht.

## Einrichtung (einmalig, ~5 Minuten)

1. Neues **öffentliches** GitHub-Repository anlegen (z. B. `sport-radar`) und diese Dateien pushen.
2. **Settings → Pages**: Source = *Deploy from a branch*, Branch = `main`, Ordner = `/docs`.
3. **Actions-Tab**: Workflow „Tägliches Daten-Update“ einmal manuell starten (*Run workflow*).
4. Fertig — die Seite liegt unter `https://blsports.github.io/` und aktualisiert
   sich jeden Morgen selbst.

## 📱 Echte iPhone-App (Swift)

Unter `ios/` liegt eine native iPhone-App (SwiftUI, ab iOS 17). Sie liest dieselben Daten wie die
Website (`data/data.json`, `data/live.json`) und bietet:

- Tabs **Spiele** (3 Tage, Filter, Suche), **Tipps** (sicherste Tipps, Value, Torspiele), **Live** und **Bilanz**
- Detailansicht je Spiel: Wahrscheinlichkeiten, xG, Quoten, Form, direkte Duelle, Torschützen, Ausfälle, News
- **Favoriten** (☆ bei Team/Spieler), **Erinnerung** 🔔 15 Minuten vor Anpfiff, Teilen
- Offline-Cache, Nach-unten-ziehen zum Aktualisieren, Dark Mode, iPad

**Gebaut wird automatisch in der Cloud:** `.github/workflows/ios.yml` erzeugt auf einem Mac-Runner
eine `.ipa`-Datei (Kontrolle, dass alles kompiliert, plus Screenshots aus dem iPhone-Simulator).

### Installation ohne Entwicklerkonto (kostenlos, mit Xcode auf dem Mac)

Nur Apple-Software, keine Zusatzprogramme, die Apple-ID bleibt bei Apple.
Mit einer normalen (kostenlosen) Apple-ID läuft die App jeweils **7 Tage** und wird dann per Klick erneuert.

**Einmalig einrichten:**
1. **Xcode** aus dem Mac App Store installieren (kostenlos, ca. 10 GB) und einmal starten.
   Unter *Xcode → Settings → Accounts* mit „+“ die eigene Apple-ID hinzufügen.
2. Dieses Repository als ZIP laden: [Download ZIP](https://github.com/BLSports/blsports.github.io/archive/refs/heads/main.zip),
   entpacken und **`ios/SportRadar.xcodeproj`** doppelklicken.
3. In Xcode links oben auf **SportRadar** (blaues Symbol) → Reiter **Signing & Capabilities** →
   bei **Team** die eigene Apple-ID („Personal Team“) wählen.
4. iPhone per Kabel anschließen, entsperren und „Diesem Computer vertrauen“ bestätigen.
   Oben in der Xcode-Leiste das iPhone als Ziel wählen und **▶︎** klicken.
5. Auf dem iPhone, beim ersten Mal:
   *Einstellungen → Datenschutz & Sicherheit → **Entwicklermodus*** einschalten (Neustart) und
   *Einstellungen → Allgemein → **VPN & Geräteverwaltung*** → der eigenen Apple-ID vertrauen.

**Alle 7 Tage:** iPhone anschließen, Xcode öffnen, **▶︎** klicken – fertig (Favoriten bleiben erhalten).
Für eine neue App-Version vorher die ZIP-Datei neu laden.

### Mit Apple-Entwicklerkonto (99 €/Jahr)

Dann kann der Workflow die App signieren und automatisch zu **TestFlight** hochladen – ohne 7-Tage-Grenze
und ohne PC. Dafür werden einige Schlüssel als GitHub-Secrets benötigt (wird bei Bedarf ergänzt).

### Für Entwickler

`ios/SportRadar.xcodeproj` wird vom Workflow automatisch aus `ios/project.yml` erzeugt
(XcodeGen). Projektänderungen also in `project.yml` vornehmen.

## 📱 Als Web-App aufs iPhone

Das Dashboard ist eine installierbare Web-App (PWA) – kein App Store, kein Mac nötig:

1. `https://blsports.github.io/` in **Safari** öffnen.
2. Unten auf **Teilen** (Quadrat mit Pfeil) tippen → **„Zum Home-Bildschirm“** → *Hinzufügen*.
3. Sport-Radar startet ab jetzt wie eine normale App: eigenes Icon, Vollbild ohne Safari-Leisten.

In der App:
- **Nach unten ziehen** oder **↻** oben rechts lädt den neuesten Stand.
- Kommt man nach > 20 Minuten zurück in die App, werden neue Daten automatisch geladen.
- **Offline** (Flugmodus, Funkloch) bleibt der zuletzt geladene Stand lesbar.
- Notch/Dynamic Island, Querformat und Dark Mode werden berücksichtigt.

Technik: `manifest.webmanifest`, `sw.js` (Service Worker, Offline-Cache) und `icons/`
(erzeugt mit `python scripts/make_icons.py`) liegen in der Repo-Wurzel; die iOS-Meta-Tags
und das App-Verhalten stecken in `scripts/build_site.py`.

## Vorhersage-Modell (Kurzfassung)

- **Fußball:** Poisson-Modell. Angriffs-/Abwehrstärke je Team aus den Ergebnissen der letzten
  zwei Saisons, exponentiell gewichtet (neuere Spiele zählen mehr), plus Heimvorteil der Liga.
  Ergibt Wahrscheinlichkeiten für Sieg/Unentschieden/Niederlage, erwartete Tore und die
  Über-2,5-Tore-Quote. „Value“ wird markiert, wenn das Modell ≥ 5 Prozentpunkte über der
  impliziten Buchmacher-Wahrscheinlichkeit liegt.
- **Tennis:** Ranglisten-basiert: P(Sieg Spieler 1) = R2^0,85 / (R1^0,85 + R2^0,85).
  Ohne bekanntes Ranking wird konservativ Rang 250 angenommen.

## Lokal testen

```bash
python scripts/fetch_data.py     # braucht Internetzugang
python scripts/build_site.py
open docs/index.html
```

`scripts/make_demo.py` erzeugt zusätzlich Beispieldaten (`docs/demo.html`), um das Layout
ohne Live-Daten zu prüfen.

---

*Privates Statistik-Projekt, keine Wettempfehlung. Glücksspiel kann süchtig machen (18+).*

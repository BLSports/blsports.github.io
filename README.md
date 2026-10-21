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
eine `.ipa`-Datei. Die aktuelle Version liegt immer unter
[Releases → ios-latest](https://github.com/BLSports/blsports.github.io/releases/tag/ios-latest).

### Installation ohne Entwicklerkonto (kostenlos, alle 7 Tage erneuern)

Apple erlaubt mit einer normalen Apple-ID nur Apps, die alle 7 Tage neu signiert werden.

**Variante A – AltStore (erneuert automatisch im WLAN):**
1. Auf dem PC/Mac **AltServer** von [altstore.io](https://altstore.io) installieren (Windows: zusätzlich iTunes und iCloud *von apple.com*, nicht aus dem Microsoft Store).
2. iPhone per Kabel anschließen, im AltServer-Symbol „Install AltStore“ → iPhone wählen, mit Apple-ID anmelden.
3. Auf dem iPhone: *Einstellungen → Allgemein → VPN & Geräteverwaltung* → deiner Apple-ID vertrauen;
   *Einstellungen → Datenschutz & Sicherheit → Entwicklermodus* einschalten (Neustart).
4. `SportRadar.ipa` aus dem Release auf dem iPhone in Safari laden → *Teilen → AltStore* (oder in AltStore unter *My Apps* auf „+“).
5. Solange AltServer auf dem PC läuft und das iPhone im selben WLAN ist, erneuert AltStore die App von selbst.

**Variante B – Sideloadly (einfach, Erneuern per Klick):**
1. [Sideloadly](https://sideloadly.io) auf PC/Mac installieren, iPhone per Kabel anschließen.
2. `SportRadar.ipa` ins Fenster ziehen, Apple-ID eintragen, *Start*.
3. Auf dem iPhone wie oben der Apple-ID vertrauen und den Entwicklermodus einschalten.
4. Alle 7 Tage *Start* erneut klicken (ca. 1 Minute; Favoriten bleiben erhalten).

### Mit Apple-Entwicklerkonto (99 €/Jahr)

Dann kann der Workflow die App signieren und automatisch zu **TestFlight** hochladen – ohne 7-Tage-Grenze
und ohne PC. Dafür werden einige Schlüssel als GitHub-Secrets benötigt (wird bei Bedarf ergänzt).

### Lokal mit Xcode

```bash
brew install xcodegen
cd ios && xcodegen generate && open SportRadar.xcodeproj
```

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

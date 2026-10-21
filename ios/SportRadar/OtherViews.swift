import SwiftUI

// MARK: Tipps

struct TipsView: View {
    @Environment(AppStore.self) private var store
    @State private var dayIndex = 0

    private var day: String {
        let days = store.days
        guard !days.isEmpty else { return "" }
        return days[min(dayIndex, days.count - 1)]
    }

    var body: some View {
        NavigationStack {
            List {
                if store.days.count > 1 {
                    Picker("Tag", selection: $dayIndex) {
                        ForEach(Array(store.days.enumerated()), id: \.offset) { i, d in
                            Text(Fmt.dayLabel(d, index: i)).tag(i)
                        }
                    }
                    .pickerStyle(.segmented)
                    .listRowInsets(EdgeInsets())
                    .listRowBackground(Color.clear)
                }

                let safest = store.safestTips(day: day)
                if !safest.isEmpty {
                    Section {
                        ForEach(safest) { t in
                            NavigationLink(value: t.match.id) {
                                TipRow(p: t.p, tint: .accentColor, title: t.pick,
                                       subtitle: "\(Fmt.time(t.match.date)) · \(t.match.title)",
                                       trailing: nil)
                            }
                        }
                    } header: {
                        Label("Sicherste Tipps", systemImage: "scope")
                    }
                }

                let values = store.valueTips(day: day)
                if !values.isEmpty {
                    Section {
                        ForEach(values) { m in
                            NavigationLink(value: m.id) {
                                TipRow(p: m.value?.modelP, tint: .gold, title: valueName(m),
                                       subtitle: "\(Fmt.time(m.date)) · \(m.title)",
                                       trailing: m.value.map { "Quote \(Fmt.num($0.odds, digits: 2)) · +\(Int(($0.edge * 100).rounded()))" })
                            }
                        }
                    } header: {
                        Label("Value-Signale", systemImage: "diamond")
                    } footer: {
                        Text("Value = Modell schätzt ein Ergebnis deutlich wahrscheinlicher ein als die Quote. Statistisches Signal mit Unsicherheit, keine Wettempfehlung.")
                    }
                }

                let goals = store.goalGames(day: day)
                if !goals.isEmpty {
                    Section {
                        ForEach(goals, id: \.id) { m in
                            NavigationLink(value: m.id) {
                                TipRow(p: m.prediction?.pOver25, tint: .good, title: "\(m.home) – \(m.away)",
                                       subtitle: "\(Fmt.time(m.date)) · xG gesamt \(Fmt.num((m.prediction?.xgHome ?? 0) + (m.prediction?.xgAway ?? 0)))",
                                       trailing: nil)
                            }
                        }
                    } header: {
                        Label("Torreiche Spiele (Über 2,5)", systemImage: "flame")
                    }
                }
            }
            .navigationTitle("Tipps")
            .refreshable { await store.refresh() }
            .navigationDestination(for: String.self) { MatchDetailView(matchID: $0) }
            .overlay {
                if store.data != nil && store.safestTips(day: day).isEmpty && store.valueTips(day: day).isEmpty {
                    ContentUnavailableView("Noch keine Tipps", systemImage: "scope",
                                           description: Text("Für diesen Tag liegen noch keine Vorhersagen vor."))
                }
            }
        }
    }

    private func valueName(_ m: AnyMatch) -> String {
        guard let v = m.value else { return "" }
        if let n = v.name { return n }
        if case .football(let f, _) = m {
            switch v.outcome {
            case "1": return f.home
            case "2": return f.away
            default: return "Unentschieden"
            }
        }
        return ""
    }
}

private struct TipRow: View {
    let p: Double?
    let tint: Color
    let title: String
    let subtitle: String
    let trailing: String?

    var body: some View {
        HStack(spacing: 12) {
            Text(p.map { Fmt.pctShort($0) } ?? "–")
                .font(.system(.title3, design: .rounded).weight(.bold).monospacedDigit())
                .foregroundStyle(tint)
                .frame(minWidth: 52, alignment: .leading)
            VStack(alignment: .leading, spacing: 2) {
                Text(title).font(.body.weight(.semibold)).lineLimit(1)
                Text(subtitle).font(.caption).foregroundStyle(.secondary).lineLimit(1)
            }
            Spacer(minLength: 4)
            if let trailing {
                Text(trailing).font(.caption2).foregroundStyle(.secondary)
                    .padding(.horizontal, 7).padding(.vertical, 2)
                    .background(Color(.tertiarySystemFill), in: Capsule())
            }
        }
    }
}

// MARK: Live

struct LiveView: View {
    @Environment(AppStore.self) private var store

    var body: some View {
        NavigationStack {
            List {
                if store.liveIsFresh, let live = store.live {
                    if !live.football.isEmpty {
                        Section("Fußball") {
                            ForEach(live.football) { m in
                                VStack(alignment: .leading, spacing: 6) {
                                    HStack {
                                        Text(m.league).font(.caption).foregroundStyle(.secondary)
                                        Spacer()
                                        if let min = m.minute {
                                            Text("\(min)′").font(.caption.weight(.bold)).foregroundStyle(Color.bad)
                                        }
                                    }
                                    HStack {
                                        Text(m.home).font(.body.weight(.semibold)).lineLimit(1)
                                        Spacer()
                                        Text(m.score).font(.system(.title3, design: .rounded).weight(.bold).monospacedDigit())
                                        Spacer()
                                        Text(m.away).font(.body.weight(.semibold)).lineLimit(1)
                                    }
                                    if let o = m.odds {
                                        HStack(spacing: 6) {
                                            OddsChip(label: "1", odds: o.h, hot: m.value?.outcome == "1")
                                            OddsChip(label: "X", odds: o.d, hot: m.value?.outcome == "X")
                                            OddsChip(label: "2", odds: o.a, hot: m.value?.outcome == "2")
                                        }
                                    }
                                    if let v = m.value {
                                        Label("Live-Value: \(v.name ?? v.outcome ?? "") (Quote \(Fmt.num(v.odds, digits: 2)), +\(Int((v.edge * 100).rounded())) Pp.)",
                                              systemImage: "diamond.fill")
                                            .font(.footnote).foregroundStyle(Color.gold)
                                    }
                                }
                                .padding(.vertical, 2)
                            }
                        }
                    }
                    if !live.tennis.isEmpty {
                        Section("Tennis") {
                            ForEach(live.tennis) { t in
                                VStack(alignment: .leading, spacing: 4) {
                                    Text("\(t.tour) · \(t.tournament)").font(.caption).foregroundStyle(.secondary)
                                    let sets = t.sets.components(separatedBy: " | ")
                                    LiveTennisLine(name: t.p1, sets: sets.first ?? "")
                                    LiveTennisLine(name: t.p2, sets: sets.count > 1 ? sets[1] : "")
                                }
                                .padding(.vertical, 2)
                            }
                        }
                    }
                }
            }
            .navigationTitle("Live")
            .refreshable { await store.refreshLive() }
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    if let d = store.live?.updatedDate, store.liveIsFresh {
                        Text("Stand \(d.formatted(date: .omitted, time: .shortened))").font(.caption).foregroundStyle(.secondary)
                    }
                }
            }
            .overlay {
                if store.liveCount == 0 {
                    ContentUnavailableView("Gerade läuft nichts", systemImage: "dot.radiowaves.left.and.right",
                                           description: Text("Laufende Spiele erscheinen hier automatisch. Der Live-Ticker wird alle 15 Minuten aktualisiert."))
                }
            }
            .task {
                // solange der Tab sichtbar ist, jede Minute nachladen
                while !Task.isCancelled {
                    await store.refreshLive()
                    try? await Task.sleep(for: .seconds(60))
                }
            }
        }
    }
}

private struct LiveTennisLine: View {
    let name: String
    let sets: String

    var body: some View {
        HStack {
            Text(name).font(.body.weight(.semibold)).lineLimit(1)
            Spacer()
            HStack(spacing: 8) {
                ForEach(Array(sets.split(separator: "-").enumerated()), id: \.offset) { _, s in
                    Text(String(s)).monospacedDigit().frame(minWidth: 14)
                }
            }
            .font(.system(.body, design: .rounded).weight(.semibold))
        }
    }
}

// MARK: Bilanz

struct StatsView: View {
    @Environment(AppStore.self) private var store
    @State private var showInfo = false

    var body: some View {
        NavigationStack {
            List {
                if let s = store.data?.stats {
                    Section {
                        LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 10) {
                            if let o = s.overall { StatTile(title: "Trefferquote gesamt", value: Fmt.pct(o.pct), sub: "\(o.correct) von \(o.n) Tipps") }
                            if let f = s.football { StatTile(title: "Fußball (1X2)", value: Fmt.pct(f.pct), sub: "\(f.correct) von \(f.n)") }
                            if let t = s.tennis { StatTile(title: "Tennis", value: Fmt.pct(t.pct), sub: "\(t.correct) von \(t.n)") }
                            if let e = s.exact { StatTile(title: "Exaktes Ergebnis", value: Fmt.pct(e.pct), sub: "\(e.correct) von \(e.n)") }
                            if let v = s.value, v.n > 0 {
                                StatTile(title: "Value-Signale",
                                         value: (v.units ?? 0) >= 0 ? "+\(Fmt.num(v.units ?? 0)) E" : "\(Fmt.num(v.units ?? 0)) E",
                                         sub: "\(v.correct) von \(v.n) getroffen" + (v.avgOdds.map { " · Ø Quote \(Fmt.num($0, digits: 2))" } ?? ""),
                                         highlight: true)
                            }
                            if let open = s.open { StatTile(title: "Offene Tipps", value: "\(open)", sub: "warten auf Ergebnis") }
                        }
                        .listRowInsets(EdgeInsets())
                        .listRowBackground(Color.clear)
                    } footer: {
                        Text("E = Einheiten Gewinn/Verlust bei 1 Einheit Einsatz pro Value-Signal.")
                    }

                    if let recent = s.recent, !recent.isEmpty {
                        Section("Letzte Ergebnisse") {
                            ForEach(recent) { r in
                                HStack(spacing: 10) {
                                    Image(systemName: r.correct == true ? "checkmark.circle.fill" : (r.correct == false ? "xmark.circle.fill" : "clock"))
                                        .foregroundStyle(r.correct == true ? Color.good : (r.correct == false ? Color.bad : Color.secondary))
                                        .font(.title3)
                                    VStack(alignment: .leading, spacing: 2) {
                                        Text(r.label).font(.subheadline.weight(.semibold)).lineLimit(1)
                                        Text("\(r.sport == "fb" ? "⚽" : "🎾") \(r.comp)").font(.caption).foregroundStyle(.secondary).lineLimit(1)
                                        Text("Tipp: \(r.tipName ?? "–")\(r.prob.map { " (\(Fmt.pctShort($0)))" } ?? "") · \(resultText(r))")
                                            .font(.caption).foregroundStyle(.secondary).lineLimit(1)
                                    }
                                }
                            }
                        }
                    }
                }

                Section {
                    Link(destination: AppStore.websiteURL) {
                        Label("Website öffnen", systemImage: "safari")
                    }
                    Button { showInfo = true } label: {
                        Label("Wie funktionieren die Vorhersagen?", systemImage: "info.circle")
                    }
                }
            }
            .navigationTitle("Bilanz")
            .refreshable { await store.refresh() }
            .sheet(isPresented: $showInfo) { InfoSheet() }
            .overlay {
                if store.data?.stats == nil && store.data != nil {
                    ContentUnavailableView("Noch keine Bilanz", systemImage: "chart.bar")
                }
            }
        }
    }
}

/// "Sieger: P2" -> "Sieger: James Duckworth" (P1/P2 = erster/zweiter Name im Label)
private func resultText(_ r: RecentTip) -> String {
    guard var res = r.result else { return "" }
    let parts = r.label.components(separatedBy: " – ")
    if parts.count == 2 {
        res = res.replacingOccurrences(of: "P1", with: parts[0]).replacingOccurrences(of: "P2", with: parts[1])
    }
    return res
}

private struct StatTile: View {
    let title: String
    let value: String
    let sub: String
    var highlight = false

    var body: some View {
        VStack(alignment: .leading, spacing: 3) {
            Text(value).font(.system(size: 30, weight: .bold, design: .rounded)).monospacedDigit()
                .lineLimit(1).minimumScaleFactor(0.6)
            Text(title).font(.footnote.weight(.semibold))
            Text(sub).font(.caption2).foregroundStyle(.secondary).lineLimit(2)
        }
        .frame(maxWidth: .infinity, minHeight: 96, alignment: .topLeading)
        .padding(12)
        .background(highlight ? Color.gold.opacity(0.14) : Color(.secondarySystemGroupedBackground),
                    in: RoundedRectangle(cornerRadius: 14))
    }
}

struct InfoSheet: View {
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    Group {
                        Text("Fußball").font(.headline)
                        Text("Poisson-Modell auf Basis der Ergebnisse der letzten zwei Saisons (neuere Spiele zählen stärker), inklusive Heimvorteil. Daraus ergeben sich Wahrscheinlichkeiten für 1/X/2, erwartete Tore (xG) und ein wahrscheinlichstes Ergebnis. „Value“ markiert Fälle, in denen das Modell ein Ergebnis deutlich wahrscheinlicher einschätzt als die Buchmacher-Quote.")
                        Text("Tennis").font(.headline)
                        Text("Elo-Formmodell aus rund 24.000 Tour-Matches der letzten fünf Jahre, mit eigenem Rating je Belag, direktem Vergleich und der Weltrangliste als Absicherung bei dünner Datenlage („o. R.“ = ohne Top-Ranking).")
                        Text("Datenquellen").font(.headline)
                        Text("OpenLigaDB, ESPN, football-data.co.uk, tennis-data.co.uk, TheSportsDB. Die Daten werden mehrmals täglich automatisch aktualisiert.")
                    }
                    Text("Keine Wettempfehlung. Quoten dienen nur dem Vergleich mit dem Modell. Glücksspiel kann süchtig machen (18+). Hilfe: bundesweit-gegen-gluecksspielsucht.de")
                        .font(.footnote).foregroundStyle(.secondary)
                }
                .padding()
            }
            .navigationTitle("So rechnet Sport-Radar")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar { ToolbarItem(placement: .confirmationAction) { Button("Fertig") { dismiss() } } }
        }
    }
}

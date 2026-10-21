import SwiftUI

struct MatchesView: View {
    @Environment(AppStore.self) private var store
    @AppStorage("filter") private var filterRaw = MatchFilter.alle.rawValue
    @State private var dayIndex = 0
    @State private var search = ""
    @State private var path: [String] = []

    private var filter: MatchFilter { MatchFilter(rawValue: filterRaw) ?? .alle }

    var body: some View {
        NavigationStack(path: $path) {
            List {
                Section {
                    header
                }
                .listRowInsets(EdgeInsets())
                .listRowBackground(Color.clear)

                content
            }
            .listStyle(.insetGrouped)
            .navigationTitle("Spiele")
            .searchable(text: $search, prompt: "Team, Spieler, Liga …")
            .refreshable { await store.refresh() }
            .navigationDestination(for: String.self) { id in
                MatchDetailView(matchID: id)
            }
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) { StandLabel() }
            }
            .overlay { emptyState }
            .task(id: store.data?.generatedAt) { openDemoDetail() }
        }
    }

    /// Startparameter "-demoDetail YES" (nur für automatische Screenshots): öffnet ein Beispielspiel.
    private func openDemoDetail() {
        guard UserDefaults.standard.bool(forKey: "demoDetail"), path.isEmpty else { return }
        let all = store.days.flatMap { store.allMatches(day: $0) }
        let pick = all.first { m in
            if case .football(let f, _) = m { return f.value != nil && f.prediction != nil && !(f.h2h ?? []).isEmpty }
            return false
        } ?? all.first
        if let pick { path = [pick.id] }
    }

    private var day: String {
        let days = store.days
        guard !days.isEmpty else { return "" }
        return days[min(dayIndex, days.count - 1)]
    }

    @ViewBuilder private var header: some View {
        VStack(spacing: 10) {
            if store.days.count > 1 {
                Picker("Tag", selection: $dayIndex) {
                    ForEach(Array(store.days.enumerated()), id: \.offset) { i, d in
                        Text("\(Fmt.dayLabel(d, index: i)) (\(store.allMatches(day: d).count))").tag(i)
                    }
                }
                .pickerStyle(.segmented)
            }
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 6) {
                    ForEach(MatchFilter.allCases) { f in
                        Button {
                            filterRaw = f.rawValue
                        } label: {
                            Label(f.rawValue, systemImage: f.icon)
                                .font(.subheadline.weight(filter == f ? .semibold : .regular))
                                .padding(.horizontal, 12).padding(.vertical, 6)
                                .foregroundStyle(filter == f ? Color(.systemBackground) : .primary)
                                .background(filter == f ? Color.primary : Color(.secondarySystemGroupedBackground),
                                            in: Capsule())
                        }
                        .buttonStyle(.plain)
                    }
                }
                .padding(.horizontal, 2)
            }
            .sensoryFeedback(.selection, trigger: filterRaw)
            if store.isOffline {
                Label("Offline – zuletzt geladener Stand", systemImage: "wifi.slash")
                    .font(.footnote).foregroundStyle(.secondary)
            }
        }
        .padding(.vertical, 4)
    }

    @ViewBuilder private var content: some View {
        let groups = store.groups(day: day, filter: filter, search: search)
        ForEach(groups) { g in
            Section {
                ForEach(g.matches) { m in
                    NavigationLink(value: m.id) {
                        MatchRow(match: m)
                    }
                }
            } header: {
                HStack {
                    Text(g.title)
                    if let s = g.subtitle { Text("· \(s)").foregroundStyle(.secondary) }
                    Spacer()
                    Text("\(g.matches.count)")
                }
                .textCase(nil)
            }
        }
    }

    @ViewBuilder private var emptyState: some View {
        if store.data == nil {
            if store.isLoading {
                ProgressView("Lade Spiele …")
            } else {
                ContentUnavailableView {
                    Label("Keine Daten", systemImage: "wifi.exclamationmark")
                } description: {
                    Text(store.loadError ?? "Zum Aktualisieren nach unten ziehen.")
                } actions: {
                    Button("Erneut versuchen") { Task { await store.refresh() } }
                        .buttonStyle(.borderedProminent)
                }
            }
        } else if store.groups(day: day, filter: filter, search: search).isEmpty {
            if !search.isEmpty {
                ContentUnavailableView.search(text: search)
            } else if filter == .favoriten {
                ContentUnavailableView("Keine Favoriten-Spiele", systemImage: "star",
                                       description: Text("Markiere Teams oder Spieler in der Detailansicht mit ☆."))
            } else {
                ContentUnavailableView("Keine Spiele", systemImage: "calendar",
                                       description: Text("Für diesen Tag und Filter gibt es keine Spiele."))
            }
        }
    }
}

/// "Stand: vor 3 Std." in der Navigationsleiste.
struct StandLabel: View {
    @Environment(AppStore.self) private var store

    var body: some View {
        if store.isLoading {
            ProgressView()
        } else if let d = store.data?.generatedDate {
            TimelineView(.periodic(from: .now, by: 60)) { _ in
                Text("Stand \(Fmt.ago(d))").font(.caption).foregroundStyle(.secondary)
            }
        }
    }
}

// MARK: Zeilen

struct MatchRow: View {
    @Environment(AppStore.self) private var store
    let match: AnyMatch

    var body: some View {
        TimelineView(.periodic(from: .now, by: 60)) { ctx in
            let state = MatchState(start: match.date, duration: match.duration, now: ctx.date)
            VStack(alignment: .leading, spacing: 8) {
                HStack(spacing: 6) {
                    Text(timeText).font(.system(.headline, design: .rounded).monospacedDigit())
                    StateBadge(state: state)
                    Text(subtitle).font(.caption).foregroundStyle(.secondary).lineLimit(1)
                    Spacer(minLength: 4)
                    if store.hasReminder(match) {
                        Image(systemName: "bell.fill").font(.caption).foregroundStyle(.secondary)
                    }
                    if let v = match.value { ValuePill(edge: v.edge) }
                }
                switch match {
                case .football(let m, _): FootballRowBody(m: m)
                case .tennis(let m): TennisRowBody(m: m)
                }
            }
            .padding(.vertical, 4)
            .opacity(state.kind == .over ? 0.5 : 1)
        }
    }

    private var timeText: String {
        if case .tennis(let t) = match, t.timeTBD == true { return "offen" }
        return Fmt.time(match.date)
    }

    private var subtitle: String {
        switch match {
        case .football(let m, _):
            if let r = m.roundName, !r.isEmpty { return r }
            if let md = m.matchday { return "\(md). Spieltag" }
            return ""
        case .tennis(let m):
            return [m.round, m.isDoubles ? "Doppel" : nil].compactMap { $0 }.joined(separator: " · ")
        }
    }
}

private struct SideLine: View {
    @Environment(AppStore.self) private var store
    let crest: AnyView
    let name: String
    let meta: AnyView
    let p: Double?
    let isTip: Bool

    var body: some View {
        HStack(spacing: 10) {
            crest
            VStack(alignment: .leading, spacing: 2) {
                HStack(spacing: 4) {
                    Text(name).font(.body.weight(.semibold)).lineLimit(1)
                    if store.isFavorite(name: name) {
                        Image(systemName: "star.fill").font(.caption2).foregroundStyle(Color.gold)
                    }
                }
                meta
            }
            Spacer(minLength: 4)
            if let p {
                Text(Fmt.pctShort(p))
                    .font(.system(.title3, design: .rounded).weight(.bold).monospacedDigit())
                    .foregroundStyle(isTip ? .primary : .secondary)
            }
        }
    }
}

struct FootballRowBody: View {
    let m: FootballMatch

    var body: some View {
        let tip = m.tipIndex
        VStack(alignment: .leading, spacing: 6) {
            SideLine(crest: AnyView(Crest(url: m.homeIcon, name: m.home)), name: m.home,
                     meta: AnyView(meta(pos: m.posHome, form: m.formHome)),
                     p: m.prediction?.pHome, isTip: tip == 0)
            SideLine(crest: AnyView(Crest(url: m.awayIcon, name: m.away)), name: m.away,
                     meta: AnyView(meta(pos: m.posAway, form: m.formAway)),
                     p: m.prediction?.pAway, isTip: tip == 2)
            if let p = m.prediction {
                ProbBar.football(p, height: 18)
            } else {
                Text("Keine Modell-Vorhersage (zu wenig Daten)").font(.caption).foregroundStyle(.secondary)
            }
        }
    }

    @ViewBuilder private func meta(pos: Int?, form: [String]?) -> some View {
        HStack(spacing: 6) {
            if let pos { Text("\(pos).").font(.caption2.weight(.semibold)).foregroundStyle(.secondary) }
            if let form, !form.isEmpty { FormBadges(form: form, size: 13) }
        }
    }
}

struct TennisRowBody: View {
    let m: TennisMatch

    var body: some View {
        let p1 = m.pP1
        VStack(alignment: .leading, spacing: 6) {
            SideLine(crest: AnyView(Crest(url: nil, name: m.p1.name, round: true)), name: m.p1.name,
                     meta: AnyView(meta(m.p1)), p: p1, isTip: (p1 ?? 0) >= 0.5)
            SideLine(crest: AnyView(Crest(url: nil, name: m.p2.name, round: true)), name: m.p2.name,
                     meta: AnyView(meta(m.p2)), p: p1.map { 1 - $0 }, isTip: (p1 ?? 1) < 0.5)
            if let p1 { ProbBar.tennis(p1, height: 18) }
            if m.unconfirmed == true {
                Label("Ansetzung unbestätigt", systemImage: "exclamationmark.triangle")
                    .font(.caption).foregroundStyle(.secondary)
            }
        }
    }

    @ViewBuilder private func meta(_ p: TennisPlayer) -> some View {
        HStack(spacing: 6) {
            Text(p.rank.map { "#\($0)" } ?? "o. R.").font(.caption2.weight(.semibold)).foregroundStyle(.secondary)
            if let f = p.form, !f.isEmpty { FormBadges(form: f, size: 13) }
        }
    }
}

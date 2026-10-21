import SwiftUI

struct MatchDetailView: View {
    @Environment(AppStore.self) private var store
    let matchID: String
    @State private var reminderMessage: String?

    var body: some View {
        Group {
            if let m = store.match(id: matchID) {
                ScrollView {
                    VStack(spacing: 12) {
                        switch m {
                        case .football(let f, let l): FootballDetail(m: f, league: l)
                        case .tennis(let t): TennisDetail(m: t)
                        }
                        Text("Statistische Schätzung, keine Wettempfehlung. 18+")
                            .font(.caption2).foregroundStyle(.secondary).padding(.top, 4)
                    }
                    .padding(.horizontal, 16).padding(.bottom, 24)
                }
                .background(Color(.systemGroupedBackground))
                .navigationTitle(m.title)
                .navigationBarTitleDisplayMode(.inline)
                .toolbar {
                    ToolbarItemGroup(placement: .topBarTrailing) {
                        Button {
                            Task { reminderMessage = await store.toggleReminder(m) }
                        } label: {
                            Image(systemName: store.hasReminder(m) ? "bell.fill" : "bell")
                        }
                        .accessibilityLabel(store.hasReminder(m) ? "Erinnerung entfernen" : "15 Min. vorher erinnern")
                        .sensoryFeedback(.success, trigger: store.hasReminder(m))
                        ShareLink(item: shareText(m)) { Image(systemName: "square.and.arrow.up") }
                    }
                }
                .alert("Erinnerung", isPresented: Binding(get: { reminderMessage != nil },
                                                          set: { if !$0 { reminderMessage = nil } })) {
                    Button("OK", role: .cancel) {}
                } message: {
                    Text(reminderMessage ?? "")
                }
            } else {
                ContentUnavailableView("Spiel nicht mehr in den Daten", systemImage: "calendar.badge.exclamationmark")
            }
        }
    }

    private func shareText(_ m: AnyMatch) -> String {
        var s = "\(m.title)\n\(m.competition) · \(Fmt.longDate(m.date))"
        switch m {
        case .football(let f, _):
            if let p = f.prediction, let i = f.tipIndex {
                s += "\nModell: \([f.home, "Unentschieden", f.away][i]) \(Fmt.pct([p.pHome, p.pDraw, p.pAway][i]))"
                if let t = p.tipScore { s += " · Tipp \(t)" }
            }
        case .tennis(let t):
            if let p1 = t.pP1 { s += "\nModell: \(p1 >= 0.5 ? t.p1.name : t.p2.name) \(Fmt.pct(max(p1, 1 - p1)))" }
        }
        return s + "\n\nvia Sport-Radar"
    }
}

// MARK: Kopf mit beiden Seiten

private struct DuelHeader: View {
    @Environment(AppStore.self) private var store
    let competition: String
    let date: Date?
    let left: (name: String, icon: String?, meta: String)
    let right: (name: String, icon: String?, meta: String)
    var round = false
    var duration: TimeInterval

    var body: some View {
        VStack(spacing: 14) {
            VStack(spacing: 4) {
                Text(competition).font(.subheadline.weight(.semibold))
                TimelineView(.periodic(from: .now, by: 60)) { ctx in
                    HStack(spacing: 6) {
                        Text(Fmt.longDate(date))
                        StateBadge(state: MatchState(start: date, duration: duration, now: ctx.date))
                    }
                    .font(.footnote)
                }
            }
            .foregroundStyle(.white.opacity(0.9))
            HStack(alignment: .top, spacing: 8) {
                side(left)
                Text("vs").font(.headline).foregroundStyle(.white.opacity(0.6)).padding(.top, 22)
                side(right)
            }
        }
        .padding(16)
        .frame(maxWidth: .infinity)
        .background(BrandBackground())
        .clipShape(RoundedRectangle(cornerRadius: 20))
        .padding(.top, 8)
    }

    private func side(_ s: (name: String, icon: String?, meta: String)) -> some View {
        VStack(spacing: 6) {
            Crest(url: s.icon, name: s.name, size: 56, round: round)
            Text(s.name).font(.headline).foregroundStyle(.white).multilineTextAlignment(.center).lineLimit(2)
            if !s.meta.isEmpty {
                Text(s.meta).font(.caption).foregroundStyle(.white.opacity(0.75)).multilineTextAlignment(.center)
            }
            Button {
                store.toggleFavorite(s.name)
            } label: {
                Image(systemName: store.isFavorite(name: s.name) ? "star.fill" : "star")
                    .foregroundStyle(store.isFavorite(name: s.name) ? Color.gold : .white.opacity(0.8))
                    .padding(6)
            }
            .accessibilityLabel(store.isFavorite(name: s.name) ? "\(s.name) aus Favoriten entfernen" : "\(s.name) als Favorit merken")
            .sensoryFeedback(.impact(weight: .light), trigger: store.isFavorite(name: s.name))
        }
        .frame(maxWidth: .infinity)
    }
}

// MARK: Fußball

struct FootballDetail: View {
    let m: FootballMatch
    let league: League

    var body: some View {
        DuelHeader(competition: "\(league.flag) \(league.name)", date: m.date,
                   left: (m.home, m.homeIcon, posText(m.posHome)),
                   right: (m.away, m.awayIcon, posText(m.posAway)),
                   duration: 115 * 60)

        if let p = m.prediction {
            SectionCard(title: "Modell-Vorhersage", icon: "chart.bar.fill") {
                ProbBar.football(p, height: 28)
                HStack {
                    Text(m.home).foregroundStyle(Color.homeSide)
                    Spacer()
                    Text("Unentschieden").foregroundStyle(.secondary)
                    Spacer()
                    Text(m.away).foregroundStyle(Color.awaySide)
                }
                .font(.caption.weight(.semibold)).lineLimit(1)
                LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible()), GridItem(.flexible())], spacing: 8) {
                    if let t = p.tipScore { KV(label: "Tipp", value: t) }
                    if let h = p.xgHome, let a = p.xgAway {
                        KV(label: "xG", value: "\(Fmt.num(h)) : \(Fmt.num(a))")
                    }
                    if let o = p.pOver25 { KV(label: "Über 2,5 Tore", value: Fmt.pct(o)) }
                    if let b = p.pBtts { KV(label: "Beide treffen", value: Fmt.pct(b)) }
                    if let c = p.confidence {
                        KV(label: "Datenlage", value: c.capitalized,
                           tint: c == "hoch" ? Color.good : (c == "niedrig" ? Color.bad : nil))
                    }
                }
            }
        }

        if let o = m.odds {
            SectionCard(title: "Quoten", icon: "eurosign.circle") {
                HStack(spacing: 8) {
                    OddsChip(label: "1", odds: o.h, hot: m.value?.outcome == "1")
                    OddsChip(label: "X", odds: o.d, hot: m.value?.outcome == "X")
                    OddsChip(label: "2", odds: o.a, hot: m.value?.outcome == "2")
                    Spacer()
                    if let s = o.src { Text(s).font(.caption).foregroundStyle(.secondary) }
                }
                if let v = m.value {
                    let name = v.outcome == "1" ? m.home : (v.outcome == "2" ? m.away : "Unentschieden")
                    ValueNote(name: name, odds: v.odds, edge: v.edge)
                }
            }
        }

        if let a = m.analysis, !a.isEmpty {
            SectionCard(title: "Analyse", icon: "text.alignleft") {
                Text(a).font(.callout).foregroundStyle(.secondary).fixedSize(horizontal: false, vertical: true)
            }
        }

        SectionCard(title: "Form", icon: "waveform.path.ecg") {
            FormLine(title: "\(m.home) – gesamt", form: m.formHome)
            FormLine(title: "\(m.home) – zu Hause", form: m.formHomeH)
            FormLine(title: "\(m.away) – gesamt", form: m.formAway)
            FormLine(title: "\(m.away) – auswärts", form: m.formAwayA)
        }

        if let h = m.h2h, !h.isEmpty {
            SectionCard(title: "Direkte Duelle", icon: "arrow.left.arrow.right") {
                ForEach(h, id: \.self) { x in
                    HStack {
                        Text(x.date ?? "").font(.caption).foregroundStyle(.secondary).frame(width: 78, alignment: .leading)
                        Text("\(x.home ?? "") – \(x.away ?? "")").font(.footnote).lineLimit(1)
                        Spacer()
                        Text(x.score ?? "").font(.footnote.weight(.semibold)).monospacedDigit()
                    }
                }
            }
        }

        if !(m.scorersHome ?? []).isEmpty || !(m.scorersAway ?? []).isEmpty {
            SectionCard(title: "Torschützen" + (m.scorersPeriod.map { " (\($0))" } ?? ""), icon: "soccerball") {
                HStack(alignment: .top, spacing: 12) {
                    PeopleColumn(title: m.home, rows: (m.scorersHome ?? []).map { ($0.name, $0.goals.map { "\($0)" } ?? "") })
                    PeopleColumn(title: m.away, rows: (m.scorersAway ?? []).map { ($0.name, $0.goals.map { "\($0)" } ?? "") })
                }
            }
        }

        if !(m.injuriesHome ?? []).isEmpty || !(m.injuriesAway ?? []).isEmpty {
            SectionCard(title: "Ausfälle", icon: "cross.case") {
                HStack(alignment: .top, spacing: 12) {
                    PeopleColumn(title: m.home, rows: (m.injuriesHome ?? []).map { ($0.name, Self.reason($0.reason)) })
                    PeopleColumn(title: m.away, rows: (m.injuriesAway ?? []).map { ($0.name, Self.reason($0.reason)) })
                }
            }
        }

        if let n = m.news, !n.isEmpty {
            SectionCard(title: "News", icon: "newspaper") {
                ForEach(n, id: \.self) { item in
                    if let u = URL(string: item.link) {
                        Link(destination: u) {
                            HStack {
                                Text(item.title).font(.footnote).multilineTextAlignment(.leading)
                                Spacer()
                                Image(systemName: "arrow.up.right").font(.caption)
                            }
                        }
                    }
                }
            }
        }

        if let b = m.basis, !b.isEmpty {
            Text(b).font(.caption2).foregroundStyle(.secondary).padding(.horizontal, 4)
        }
    }

    private func posText(_ p: Int?) -> String {
        guard let p else { return "" }
        if let n = m.nTeams { return "Platz \(p) von \(n)" }
        return "Platz \(p)"
    }

    /// Übersetzt die häufigsten englischen Verletzungsgründe.
    static func reason(_ r: String?) -> String {
        guard let r else { return "" }
        let map = ["Muscle Injury": "Muskel", "Knee Injury": "Knie", "Back Injury": "Rücken",
                   "Shoulder Injury": "Schulter", "Groin Injury": "Leiste", "Ankle Injury": "Knöchel",
                   "Hamstring Injury": "Oberschenkel", "Neck Injury": "Nacken", "Foot Injury": "Fuß",
                   "Calf Injury": "Wade", "Hip Injury": "Hüfte", "Thigh Injury": "Oberschenkel",
                   "Injury": "Verletzung", "Illness": "Krank", "Suspended": "Gesperrt",
                   "Red Card": "Rote Karte", "Yellow Cards": "Gelbsperre", "Knock": "Schlag"]
        return map[r] ?? r
    }
}

// MARK: Tennis

struct TennisDetail: View {
    let m: TennisMatch

    var body: some View {
        DuelHeader(competition: "\(m.tour) · \(m.tournament)", date: m.timeTBD == true ? nil : m.date,
                   left: (m.p1.name, nil, rankText(m.p1)),
                   right: (m.p2.name, nil, rankText(m.p2)),
                   round: true, duration: 150 * 60)

        if m.unconfirmed == true {
            Label("Ansetzung unbestätigt – der finale Spielplan erscheint meist erst am Vorabend.",
                  systemImage: "exclamationmark.triangle")
                .font(.footnote).foregroundStyle(.secondary)
                .frame(maxWidth: .infinity, alignment: .leading)
        }

        if let p1 = m.pP1 {
            SectionCard(title: "Modell-Vorhersage", icon: "chart.bar.fill") {
                ProbBar.tennis(p1, height: 28)
                HStack {
                    Text(m.p1.name).foregroundStyle(Color.homeSide)
                    Spacer()
                    Text(m.p2.name).foregroundStyle(Color.awaySide)
                }
                .font(.caption.weight(.semibold)).lineLimit(1)
                LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 8) {
                    KV(label: "Basis", value: m.usesElo ? "Elo-Formmodell" : "Weltrangliste")
                    KV(label: "Runde", value: [m.round, m.surface].compactMap { $0 }.joined(separator: " · ").ifEmpty("–"))
                }
            }
        }

        if let o = m.odds {
            SectionCard(title: "Quoten", icon: "eurosign.circle") {
                HStack(spacing: 8) {
                    OddsChip(label: lastName(m.p1.name), odds: o.p1, hot: m.value?.name == m.p1.name)
                    OddsChip(label: lastName(m.p2.name), odds: o.p2, hot: m.value?.name == m.p2.name)
                    Spacer()
                    if let s = o.src { Text(s).font(.caption).foregroundStyle(.secondary) }
                }
                if let v = m.value {
                    ValueNote(name: v.name ?? "", odds: v.odds, edge: v.edge)
                }
            }
        }

        if let a = m.analysis, !a.isEmpty {
            SectionCard(title: "Analyse", icon: "text.alignleft") {
                Text(a).font(.callout).foregroundStyle(.secondary).fixedSize(horizontal: false, vertical: true)
            }
        }

        if !m.isDoubles {
            SectionCard(title: "Spielerprofil", icon: "person.2") {
                PlayerProfile(p: m.p1, surface: m.surface)
                Divider()
                PlayerProfile(p: m.p2, surface: m.surface)
            }
        }

        if let h = m.h2h, !h.isEmpty {
            SectionCard(title: "Direkte Duelle (\(h.count))", icon: "arrow.left.arrow.right") {
                ForEach(h, id: \.self) { x in
                    VStack(alignment: .leading, spacing: 2) {
                        HStack {
                            Text(x.year).font(.caption).foregroundStyle(.secondary)
                            Text(x.tourney + (x.surface.map { " (\($0))" } ?? "")).font(.caption).lineLimit(1)
                            Spacer()
                            Text(x.score ?? "").font(.caption.weight(.semibold)).monospacedDigit()
                        }
                        Text("Sieger: \(x.winner)").font(.footnote.weight(.semibold))
                    }
                }
            }
        }

        if let b = m.basis, !b.isEmpty {
            Text(b).font(.caption2).foregroundStyle(.secondary).padding(.horizontal, 4)
        }
    }

    private func rankText(_ p: TennisPlayer) -> String {
        p.rank.map { "Weltrangliste #\($0)" } ?? (m.isDoubles ? "Doppel" : "ohne Top-Ranking")
    }

    private func lastName(_ n: String) -> String { n.split(separator: " ").last.map(String.init) ?? n }
}

private struct PlayerProfile: View {
    let p: TennisPlayer
    let surface: String?

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Text(p.name).font(.subheadline.weight(.semibold))
                Spacer()
                if let f = p.form, !f.isEmpty { FormBadges(form: f) }
            }
            let list = facts()
            if !list.isEmpty {
                Text(list.joined(separator: " · ")).font(.caption).foregroundStyle(.secondary)
            }
        }
    }

    private func facts() -> [String] {
        var out: [String] = []
        if let r = p.rank { out.append("#\(r)") }
        if let s = p.onSurface, let surface { out.append("\(surface): \(Fmt.pct(s.pct)) (\(s.w):\(s.l))") }
        if let f = p.favSurface { out.append("Lieblingsbelag: \(f)") }
        if let e = p.elo { out.append("Elo \(Int(e.rounded()))") }
        if let l = p.last7, l >= 3 { out.append("⚠️ \(l) Matches in 7 Tagen") }
        return out
    }
}

// MARK: Bausteine

private struct ValueNote: View {
    let name: String
    let odds: Double
    let edge: Double

    var body: some View {
        HStack(alignment: .top, spacing: 8) {
            Image(systemName: "diamond.fill").foregroundStyle(Color.gold)
            Text("**Value-Signal: \(name)** – Quote \(Fmt.num(odds, digits: 2)), das Modell sieht \(Int((edge * 100).rounded())) Prozentpunkte mehr Wahrscheinlichkeit als der Buchmacher.")
                .font(.footnote)
                .fixedSize(horizontal: false, vertical: true)
        }
        .padding(10)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color.gold.opacity(0.12), in: RoundedRectangle(cornerRadius: 10))
    }
}

private struct FormLine: View {
    let title: String
    let form: [String]?

    var body: some View {
        if let form, !form.isEmpty {
            HStack {
                Text(title).font(.footnote).lineLimit(1)
                Spacer()
                FormBadges(form: form, size: 18)
            }
        }
    }
}

private struct PeopleColumn: View {
    let title: String
    let rows: [(String, String)]

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(title).font(.caption.weight(.semibold)).foregroundStyle(.secondary).lineLimit(1)
            if rows.isEmpty {
                Text("–").font(.footnote).foregroundStyle(.secondary)
            }
            ForEach(Array(rows.prefix(8).enumerated()), id: \.offset) { _, r in
                HStack(spacing: 4) {
                    Text(r.0).font(.footnote).lineLimit(1)
                    Spacer(minLength: 2)
                    Text(r.1).font(.caption).foregroundStyle(.secondary).lineLimit(1)
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }
}

extension String {
    func ifEmpty(_ fallback: String) -> String { isEmpty ? fallback : self }
}

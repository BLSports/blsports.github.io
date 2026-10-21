import Foundation
import Observation
import UserNotifications

/// Ein Spiel aus beiden Sportarten, für gemeinsame Listen, Suche und Filter.
enum AnyMatch: Identifiable {
    case football(FootballMatch, League)
    case tennis(TennisMatch)

    var id: String {
        switch self {
        case .football(let m, _): return m.id
        case .tennis(let m): return m.id
        }
    }

    var date: Date? {
        switch self {
        case .football(let m, _): return m.date
        case .tennis(let m): return m.date
        }
    }

    var names: [String] {
        switch self {
        case .football(let m, _): return [m.home, m.away]
        case .tennis(let m): return [m.p1.name, m.p2.name]
        }
    }

    var title: String { names.joined(separator: " – ") }

    var competition: String {
        switch self {
        case .football(_, let l): return "\(l.flag) \(l.name)"
        case .tennis(let m): return "\(m.tour) · \(m.tournament)"
        }
    }

    var value: ValueSignal? {
        switch self {
        case .football(let m, _): return m.value
        case .tennis(let m): return m.value
        }
    }

    var isFootball: Bool { if case .football = self { return true } else { return false } }

    /// Ungefähre Spieldauer, um "läuft" / "vorbei" anzuzeigen.
    var duration: TimeInterval { isFootball ? 115 * 60 : 150 * 60 }

    func matches(search q: String) -> Bool {
        if q.isEmpty { return true }
        let hay = (names + [competition]).joined(separator: " ").lowercased()
        return q.lowercased().split(separator: " ").allSatisfy { hay.contains($0) }
    }
}

enum MatchFilter: String, CaseIterable, Identifiable {
    case alle = "Alle", fussball = "Fußball", tennis = "Tennis", value = "Value", favoriten = "Favoriten"
    var id: String { rawValue }
    var icon: String {
        switch self {
        case .alle: return "square.grid.2x2"
        case .fussball: return "soccerball"
        case .tennis: return "tennis.racket"
        case .value: return "diamond.fill"
        case .favoriten: return "star.fill"
        }
    }
}

@MainActor
@Observable
final class AppStore {
    static let dataURL = URL(string: "https://raw.githubusercontent.com/BLSports/blsports.github.io/main/data/data.json")!
    static let liveURL = URL(string: "https://raw.githubusercontent.com/BLSports/blsports.github.io/main/data/live.json")!
    static let websiteURL = URL(string: "https://blsports.github.io/")!

    private(set) var data: SportData?
    private(set) var live: LiveData?
    private(set) var isLoading = false
    private(set) var loadError: String?
    private(set) var lastFetch: Date?
    private(set) var isOffline = false

    var favorites: Set<String> {
        didSet { UserDefaults.standard.set(Array(favorites), forKey: "favorites") }
    }
    var reminders: Set<String> {
        didSet { UserDefaults.standard.set(Array(reminders), forKey: "reminders") }
    }

    private let cacheFile: URL = {
        let dir = FileManager.default.urls(for: .cachesDirectory, in: .userDomainMask)[0]
        return dir.appendingPathComponent("data.json")
    }()

    init() {
        favorites = Set(UserDefaults.standard.stringArray(forKey: "favorites") ?? [])
        reminders = Set(UserDefaults.standard.stringArray(forKey: "reminders") ?? [])
        if let raw = try? Data(contentsOf: cacheFile),
           let d = try? JSONDecoder().decode(SportData.self, from: raw) {
            data = d
        }
    }

    // MARK: Laden

    private func fetch(_ url: URL) async throws -> Data {
        var comps = URLComponents(url: url, resolvingAgainstBaseURL: false)!
        comps.queryItems = [URLQueryItem(name: "v", value: String(Int(Date().timeIntervalSince1970)))]
        var req = URLRequest(url: comps.url!, cachePolicy: .reloadIgnoringLocalCacheData, timeoutInterval: 20)
        req.setValue("application/json", forHTTPHeaderField: "Accept")
        let (body, resp) = try await URLSession.shared.data(for: req)
        if let http = resp as? HTTPURLResponse, !(200..<300).contains(http.statusCode) {
            throw URLError(.badServerResponse)
        }
        return body
    }

    func refresh() async {
        guard !isLoading else { return }
        isLoading = true
        defer { isLoading = false }
        do {
            let raw = try await fetch(Self.dataURL)
            let d = try JSONDecoder().decode(SportData.self, from: raw)
            data = d
            loadError = nil
            isOffline = false
            lastFetch = Date()
            try? raw.write(to: cacheFile, options: .atomic)
        } catch is DecodingError {
            loadError = "Die Daten haben ein unerwartetes Format."
        } catch {
            isOffline = true
            loadError = data == nil ? "Keine Verbindung – bitte später erneut versuchen." : nil
        }
        await refreshLive()
    }

    /// Lädt neu, wenn der letzte Abruf älter als `maxAge` ist (z. B. beim Zurückkehren in die App).
    func refreshIfStale(maxAge: TimeInterval = 10 * 60) async {
        if let t = lastFetch, Date().timeIntervalSince(t) < maxAge {
            await refreshLive()
        } else {
            await refresh()
        }
    }

    func refreshLive() async {
        guard let raw = try? await fetch(Self.liveURL),
              let l = try? JSONDecoder().decode(LiveData.self, from: raw) else { return }
        live = l
    }

    /// Live-Daten gelten nur, wenn sie frisch sind (der Ticker läuft alle 15 Min.).
    var liveIsFresh: Bool {
        guard let d = live?.updatedDate else { return false }
        return Date().timeIntervalSince(d) < 40 * 60
    }

    var liveCount: Int {
        guard liveIsFresh, let l = live else { return 0 }
        return l.football.count + l.tennis.count
    }

    // MARK: Abfragen

    var days: [String] { data?.days ?? [] }

    func allMatches(day: String) -> [AnyMatch] {
        guard let d = data else { return [] }
        var out: [AnyMatch] = []
        for l in d.football {
            for m in l.matches where m.day == day { out.append(.football(m, l)) }
        }
        for m in d.tennis where m.day == day { out.append(.tennis(m)) }
        return out
    }

    func match(id: String) -> AnyMatch? {
        guard let d = data else { return nil }
        if id.hasPrefix("fb|") {
            for l in d.football {
                if let m = l.matches.first(where: { $0.id == id }) { return .football(m, l) }
            }
        } else if let m = d.tennis.first(where: { $0.id == id }) {
            return .tennis(m)
        }
        return nil
    }

    struct Group: Identifiable {
        let id: String
        let title: String
        let subtitle: String?
        let matches: [AnyMatch]
    }

    /// Spiele eines Tages, gefiltert und nach Liga bzw. Turnier gruppiert.
    func groups(day: String, filter: MatchFilter, search: String) -> [Group] {
        guard let d = data else { return [] }
        func keep(_ m: AnyMatch) -> Bool {
            guard m.matches(search: search) else { return false }
            switch filter {
            case .alle: return true
            case .fussball: return m.isFootball
            case .tennis: return !m.isFootball
            case .value: return m.value != nil
            case .favoriten: return isFavorite(m)
            }
        }
        var out: [Group] = []
        for l in d.football {
            let ms = l.matches.filter { $0.day == day }
                .map { AnyMatch.football($0, l) }
                .filter(keep)
                .sorted { ($0.date ?? .distantFuture) < ($1.date ?? .distantFuture) }
            if !ms.isEmpty { out.append(Group(id: "fb-\(l.id)", title: "\(l.flag) \(l.name)", subtitle: nil, matches: ms)) }
        }
        var order: [String] = []
        var byTourney: [String: [AnyMatch]] = [:]
        var surfaces: [String: String] = [:]
        for m in d.tennis where m.day == day {
            let am = AnyMatch.tennis(m)
            guard keep(am) else { continue }
            let key = "\(m.tour) · \(m.tournament)"
            if byTourney[key] == nil { order.append(key) }
            byTourney[key, default: []].append(am)
            if let s = m.surface { surfaces[key] = s }
        }
        for key in order {
            let ms = (byTourney[key] ?? []).sorted { ($0.date ?? .distantFuture) < ($1.date ?? .distantFuture) }
            out.append(Group(id: "tn-\(key)", title: "🎾 \(key)", subtitle: surfaces[key], matches: ms))
        }
        return out
    }

    struct Tip: Identifiable {
        let match: AnyMatch
        let p: Double
        let pick: String
        var id: String { match.id }
    }

    /// Die sichersten Tipps eines Tages (Modell-Wahrscheinlichkeit des Favoriten).
    func safestTips(day: String, limit: Int = 10) -> [Tip] {
        var tips: [Tip] = []
        for m in allMatches(day: day) {
            switch m {
            case .football(let f, _):
                guard let p = f.prediction, p.confidence != "niedrig", let i = f.tipIndex else { continue }
                tips.append(Tip(match: m, p: [p.pHome, p.pDraw, p.pAway][i], pick: [f.home, "Unentschieden", f.away][i]))
            case .tennis(let t):
                guard let p1 = t.pP1, !t.isDoubles else { continue }
                tips.append(Tip(match: m, p: max(p1, 1 - p1), pick: p1 >= 0.5 ? t.p1.name : t.p2.name))
            }
        }
        return Array(tips.sorted { $0.p > $1.p }.prefix(limit))
    }

    func valueTips(day: String) -> [AnyMatch] {
        allMatches(day: day).filter { $0.value != nil }.sorted { ($0.value?.edge ?? 0) > ($1.value?.edge ?? 0) }
    }

    func goalGames(day: String, limit: Int = 6) -> [FootballMatch] {
        var out: [FootballMatch] = []
        for m in allMatches(day: day) {
            if case .football(let f, _) = m, f.prediction?.pOver25 != nil { out.append(f) }
        }
        return Array(out.sorted { ($0.prediction?.pOver25 ?? 0) > ($1.prediction?.pOver25 ?? 0) }.prefix(limit))
    }

    // MARK: Favoriten

    func isFavorite(name: String) -> Bool { favorites.contains(name) }
    func isFavorite(_ m: AnyMatch) -> Bool { m.names.contains { favorites.contains($0) } }

    func toggleFavorite(_ name: String) {
        if favorites.contains(name) { favorites.remove(name) } else { favorites.insert(name) }
    }

    // MARK: Erinnerungen (lokale Mitteilung 15 Min. vor Beginn)

    func hasReminder(_ m: AnyMatch) -> Bool { reminders.contains(m.id) }

    /// Gibt eine Fehlermeldung zurück, falls die Erinnerung nicht gesetzt werden konnte.
    func toggleReminder(_ m: AnyMatch) async -> String? {
        let center = UNUserNotificationCenter.current()
        if reminders.contains(m.id) {
            center.removePendingNotificationRequests(withIdentifiers: [m.id])
            reminders.remove(m.id)
            return nil
        }
        guard let start = m.date else { return "Für dieses Spiel steht noch keine Uhrzeit fest." }
        let fire = start.addingTimeInterval(-15 * 60)
        guard fire > Date() else { return "Das Spiel beginnt in weniger als 15 Minuten." }
        let granted = (try? await center.requestAuthorization(options: [.alert, .sound, .badge])) ?? false
        guard granted else { return "Mitteilungen sind deaktiviert. Du kannst sie in den iPhone-Einstellungen unter „Sport-Radar“ erlauben." }

        let content = UNMutableNotificationContent()
        content.title = m.title
        content.body = "\(m.competition) – beginnt in 15 Minuten (\(start.formatted(date: .omitted, time: .shortened)) Uhr)."
        content.sound = .default
        let comps = Calendar.current.dateComponents([.year, .month, .day, .hour, .minute], from: fire)
        let req = UNNotificationRequest(identifier: m.id, content: content,
                                        trigger: UNCalendarNotificationTrigger(dateMatching: comps, repeats: false))
        do {
            try await center.add(req)
            reminders.insert(m.id)
            return nil
        } catch {
            return "Erinnerung konnte nicht gespeichert werden."
        }
    }

    /// Entfernt Erinnerungen, deren Mitteilung bereits ausgelöst wurde.
    func pruneReminders() async {
        let pending = await UNUserNotificationCenter.current().pendingNotificationRequests().map(\.identifier)
        reminders = reminders.intersection(pending)
    }
}

import Foundation

// Abbild von data/data.json und data/live.json (erzeugt von scripts/fetch_data.py
// bzw. scripts/live_update.py). Fast alles ist optional, damit ein neues oder
// fehlendes Feld im Python-Teil nie die ganze App lahmlegt.

struct SportData: Decodable {
    let generatedAt: String
    let days: [String]
    let football: [League]
    let tennis: [TennisMatch]
    let tennisFinished: [TennisResult]
    let stats: Stats?
    let meta: Meta?

    enum CodingKeys: String, CodingKey {
        case generatedAt, days, football, tennis, tennisFinished, stats, meta
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        generatedAt = try c.decode(String.self, forKey: .generatedAt)
        days = (try? c.decode([String].self, forKey: .days)) ?? []
        football = (try? c.decode(Lossy<League>.self, forKey: .football).items) ?? []
        tennis = (try? c.decode(Lossy<TennisMatch>.self, forKey: .tennis).items) ?? []
        tennisFinished = (try? c.decode(Lossy<TennisResult>.self, forKey: .tennisFinished).items) ?? []
        stats = try? c.decode(Stats.self, forKey: .stats)
        meta = try? c.decode(Meta.self, forKey: .meta)
    }

    var generatedDate: Date? { DateParse.parse(generatedAt) }
}

struct Meta: Decodable {
    let season: String?
}

struct League: Decodable, Identifiable {
    let id: String
    let name: String
    let flag: String
    let matches: [FootballMatch]
    let isCup: Bool?

    enum CodingKeys: String, CodingKey { case id, name, flag, matches, isCup }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        id = try c.decode(String.self, forKey: .id)
        name = try c.decode(String.self, forKey: .name)
        flag = (try? c.decode(String.self, forKey: .flag)) ?? "⚽"
        matches = (try? c.decode(Lossy<FootballMatch>.self, forKey: .matches).items) ?? []
        isCup = try? c.decode(Bool.self, forKey: .isCup)
    }
}

struct FootballMatch: Decodable {
    let kickoff: String
    let home: String
    let away: String
    let homeIcon: String?
    let awayIcon: String?
    let matchday: Int?
    let roundName: String?
    let formHome: [String]?
    let formAway: [String]?
    let formHomeH: [String]?
    let formAwayA: [String]?
    let posHome: Int?
    let posAway: Int?
    let nTeams: Int?
    let h2h: [FootballH2H]?
    let prediction: Prediction?
    let odds: Odds1X2?
    let value: ValueSignal?
    let scorersHome: [Scorer]?
    let scorersAway: [Scorer]?
    let scorersPeriod: String?
    let analysis: String?
    let basis: String?
    let injuriesHome: [Injury]?
    let injuriesAway: [Injury]?
    let news: [News]?

    var id: String { "fb|\(kickoff)|\(home)|\(away)" }
    var date: Date? { DateParse.parse(kickoff) }
    var day: String { String(kickoff.prefix(10)) }

    /// Index des wahrscheinlichsten Ausgangs (0 = Heim, 1 = X, 2 = Gast)
    var tipIndex: Int? {
        guard let p = prediction else { return nil }
        let probs = [p.pHome, p.pDraw, p.pAway]
        return probs.indices.max { probs[$0] < probs[$1] }
    }
}

struct Prediction: Decodable {
    let pHome: Double
    let pDraw: Double
    let pAway: Double
    let pOver25: Double?
    let pBtts: Double?
    let xgHome: Double?
    let xgAway: Double?
    let tipScore: String?
    let confidence: String?

    var maxP: Double { max(pHome, pDraw, pAway) }
}

struct Odds1X2: Decodable {
    let h: Double
    let d: Double
    let a: Double
    let src: String?
}

/// Fußball: outcome "1"/"X"/"2"; Tennis: name des Spielers.
struct ValueSignal: Decodable {
    let outcome: String?
    let name: String?
    let edge: Double
    let modelP: Double?
    let odds: Double
}

struct FootballH2H: Decodable, Hashable {
    let date: String?
    let home: String?
    let away: String?
    let score: String?
}

struct Scorer: Decodable, Hashable {
    let name: String
    let goals: Int?
}

struct Injury: Decodable, Hashable {
    let name: String
    let reason: String?
}

struct News: Decodable, Hashable {
    let title: String
    let link: String
}

// MARK: Tennis

struct TennisMatch: Decodable {
    let start: String
    let tour: String
    let tournament: String
    let round: String?
    let surface: String?
    let doubles: Bool?
    let p1: TennisPlayer
    let p2: TennisPlayer
    let pP1: Double?
    let model: TennisModel?
    let h2h: [TennisH2H]?
    let analysis: String?
    let basis: String?
    let unconfirmed: Bool?
    let timeTBD: Bool?
    let odds: TennisOdds?
    let value: ValueSignal?

    var id: String { "tn|\(start)|\(p1.name)|\(p2.name)" }
    var date: Date? { DateParse.parse(start) }
    var day: String { String(start.prefix(10)) }
    var isDoubles: Bool { doubles == true }
    var usesElo: Bool { model?.pElo != nil }
}

struct TennisPlayer: Decodable {
    let name: String
    let rank: Int?
    let form: [String]?
    let elo: Double?
    let favSurface: String?
    let onSurface: SurfaceRecord?
    let last7: Int?
}

struct SurfaceRecord: Decodable {
    let pct: Double
    let w: Int
    let l: Int
}

struct TennisModel: Decodable {
    let pElo: Double?
    let pRank: Double?
}

struct TennisOdds: Decodable {
    let p1: Double
    let p2: Double
    let src: String?
}

struct TennisH2H: Decodable, Hashable {
    let year: String
    let tourney: String
    let surface: String?
    let winner: String
    let score: String?

    enum CodingKeys: String, CodingKey { case year, tourney, surface, winner, score }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        if let s = try? c.decode(String.self, forKey: .year) {
            year = s
        } else {
            year = String((try? c.decode(Int.self, forKey: .year)) ?? 0)
        }
        tourney = (try? c.decode(String.self, forKey: .tourney)) ?? ""
        surface = try? c.decode(String.self, forKey: .surface)
        winner = (try? c.decode(String.self, forKey: .winner)) ?? ""
        score = try? c.decode(String.self, forKey: .score)
    }
}

struct TennisResult: Decodable, Hashable {
    let tour: String
    let tournament: String
    let p1: String
    let p2: String
    let winner: String?
    let score: String?
}

// MARK: Bilanz

struct Stats: Decodable {
    let overall: HitRate?
    let football: HitRate?
    let tennis: HitRate?
    let exact: HitRate?
    let open: Int?
    let value: ValueStats?
    let recent: [RecentTip]?
}

struct HitRate: Decodable {
    let n: Int
    let correct: Int
    var pct: Double { n > 0 ? Double(correct) / Double(n) : 0 }
}

struct ValueStats: Decodable {
    let n: Int
    let correct: Int
    let units: Double?
    let avgOdds: Double?
}

struct RecentTip: Decodable, Identifiable {
    let date: String
    let comp: String
    let label: String
    let tipName: String?
    let prob: Double?
    let result: String?
    let correct: Bool?
    let sport: String?

    var id: String { "\(date)|\(label)|\(tipName ?? "")" }
}

// MARK: Live

struct LiveData: Decodable {
    let updated: String?
    let football: [LiveFootball]
    let tennis: [LiveTennis]

    enum CodingKeys: String, CodingKey { case updated, football, tennis }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        updated = try? c.decode(String.self, forKey: .updated)
        football = (try? c.decode(Lossy<LiveFootball>.self, forKey: .football).items) ?? []
        tennis = (try? c.decode(Lossy<LiveTennis>.self, forKey: .tennis).items) ?? []
    }

    var updatedDate: Date? { updated.flatMap(DateParse.parse) }
}

struct LiveFootball: Decodable, Identifiable {
    let league: String
    let home: String
    let away: String
    let score: String
    let minute: Int?
    let status: String?
    let odds: Odds1X2?
    let value: ValueSignal?

    var id: String { "\(home)|\(away)" }
}

struct LiveTennis: Decodable, Identifiable {
    let tour: String
    let tournament: String
    let p1: String
    let p2: String
    let sets: String

    var id: String { "\(p1)|\(p2)" }
}

// MARK: Hilfen

/// Dekodiert ein Array und überspringt einzelne kaputte Einträge, statt komplett zu scheitern.
struct Lossy<T: Decodable>: Decodable {
    let items: [T]

    init(from decoder: Decoder) throws {
        var c = try decoder.unkeyedContainer()
        var out: [T] = []
        while !c.isAtEnd {
            let sub = try c.superDecoder()
            if let item = try? T(from: sub) { out.append(item) }
        }
        items = out
    }
}

enum DateParse {
    private static let iso: ISO8601DateFormatter = {
        let f = ISO8601DateFormatter()
        f.formatOptions = [.withInternetDateTime]
        return f
    }()

    private static let dayOnly: DateFormatter = {
        let f = DateFormatter()
        f.locale = Locale(identifier: "en_US_POSIX")
        f.timeZone = TimeZone(identifier: "Europe/Berlin")
        f.dateFormat = "yyyy-MM-dd"
        return f
    }()

    /// ISO-8601 mit beliebig vielen Nachkommastellen ("…13:04:34.332723+02:00").
    static func parse(_ s: String) -> Date? {
        var str = s
        if let dot = str.firstIndex(of: "."),
           let tz = str[dot...].firstIndex(where: { $0 == "+" || $0 == "-" || $0 == "Z" }) {
            str.removeSubrange(dot..<tz)
        } else if let dot = str.firstIndex(of: ".") {
            str.removeSubrange(dot..<str.endIndex)
            str += "Z"
        }
        if let d = iso.date(from: str) { return d }
        return dayOnly.date(from: String(s.prefix(10)))
    }
}

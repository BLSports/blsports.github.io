import SwiftUI

// Farben wie auf der Website (helles/dunkles Erscheinungsbild).
extension Color {
    static let brand = Color(red: 14 / 255, green: 59 / 255, blue: 44 / 255)
    static let brand2 = Color(red: 24 / 255, green: 104 / 255, blue: 74 / 255)
    static let homeSide = Color(light: (37, 99, 201), dark: (76, 139, 240))
    static let awaySide = Color(light: (224, 102, 47), dark: (238, 122, 69))
    static let gold = Color(light: (201, 138, 4), dark: (242, 182, 50))
    static let good = Color(light: (23, 163, 74), dark: (34, 197, 94))
    static let bad = Color(light: (220, 61, 61), dark: (239, 91, 91))

    init(light: (Int, Int, Int), dark: (Int, Int, Int)) {
        self.init(uiColor: UIColor { tc in
            let c = tc.userInterfaceStyle == .dark ? dark : light
            return UIColor(red: CGFloat(c.0) / 255, green: CGFloat(c.1) / 255, blue: CGFloat(c.2) / 255, alpha: 1)
        })
    }
}

enum Fmt {
    static func pct(_ p: Double) -> String { "\(Int((p * 100).rounded())) %" }
    static func pctShort(_ p: Double) -> String { "\(Int((p * 100).rounded()))%" }

    static func num(_ x: Double, digits: Int = 1) -> String {
        x.formatted(.number.precision(.fractionLength(digits)).locale(Locale(identifier: "de_DE")))
    }

    static func time(_ d: Date?) -> String {
        guard let d else { return "offen" }
        return d.formatted(.dateTime.hour(.twoDigits(amPM: .omitted)).minute(.twoDigits))
    }

    static func longDate(_ d: Date?) -> String {
        guard let d else { return "Termin offen" }
        return d.formatted(.dateTime.weekday(.wide).day().month(.wide).hour().minute().locale(Locale(identifier: "de_DE")))
    }

    static func dayLabel(_ iso: String, index: Int) -> String {
        switch index {
        case 0: return "Heute"
        case 1: return "Morgen"
        default:
            guard let d = DateParse.parse(iso) else { return iso }
            return d.formatted(.dateTime.weekday(.wide).locale(Locale(identifier: "de_DE")))
        }
    }

    static func ago(_ d: Date?) -> String {
        guard let d else { return "" }
        let min = Int(Date().timeIntervalSince(d) / 60)
        if min < 1 { return "gerade eben" }
        if min < 60 { return "vor \(min) Min." }
        if min < 48 * 60 { return "vor \(min / 60) Std." }
        return "vor \(min / 1440) Tagen"
    }

    static func initials(_ name: String) -> String {
        name.split(separator: " ").prefix(2).compactMap(\.first).map(String.init).joined().uppercased()
    }
}

/// Status eines Spiels relativ zu jetzt ("in 20 Min.", "läuft", "vorbei").
struct MatchState {
    enum Kind { case none, soon, live, over }
    let kind: Kind
    let text: String

    init(start: Date?, duration: TimeInterval, now: Date = Date()) {
        guard let start else { kind = .none; text = ""; return }
        let mins = start.timeIntervalSince(now) / 60
        if mins > 0 && mins < 60 {
            kind = .soon; text = "in \(Int(mins.rounded())) Min."
        } else if mins >= 60 && mins < 12 * 60 {
            kind = .soon; text = "in \(Int((mins / 60).rounded())) Std."
        } else if mins <= 0 && -mins * 60 < duration {
            kind = .live; text = "läuft"
        } else if mins <= 0 {
            kind = .over; text = "vorbei"
        } else {
            kind = .none; text = ""
        }
    }
}

struct StateBadge: View {
    let state: MatchState
    var body: some View {
        switch state.kind {
        case .none: EmptyView()
        case .live:
            Text(state.text).font(.caption2.weight(.bold)).foregroundStyle(.white)
                .padding(.horizontal, 6).padding(.vertical, 2)
                .background(Color.bad, in: Capsule())
        case .soon, .over:
            Text(state.text).font(.caption2.weight(.semibold)).foregroundStyle(.secondary)
                .padding(.horizontal, 6).padding(.vertical, 2)
                .background(Color(.tertiarySystemFill), in: Capsule())
        }
    }
}

/// Wappen (Bild aus dem Netz) mit Initialen als Ersatz.
struct Crest: View {
    let url: String?
    let name: String
    var size: CGFloat = 30
    var round = false

    var body: some View {
        ZStack {
            RoundedRectangle(cornerRadius: round ? size / 2 : size * 0.27)
                .fill(Color(.secondarySystemBackground))
            if let s = url, let u = URL(string: s) {
                AsyncImage(url: u) { phase in
                    if let img = phase.image {
                        img.resizable().scaledToFit().padding(size * 0.12)
                    } else {
                        initials
                    }
                }
            } else {
                initials
            }
        }
        .frame(width: size, height: size)
        .accessibilityHidden(true)
    }

    private var initials: some View {
        Text(Fmt.initials(name)).font(.system(size: size * 0.36, weight: .bold)).foregroundStyle(.secondary)
    }
}

/// Formkurve: S/U/N (oder W/D/L) als farbige Kästchen.
struct FormBadges: View {
    let form: [String]
    var size: CGFloat = 16

    var body: some View {
        HStack(spacing: 2) {
            ForEach(Array(form.prefix(5).enumerated()), id: \.offset) { _, r in
                let k = kind(r)
                Text(label(r))
                    .font(.system(size: size * 0.6, weight: .bold))
                    .foregroundStyle(k == 0 ? Color.primary.opacity(0.7) : .white)
                    .frame(width: size, height: size)
                    .background(color(k), in: RoundedRectangle(cornerRadius: 4))
            }
        }
        .accessibilityLabel("Form: " + form.joined(separator: ", "))
    }

    private func kind(_ r: String) -> Int {
        switch r.uppercased() {
        case "S", "W": return 1
        case "N", "L": return -1
        default: return 0
        }
    }

    private func label(_ r: String) -> String {
        switch r.uppercased() {
        case "W": return "S"
        case "L": return "N"
        case "D": return "U"
        default: return r.uppercased()
        }
    }

    private func color(_ k: Int) -> Color {
        k > 0 ? .good : (k < 0 ? .bad : Color(.systemGray4))
    }
}

/// 1 / X / 2 als gestapelter Balken.
struct ProbBar: View {
    struct Part {
        let label: String
        let p: Double
        let color: Color
        var darkText = false
    }

    let parts: [Part]
    var height: CGFloat = 22
    var showLabels = true

    var body: some View {
        GeometryReader { geo in
            let gap: CGFloat = 2
            let total = max(parts.reduce(0) { $0 + $1.p }, 0.0001)
            let width = geo.size.width - gap * CGFloat(parts.count - 1)
            HStack(spacing: gap) {
                ForEach(Array(parts.enumerated()), id: \.offset) { _, part in
                    let w = width * part.p / total
                    ZStack {
                        part.color
                        if showLabels && w > 34 {
                            Text(part.label.isEmpty ? Fmt.pctShort(part.p) : "\(part.label) \(Fmt.pctShort(part.p))")
                                .font(.system(size: 11, weight: .bold))
                                .foregroundStyle(part.darkText ? Color.primary.opacity(0.75) : Color.white)
                                .lineLimit(1)
                        }
                    }
                    .frame(width: max(w, 0))
                }
            }
        }
        .frame(height: height)
        .clipShape(RoundedRectangle(cornerRadius: height * 0.3))
    }

    static func football(_ p: Prediction, height: CGFloat = 22, labels: Bool = true) -> ProbBar {
        ProbBar(parts: [Part(label: "1", p: p.pHome, color: .homeSide),
                        Part(label: "X", p: p.pDraw, color: Color(.systemGray4), darkText: true),
                        Part(label: "2", p: p.pAway, color: .awaySide)],
                height: height, showLabels: labels)
    }

    static func tennis(_ p1: Double, height: CGFloat = 22, labels: Bool = true) -> ProbBar {
        ProbBar(parts: [Part(label: "", p: p1, color: .homeSide), Part(label: "", p: 1 - p1, color: .awaySide)],
                height: height, showLabels: labels)
    }
}

struct ValuePill: View {
    let edge: Double
    var body: some View {
        Label("+\(Int((edge * 100).rounded()))", systemImage: "diamond.fill")
            .font(.caption2.weight(.bold))
            .foregroundStyle(Color.gold)
            .padding(.horizontal, 7).padding(.vertical, 2)
            .background(Color.gold.opacity(0.15), in: Capsule())
            .accessibilityLabel("Value-Signal, plus \(Int((edge * 100).rounded())) Prozentpunkte")
    }
}

/// Kleine Kennzahl-Kachel (z. B. "xG 2,0 : 1,2").
struct KV: View {
    let label: String
    let value: String
    var tint: Color? = nil

    var body: some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(label).font(.caption2).foregroundStyle(.secondary)
            Text(value).font(.subheadline.weight(.semibold)).foregroundStyle(tint ?? .primary)
                .lineLimit(1).minimumScaleFactor(0.7)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.horizontal, 10).padding(.vertical, 7)
        .background(Color(.secondarySystemBackground), in: RoundedRectangle(cornerRadius: 10))
    }
}

struct OddsChip: View {
    let label: String
    let odds: Double
    var hot = false

    var body: some View {
        HStack(spacing: 4) {
            Text(label).foregroundStyle(.secondary).lineLimit(1)
            Text(Fmt.num(odds, digits: 2)).fontWeight(.semibold).monospacedDigit()
        }
        .font(.footnote)
        .padding(.horizontal, 9).padding(.vertical, 5)
        .background(hot ? Color.gold.opacity(0.15) : Color(.secondarySystemBackground), in: RoundedRectangle(cornerRadius: 8))
        .overlay(RoundedRectangle(cornerRadius: 8).stroke(hot ? Color.gold : .clear, lineWidth: 1.5))
    }
}

struct SectionCard<Content: View>: View {
    let title: String
    var icon: String? = nil
    @ViewBuilder let content: Content

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            if let icon {
                Label(title, systemImage: icon).font(.headline)
            } else {
                Text(title).font(.headline)
            }
            content
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(14)
        .background(Color(.systemBackground), in: RoundedRectangle(cornerRadius: 16))
    }
}

/// Grüner Verlauf wie im Kopfbereich der Website.
struct BrandBackground: View {
    var body: some View {
        RadialGradient(colors: [.brand2, .brand], center: UnitPoint(x: 0.85, y: -0.1), startRadius: 0, endRadius: 420)
    }
}

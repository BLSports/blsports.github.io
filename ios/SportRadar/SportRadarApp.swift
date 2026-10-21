import SwiftUI

@main
struct SportRadarApp: App {
    @State private var store = AppStore()
    @Environment(\.scenePhase) private var scenePhase

    var body: some Scene {
        WindowGroup {
            RootView()
                .environment(store)
                .tint(Color(light: (17, 135, 93), dark: (47, 191, 134)))
                .task { await store.refresh() }
                .onChange(of: scenePhase) { _, phase in
                    if phase == .active {
                        Task {
                            await store.refreshIfStale()
                            await store.pruneReminders()
                        }
                    }
                }
        }
    }
}

struct RootView: View {
    @Environment(AppStore.self) private var store
    @AppStorage("tab") private var tab = 0

    var body: some View {
        TabView(selection: $tab) {
            MatchesView()
                .tabItem { Label("Spiele", systemImage: "sportscourt") }
                .tag(0)
            TipsView()
                .tabItem { Label("Tipps", systemImage: "scope") }
                .tag(1)
            LiveView()
                .tabItem { Label("Live", systemImage: "dot.radiowaves.left.and.right") }
                .badge(store.liveCount)
                .tag(2)
            StatsView()
                .tabItem { Label("Bilanz", systemImage: "chart.bar") }
                .tag(3)
        }
    }
}

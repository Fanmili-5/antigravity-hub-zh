import Foundation
import Combine

struct WorkspaceTag: Decodable {
    let group: String
    let label: String

    static func decode(_ encoded: Substring) -> Self? {
        guard let data = Data(base64Encoded: String(encoded)),
              let workspace = try? JSONDecoder().decode(Self.self, from: data),
              workspace.group.range(of: "^[a-f0-9]{20}$", options: .regularExpression) != nil,
              !workspace.label.isEmpty, workspace.label.count <= 40,
              workspace.label.rangeOfCharacter(from: .controlCharacters) == nil else { return nil }
        return workspace
    }
}

struct ActivitySession: Identifiable {
    let id: String
    let group: String
    let workspace: String
    let mood: Mood
    let started: Date
    let updated: Date
    let expires: TimeInterval
    let updatedUptime: TimeInterval
}

struct ActivityGroup: Identifiable {
    let id: String
    let label: String
    let sessions: [ActivitySession]
}

final class LiveActivity: ObservableObject {
    @Published private(set) var records: [String: ActivitySession] = [:]
    private var nextExpiry = Double.infinity

    var running: Int { records.values.reduce(0) { $0 + ($1.mood == .thinking ? 1 : 0) } }

    func record(_ id: String, mood: Mood, tag: WorkspaceTag?, date: Date = Date(),
                uptime: TimeInterval = ProcessInfo.processInfo.systemUptime) -> Bool {
        expire(uptime)
        let previous = records[id]
        if records.count >= 128 && previous == nil {
            let oldest = records.values.sorted {
                if ($0.mood == .thinking) != ($1.mood == .thinking) { return $0.mood != .thinking }
                return $0.updated < $1.updated
            }.first?.id
            if let oldest { records.removeValue(forKey: oldest) }
        }
        let continues = previous?.mood == .thinking
        let expires = uptime + (mood == .thinking ? 900 : 3600)
        records[id] = ActivitySession(
            id: id, group: tag?.group ?? previous?.group ?? "", workspace: tag?.label ?? previous?.workspace ?? "未标记工作区",
            mood: mood, started: continues ? (previous?.started ?? date) : date, updated: date,
            expires: expires, updatedUptime: uptime
        )
        nextExpiry = min(nextExpiry, expires)
        return previous?.mood != mood
    }

    func expire(_ uptime: TimeInterval) {
        guard uptime >= nextExpiry else { return }
        records = records.filter { $0.value.expires > uptime }
        nextExpiry = records.values.map(\.expires).min() ?? .infinity
    }

    func spriteMood(uptime: TimeInterval) -> Mood {
        if running > 0 { return .thinking }
        return records.values.filter { uptime - $0.updatedUptime < 8 }
            .max(by: { $0.updatedUptime < $1.updatedUptime })?.mood ?? .idle
    }

    var groups: [ActivityGroup] {
        Dictionary(grouping: records.values, by: \.group).map { k, v in
            let sessions = v.sorted {
                if ($0.mood == .thinking) != ($1.mood == .thinking) { return $0.mood == .thinking }
                return $0.updated > $1.updated
            }
            return ActivityGroup(id: k, label: sessions.first?.workspace ?? "工作区", sessions: sessions)
        }.sorted {
            let a = $0.sessions.first?.mood == .thinking
            let b = $1.sessions.first?.mood == .thinking
            if a != b { return a }
            if $0.label != $1.label { return $0.label.localizedStandardCompare($1.label) == .orderedAscending }
            return $0.id < $1.id
        }
    }
}

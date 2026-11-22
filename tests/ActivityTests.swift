import Foundation

@main
struct ActivityTests {
    static func main() {
        let activity = LiveActivity()
        let epoch = Date(timeIntervalSince1970: 0)
        let tag = WorkspaceTag(group: "fixture-group", label: "峡湾")

        func record(_ seconds: TimeInterval, _ mood: Mood, tag: WorkspaceTag? = nil) {
            _ = activity.record("fixture", mood: mood, tag: tag,
                                date: epoch.addingTimeInterval(seconds), uptime: seconds)
        }

        record(0, .thinking, tag: tag)
        record(7, .thinking)
        precondition(activity.running == 1)
        precondition(activity.records["fixture"]?.duration(at: epoch + 8) == 8)
        record(10, .done)
        record(13, .done)
        precondition(activity.running == 0)
        precondition(activity.groups.first?.label == "峡湾")
        precondition(activity.records["fixture"]?.duration(at: epoch + 20) == 10)
        precondition(activity.records["fixture"]?.updated == epoch + 13)

        record(21, .thinking)
        record(28, .error)
        precondition(activity.records["fixture"]?.duration(at: epoch + 30) == 7)
        activity.expire(28 + 3600)
        precondition(activity.records.isEmpty)
    }
}

import { useEffect, useMemo, useState } from "react";
import toast from "react-hot-toast";
import { api } from "../services/api";

export default function NotificationsPage() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [busyReadAll, setBusyReadAll] = useState(false);

  const unreadCount = useMemo(
    () => items.reduce((count, item) => count + (item?.is_read ? 0 : 1), 0),
    [items]
  );

  const loadNotifications = async (withLoader = true) => {
    if (withLoader) setLoading(true);
    setError("");
    try {
      const { data } = await api.get("/notifications/me", { params: { limit: 50 } });
      setItems(data.notifications || []);
    } catch (err) {
      setError(err?.response?.data?.detail || "Failed to load notifications.");
    } finally {
      if (withLoader) setLoading(false);
    }
  };

  const markAllRead = async () => {
    if (busyReadAll || unreadCount === 0) return;
    setBusyReadAll(true);
    try {
      await api.post("/notifications/read-all");
      setItems((prev) => prev.map((item) => ({ ...item, is_read: true })));
      toast.success("All notifications marked as read");
    } catch (err) {
      setError(err?.response?.data?.detail || "Failed to mark all notifications as read.");
      toast.error("Could not mark all as read");
    } finally {
      setBusyReadAll(false);
    }
  };

  const markOneRead = async (item) => {
    if (!item?.id || item?.is_read) return;
    try {
      await api.post(`/notifications/${encodeURIComponent(item.id)}/read`);
      setItems((prev) => prev.map((entry) => (entry.id === item.id ? { ...entry, is_read: true } : entry)));
    } catch {
      // Keep list interactive even if single mark-read fails.
      toast.error("Could not mark notification");
    }
  };

  useEffect(() => {
    loadNotifications();
    const id = setInterval(() => {
      loadNotifications(false);
    }, 8000);
    return () => clearInterval(id);
  }, []);

  return (
    <section className="page-enter space-y-4 pb-20 md:pb-4">
      <div className="page-hero flex items-start justify-between gap-3">
        <div>
          <h1 className="text-3xl font-bold tracking-tight dark:text-white">Notifications</h1>
          <p className="page-subtle-text">Realtime alerts from your social graph.</p>
          <p className="mt-1 text-xs font-semibold text-emerald-700">
            {unreadCount > 0 ? `${unreadCount} unread` : "All caught up"}
          </p>
        </div>
        <button
          onClick={markAllRead}
          disabled={busyReadAll || unreadCount === 0}
          className="ui-button-secondary disabled:opacity-60"
        >
          {busyReadAll ? "Marking..." : "Mark all read"}
        </button>
      </div>

      {error && <p className="rounded-xl bg-rose-100 px-3 py-2 text-sm text-rose-700 dark:bg-rose-950 dark:text-rose-300">{error}</p>}
      {loading ? (
        <div className="space-y-3">
          {[0, 1, 2, 3].map((idx) => (
            <div key={`notif-skeleton-${idx}`} className="card-surface p-4">
              <div className="flex items-start justify-between gap-2">
                <div className="w-full space-y-2">
                  <div className="skeleton h-3 w-5/6" />
                  <div className="skeleton h-3 w-1/3" />
                </div>
                <div className="skeleton h-2.5 w-2.5 rounded-full" />
              </div>
            </div>
          ))}
        </div>
      ) : null}

      <div className="space-y-3">
        {items.map((n, idx) => (
          <article
            key={`${n.id || n.created}-${idx}`}
            onClick={() => markOneRead(n)}
            className={`card-surface card-enter cursor-pointer border p-4 transition duration-200 hover:-translate-y-0.5 hover:shadow-xl ${
              n.is_read ? "border-slate-200" : "border-teal-300 bg-teal-50/50 dark:bg-teal-950/40"
            }`}
            style={{ animationDelay: `${idx * 45}ms` }}
          >
            <div className="flex items-start justify-between gap-2">
              <p className="text-sm text-slate-800 dark:text-slate-100">{n.title}</p>
              {!n.is_read ? (
                <span className="mt-0.5 inline-flex h-2.5 w-2.5 rounded-full bg-emerald-600" />
              ) : null}
            </div>
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{new Date(n.created).toLocaleString()}</p>
          </article>
        ))}
      </div>

      {!loading && items.length === 0 ? (
        <div className="empty-state-card">
          <p className="page-subtle-text">No notifications yet.</p>
        </div>
      ) : null}
    </section>
  );
}

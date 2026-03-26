import { useEffect, useState } from "react";
import { api } from "../services/api";

export default function ExplorePage() {
  const [query, setQuery] = useState("");
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadUsers = async (search = "") => {
    setLoading(true);
    setError("");
    try {
      const { data } = await api.get("/users", { params: { query: search, limit: 20, offset: 0 } });
      setUsers(data.users || []);
    } catch (err) {
      setError(err?.response?.data?.detail || "Failed to load users.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadUsers();
  }, []);

  const toggleFollow = async (user) => {
    try {
      if (user.is_following) {
        await api.post(`/unfollow/${encodeURIComponent(user.email)}`);
      } else {
        await api.post(`/follow/${encodeURIComponent(user.email)}`);
      }
      await loadUsers(query);
    } catch (err) {
      setError(err?.response?.data?.detail || "Follow action failed.");
    }
  };

  const onSearch = async (e) => {
    e.preventDefault();
    await loadUsers(query);
  };

  return (
    <section className="page-enter space-y-4 pb-20 md:pb-4">
      <div className="page-hero">
        <h1 className="text-3xl font-bold tracking-tight dark:text-white">Explore</h1>
        <p className="page-subtle-text">Discover creators, collaborators, and communities.</p>
      </div>

      <form onSubmit={onSearch} className="card-surface flex flex-col gap-2 p-3 sm:flex-row">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search by name or email"
          className="ui-input"
        />
        <button className="brand-button px-4 py-2">Search</button>
      </form>

      {error && <p className="rounded-xl bg-rose-100 px-3 py-2 text-sm text-rose-700 dark:bg-rose-950 dark:text-rose-300">{error}</p>}
      {loading ? (
        <div className="space-y-3">
          {[0, 1, 2, 3].map((idx) => (
            <div key={`explore-skeleton-${idx}`} className="card-surface flex items-center justify-between p-4">
              <div className="space-y-2">
                <div className="skeleton h-3 w-24" />
                <div className="skeleton h-3 w-40" />
                <div className="skeleton h-3 w-28" />
              </div>
              <div className="skeleton h-8 w-20 rounded-lg" />
            </div>
          ))}
        </div>
      ) : null}

      <div className="space-y-3">
        {users.map((u, idx) => (
          <article
            key={u.email}
            className="card-surface card-enter flex items-center justify-between p-4 transition duration-200 hover:-translate-y-0.5 hover:shadow-xl"
            style={{ animationDelay: `${idx * 45}ms` }}
          >
            <div>
              <h3 className="text-sm font-bold text-slate-900 dark:text-white">{u.name}</h3>
              <p className="text-xs text-slate-600 dark:text-slate-400">{u.email}</p>
              <p className="text-xs text-slate-700 dark:text-slate-300">
                {u.followers_count} followers • {u.following_count} following
              </p>
            </div>
            <button
              onClick={() => toggleFollow(u)}
              className={`rounded-lg px-3 py-1.5 text-xs font-bold ${
                u.is_following
                  ? "border border-slate-300 bg-white text-slate-700 hover:bg-slate-50 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
                  : "bg-gradient-to-r from-teal-700 to-teal-500 text-white dark:from-teal-600 dark:to-teal-400"
              }`}
            >
              {u.is_following ? "Following" : "Follow"}
            </button>
          </article>
        ))}
      </div>

      {!loading && users.length === 0 ? (
        <div className="empty-state-card">
          <p className="page-subtle-text">No users found. Try another name or email.</p>
        </div>
      ) : null}
    </section>
  );
}

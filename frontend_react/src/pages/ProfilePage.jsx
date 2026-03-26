import { useEffect, useState } from "react";
import { api } from "../services/api";
import { useAuth } from "../state/AuthContext";

export default function ProfilePage() {
  const { user } = useAuth();
  const [social, setSocial] = useState({ followers: [], following: [] });
  const [followers, setFollowers] = useState([]);
  const [following, setFollowing] = useState([]);
  const [inviteSummary, setInviteSummary] = useState(null);
  const [myPosts, setMyPosts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadData = async () => {
    setLoading(true);
    setError("");
    try {
      const [socialRes, followersRes, followingRes, postsRes] = await Promise.all([
        api.get("/users/me/social"),
        api.get("/users/me/followers"),
        api.get("/users/me/following"),
        api.get("/posts"),
      ]);
      const inviteRes = await api.get("/growth/invite/me");
      setSocial(socialRes.data || { followers: [], following: [] });
      setFollowers(followersRes?.data?.users || []);
      setFollowing(followingRes?.data?.users || []);
      setInviteSummary(inviteRes?.data || null);
      const allPosts = postsRes.data.posts || [];
      setMyPosts(
        allPosts.filter(
          (p) => p.author_email === user?.email || (!p.author_email && p.author === user?.name)
        )
      );
    } catch (err) {
      setError(err?.response?.data?.detail || "Failed to load profile.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [user?.email]);

  const copyInviteLink = async () => {
    const link = String(inviteSummary?.invite_link || "").trim();
    if (!link) return;
    try {
      await navigator.clipboard.writeText(link);
    } catch {
      // Clipboard can fail on some insecure origins.
    }
  };

  return (
    <section className="page-enter space-y-4 pb-20 md:pb-4">
      <div className="page-hero">
        <h1 className="text-3xl font-bold tracking-tight dark:text-white">{user?.name || "Profile"}</h1>
        <p className="text-sm text-slate-600 dark:text-slate-400">{user?.email}</p>
        <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3">
          <div className="card-surface-soft p-3">
            <p className="text-xs text-slate-600 dark:text-slate-400">Followers</p>
            <p className="text-xl font-bold dark:text-white">{social.followers?.length || 0}</p>
          </div>
          <div className="card-surface-soft p-3">
            <p className="text-xs text-slate-600 dark:text-slate-400">Following</p>
            <p className="text-xl font-bold dark:text-white">{social.following?.length || 0}</p>
          </div>
          <div className="card-surface-soft col-span-2 p-3 sm:col-span-1">
            <p className="text-xs text-slate-600 dark:text-slate-400">Role</p>
            <p className="text-xl font-bold capitalize dark:text-white">{user?.role || "user"}</p>
          </div>
        </div>
      </div>

      {error && <p className="rounded-xl bg-rose-100 px-3 py-2 text-sm text-rose-700 dark:bg-rose-950 dark:text-rose-300">{error}</p>}
      {loading ? (
        <div className="grid gap-4 lg:grid-cols-2">
          <div className="card-surface space-y-3 p-5 lg:col-span-2">
            <div className="skeleton h-4 w-40" />
            <div className="skeleton h-4 w-full" />
            <div className="skeleton h-4 w-2/3" />
          </div>
          <div className="card-surface space-y-3 p-5">
            <div className="skeleton h-4 w-24" />
            <div className="skeleton h-4 w-full" />
            <div className="skeleton h-4 w-3/4" />
          </div>
          <div className="card-surface space-y-3 p-5">
            <div className="skeleton h-4 w-24" />
            <div className="skeleton h-4 w-full" />
            <div className="skeleton h-4 w-3/4" />
          </div>
        </div>
      ) : null}

      <div className="card-surface p-5">
        <h2 className="text-xl font-bold dark:text-white">Invite Friends</h2>
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
          Bring 3 friends to unlock the referral-starter badge.
        </p>
        <div className="mt-3 rounded-xl border border-slate-200 p-3 dark:border-slate-700 dark:bg-slate-800/50">
          <p className="text-xs text-slate-600 dark:text-slate-400">Your code</p>
          <p className="text-lg font-bold tracking-wide text-slate-900 dark:text-white">
            {inviteSummary?.invite_code || "-"}
          </p>
          <p className="mt-2 text-xs text-slate-600 dark:text-slate-400 break-all">
            {inviteSummary?.invite_link || "Invite link will appear here"}
          </p>
          <div className="mt-3 flex items-center gap-2">
            <button
              type="button"
              onClick={copyInviteLink}
              className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 transition hover:bg-slate-50 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
            >
              Copy Link
            </button>
            <p className="text-xs font-semibold text-teal-700 dark:text-teal-400">
              Invites: {Number(inviteSummary?.invites_count || 0)} / 3
            </p>
          </div>
          {Array.isArray(inviteSummary?.badges) && inviteSummary.badges.length > 0 ? (
            <p className="mt-2 text-xs font-semibold text-amber-700 dark:text-amber-400">
              Badges: {inviteSummary.badges.join(", ")}
            </p>
          ) : null}
        </div>
      </div>

      <div className="card-surface p-5">
        <h2 className="text-xl font-bold dark:text-white">My Recent Posts</h2>
        <div className="mt-3 space-y-3">
          {myPosts.map((post) => (
            <article key={post.id} className="rounded-xl border border-slate-200 p-3 dark:border-slate-700 dark:bg-slate-800/50">
              <p className="text-sm text-slate-800 dark:text-slate-100">{post.content}</p>
              <p className="mt-2 text-xs text-slate-600 dark:text-slate-400">{new Date(post.created).toLocaleString()}</p>
            </article>
          ))}
        </div>
        {!loading && myPosts.length === 0 ? (
          <p className="mt-3 text-sm text-slate-600 dark:text-slate-400">No posts yet.</p>
        ) : null}
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <section className="card-surface p-5">
          <h2 className="text-xl font-bold dark:text-white">Followers</h2>
          <div className="mt-3 space-y-2">
            {followers.map((item) => (
              <article key={item.email} className="rounded-xl border border-slate-200 p-3 dark:border-slate-700 dark:bg-slate-800/50">
                <p className="text-sm font-semibold text-slate-900 dark:text-white">{item.name}</p>
                <p className="text-xs text-slate-600 dark:text-slate-400">{item.email}</p>
              </article>
            ))}
          </div>
          {!loading && followers.length === 0 ? (
            <p className="mt-3 text-sm text-slate-600 dark:text-slate-400">No followers yet.</p>
          ) : null}
        </section>

        <section className="card-surface p-5">
          <h2 className="text-xl font-bold dark:text-white">Following</h2>
          <div className="mt-3 space-y-2">
            {following.map((item) => (
              <article key={item.email} className="rounded-xl border border-slate-200 p-3 dark:border-slate-700 dark:bg-slate-800/50">
                <p className="text-sm font-semibold text-slate-900 dark:text-white">{item.name}</p>
                <p className="text-xs text-slate-600 dark:text-slate-400">{item.email}</p>
              </article>
            ))}
          </div>
          {!loading && following.length === 0 ? (
            <p className="mt-3 text-sm text-slate-600 dark:text-slate-400">Not following anyone yet.</p>
          ) : null}
        </section>
      </div>
    </section>
  );
}

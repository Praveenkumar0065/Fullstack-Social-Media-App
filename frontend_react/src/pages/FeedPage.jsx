import { useEffect, useMemo, useState } from "react";
import toast from "react-hot-toast";
import Composer from "../components/Composer";
import PostCard from "../components/PostCard";
import { api } from "../services/api";
import { useAuth } from "../state/AuthContext";

export default function FeedPage() {
  const { user } = useAuth();
  const [posts, setPosts] = useState([]);
  const [commentsByPost, setCommentsByPost] = useState({});
  const [loading, setLoading] = useState(true);
  const [posting, setPosting] = useState(false);
  const [error, setError] = useState("");

  const myName = useMemo(() => user?.name || "", [user]);
  const myEmail = useMemo(() => String(user?.email || "").toLowerCase(), [user]);

  const loadPosts = async ({ showLoader = true } = {}) => {
    if (showLoader) setLoading(true);
    setError("");
    try {
      const { data } = await api.get("/posts");
      const nextPosts = data.posts || [];
      setPosts(nextPosts);

      const commentEntries = await Promise.all(
        nextPosts.map(async (post) => {
          try {
            const response = await api.get(`/comments/${post.id}`);
            return [post.id, response?.data?.comments || []];
          } catch {
            return [post.id, []];
          }
        })
      );
      setCommentsByPost(Object.fromEntries(commentEntries));
    } catch (err) {
      setError(err?.response?.data?.detail || "Failed to load posts.");
    } finally {
      if (showLoader) setLoading(false);
    }
  };

  useEffect(() => {
    loadPosts();
  }, []);

  const createPost = async (content) => {
    setPosting(true);
    setError("");
    try {
      await api.post("/posts", { content, media: "" });
      await loadPosts({ showLoader: false });
      toast.success("Post published");
    } catch (err) {
      setError(err?.response?.data?.detail || "Failed to create post.");
      toast.error("Failed to publish post");
    } finally {
      setPosting(false);
    }
  };

  const likePost = async (postId) => {
    try {
      const { data } = await api.post(`/posts/${postId}/like`);
      setPosts((prev) => prev.map((p) => (p.id === postId ? data : p)));
    } catch (err) {
      setError(err?.response?.data?.detail || "Failed to like post.");
      toast.error("Could not like post");
    }
  };

  const toggleSavePost = async (postId, shouldSave) => {
    try {
      const { data } = await api.post(`/posts/${postId}/${shouldSave ? "save" : "unsave"}`);
      setPosts((prev) => prev.map((p) => (p.id === postId ? data : p)));
      toast.success(shouldSave ? "Saved" : "Removed from saved");
    } catch (err) {
      setError(err?.response?.data?.detail || "Failed to update saved state.");
      toast.error("Could not update save state");
    }
  };

  const commentOnPost = async (postId, comment, parentId = "") => {
    try {
      const { data } = await api.post(`/comments`, {
        post_id: postId,
        content: comment,
        parent_id: parentId
      });
      setCommentsByPost((prev) => ({
        ...prev,
        [postId]: [...(prev[postId] || []), data]
      }));
    } catch (err) {
      setError(err?.response?.data?.detail || "Failed to add comment.");
      toast.error("Comment failed");
    }
  };

  const likeComment = async (postId, commentId) => {
    try {
      const { data } = await api.post(`/comments/${commentId}/like`);
      setCommentsByPost((prev) => ({
        ...prev,
        [postId]: (prev[postId] || []).map((entry) => (entry.id === commentId ? data : entry))
      }));
    } catch (err) {
      setError(err?.response?.data?.detail || "Failed to like comment.");
    }
  };

  const deletePost = async (postId) => {
    try {
      await api.delete(`/posts/${postId}`);
      setPosts((prev) => prev.filter((p) => p.id !== postId));
      toast.success("Post deleted");
    } catch (err) {
      setError(err?.response?.data?.detail || "Failed to delete post.");
      toast.error("Delete failed");
    }
  };

  return (
    <section className="page-enter space-y-4 pb-20 md:pb-4">
      <div className="page-hero">
        <h1 className="text-3xl font-bold tracking-tight dark:text-white">Feed</h1>
        <p className="page-subtle-text">Fresh updates from your network in one premium stream.</p>
      </div>

      <Composer onSubmit={createPost} busy={posting} />

      {error && <p className="rounded-xl bg-rose-100 px-3 py-2 text-sm text-rose-700 dark:bg-rose-950 dark:text-rose-300">{error}</p>}

      {loading ? (
        <div className="space-y-4">
          {[0, 1, 2].map((idx) => (
            <div key={`feed-skeleton-${idx}`} className="card-surface space-y-3 p-4">
              <div className="skeleton h-4 w-1/3" />
              <div className="skeleton h-4 w-full" />
              <div className="skeleton h-4 w-5/6" />
              <div className="skeleton h-52 w-full rounded-xl" />
            </div>
          ))}
        </div>
      ) : null}

      {!loading && error && posts.length === 0 ? (
        <div className="empty-state-card">
          <p className="text-sm text-slate-700 dark:text-slate-200">Could not load your feed right now.</p>
          <button onClick={() => loadPosts()} className="brand-button mt-3">Retry</button>
        </div>
      ) : null}

      <div className="space-y-4">
        {posts.map((post, idx) => (
          <div key={post.id} className="card-enter" style={{ animationDelay: `${idx * 55}ms` }}>
            <PostCard
              post={post}
              onLike={likePost}
              onDelete={deletePost}
              onToggleSave={toggleSavePost}
              onAddComment={commentOnPost}
              onLikeComment={likeComment}
              comments={commentsByPost[post.id] || []}
              currentUserName={myName}
              currentUserEmail={myEmail}
            />
          </div>
        ))}
      </div>

      {!loading && posts.length === 0 ? (
        <div className="empty-state-card">
          <p className="page-subtle-text">No posts yet. Be the first to share.</p>
        </div>
      ) : null}
    </section>
  );
}

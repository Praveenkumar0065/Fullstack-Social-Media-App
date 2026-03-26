import { useState } from "react";
import { motion } from "framer-motion";

export default function PostCard({
  post,
  onLike,
  onDelete,
  onToggleSave,
  onAddComment,
  onLikeComment,
  comments,
  currentUserName,
  currentUserEmail
}) {
  const normalizedCurrentEmail = String(currentUserEmail || "").toLowerCase();
  const normalizedPostEmail = String(post.author_email || "").toLowerCase();
  const canDelete =
    (normalizedPostEmail && normalizedPostEmail === normalizedCurrentEmail) ||
    (!normalizedPostEmail && post.author === currentUserName);
  const [comment, setComment] = useState("");
  const [replyTo, setReplyTo] = useState("");
  const [replyText, setReplyText] = useState("");

  const legacyComments = Array.isArray(post.comments)
    ? post.comments.map((entry, idx) => ({
        id: `legacy-${post.id}-${idx}`,
        parent_id: "",
        author: "",
        content: String(entry),
        likes: 0
      }))
    : [];
  const postComments = Array.isArray(comments) && comments.length > 0 ? comments : legacyComments;
  const parentComments = postComments.filter((entry) => !String(entry.parent_id || "").trim());
  const repliesByParent = postComments.reduce((acc, entry) => {
    const parentId = String(entry.parent_id || "").trim();
    if (!parentId) return acc;
    if (!acc[parentId]) acc[parentId] = [];
    acc[parentId].push(entry);
    return acc;
  }, {});

  const submitComment = async (event) => {
    event.preventDefault();
    const trimmed = comment.trim();
    if (!trimmed) return;
    await onAddComment(post.id, trimmed, "");
    setComment("");
  };

  const submitReply = async (event) => {
    event.preventDefault();
    const trimmed = replyText.trim();
    if (!trimmed || !replyTo) return;
    await onAddComment(post.id, trimmed, replyTo);
    setReplyText("");
    setReplyTo("");
  };

  return (
    <motion.article
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.22 }}
      className="card-surface overflow-hidden p-4 transition duration-200 hover:-translate-y-0.5 hover:shadow-xl"
    >
      <div className="mb-3 flex items-center justify-between">
        <div>
          <h3 className="text-sm font-bold text-slate-900 dark:text-white">{post.author || "Unknown"}</h3>
          <p className="text-[11px] font-semibold uppercase tracking-wide text-teal-700 dark:text-teal-400">Community Update</p>
        </div>
        <p className="text-xs text-slate-600 dark:text-slate-400">
          {post.created ? new Date(post.created).toLocaleString() : "now"}
        </p>
      </div>
      <p className="mb-4 whitespace-pre-wrap text-sm leading-relaxed text-slate-800 dark:text-slate-100">{post.content}</p>

      {post.image_url || post.media ? (
        <div className="mb-4 overflow-hidden rounded-xl border border-slate-200 dark:border-slate-700">
          <img
            src={String(post.image_url || post.media || "").trim()}
            alt="Post"
            className="max-h-96 w-full object-cover"
            loading="lazy"
          />
        </div>
      ) : null}

      <div className="flex flex-wrap items-center gap-2">
        <motion.button
          onClick={() => onLike(post.id)}
          whileTap={{ scale: 1.08 }}
          whileHover={{ scale: 1.02 }}
          className="rounded-lg border border-teal-300 bg-teal-50 px-3 py-1.5 text-xs font-bold text-teal-700 transition hover:bg-teal-100 dark:border-teal-700 dark:bg-teal-950/40 dark:text-teal-400 dark:hover:bg-teal-900/50"
        >
          <span className="inline-flex items-center gap-1">
            <motion.span whileTap={{ scale: 1.3 }} whileHover={{ scale: 1.12 }}>
              ❤
            </motion.span>
            <span>Like ({post.likes || 0})</span>
          </span>
        </motion.button>
        <button
          onClick={() => onToggleSave(post.id, !post.saved)}
          className="rounded-lg border border-amber-300 bg-amber-50 px-3 py-1.5 text-xs font-bold text-amber-700 transition hover:bg-amber-100 dark:border-amber-700 dark:bg-amber-950/40 dark:text-amber-400 dark:hover:bg-amber-900/50"
        >
          {post.saved ? "Saved" : "Save"}
        </button>
        {canDelete && (
          <button
            onClick={() => onDelete(post.id)}
            className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-bold text-slate-700 transition hover:bg-slate-50 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
          >
            Delete
          </button>
        )}
      </div>

      <div className="mt-3 rounded-xl border border-slate-200 bg-slate-50/70 p-3 dark:border-slate-700 dark:bg-slate-800/50">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-600 dark:text-slate-400">Comments</p>
        {parentComments.length > 0 ? (
          <ul className="mt-2 space-y-1">
            {parentComments.map((entry) => {
              const isLegacy = String(entry.id || "").startsWith("legacy-");
              return (
                <li key={entry.id} className="rounded-lg border border-slate-200 bg-white p-2 text-xs text-slate-700 dark:border-slate-700 dark:bg-slate-800/50 dark:text-slate-300">
                <div className="flex items-center justify-between gap-2">
                  <p>
                    <span className="font-semibold">{entry.author || "User"}</span> {entry.content}
                  </p>
                  <div className="flex items-center gap-2">
                    {!isLegacy ? (
                      <>
                        <button
                          onClick={() => onLikeComment(post.id, entry.id)}
                          className="text-xs font-semibold text-rose-600 hover:text-rose-700 dark:text-rose-400 dark:hover:text-rose-300"
                        >
                          Like {entry.likes || 0}
                        </button>
                        <button
                          onClick={() => {
                            setReplyTo(entry.id);
                            setReplyText("");
                          }}
                          className="text-xs font-semibold text-sky-700 hover:text-sky-800 dark:text-sky-400 dark:hover:text-sky-300"
                        >
                          Reply
                        </button>
                      </>
                    ) : null}
                  </div>
                </div>
                {(repliesByParent[entry.id] || []).length > 0 ? (
                  <ul className="mt-2 space-y-1 border-l border-slate-200 pl-3 dark:border-slate-700">
                    {(repliesByParent[entry.id] || []).map((reply) => (
                      <li key={reply.id} className="rounded bg-slate-50 p-1.5 dark:bg-slate-700/50">
                        <div className="flex items-center justify-between gap-2">
                          <p className="dark:text-slate-300">
                            <span className="font-semibold">{reply.author || "User"}</span> {reply.content}
                          </p>
                          <button
                            onClick={() => onLikeComment(post.id, reply.id)}
                            className="text-xs font-semibold text-rose-600 hover:text-rose-700 dark:text-rose-400 dark:hover:text-rose-300"
                          >
                            Like {reply.likes || 0}
                          </button>
                        </div>
                      </li>
                    ))}
                  </ul>
                ) : null}
                {replyTo === entry.id ? (
                  <form onSubmit={submitReply} className="mt-2 flex gap-2">
                    <input
                      value={replyText}
                      onChange={(e) => setReplyText(e.target.value)}
                      placeholder="Write a reply"
                      className="w-full rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs text-slate-900 outline-none focus:border-teal-500 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-300 dark:placeholder:text-slate-500 dark:focus:border-teal-400"
                    />
                    <button
                      type="submit"
                      disabled={!replyText.trim()}
                      className="rounded-lg bg-slate-900 px-3 py-1.5 text-xs font-bold text-white transition hover:bg-slate-800 disabled:opacity-60 dark:bg-slate-700 dark:hover:bg-slate-600"
                    >
                      Reply
                    </button>
                  </form>
                ) : null}
                </li>
              );
            })}
          </ul>
        ) : (
          <p className="mt-2 text-xs text-slate-600 dark:text-slate-400">No comments yet.</p>
        )}

        <form onSubmit={submitComment} className="mt-2 flex gap-2">
          <input
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder="Write a comment"
            className="w-full rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs text-slate-900 outline-none focus:border-teal-500 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-300 dark:placeholder:text-slate-500 dark:focus:border-teal-400"
          />
          <button
            type="submit"
            disabled={!comment.trim()}
            className="rounded-lg bg-slate-900 px-3 py-1.5 text-xs font-bold text-white transition hover:bg-slate-800 disabled:opacity-60 dark:bg-slate-700 dark:hover:bg-slate-600"
          >
            Add
          </button>
        </form>
      </div>
    </motion.article>
  );
}

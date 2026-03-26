import { useState } from "react";

export default function Composer({ onSubmit, busy }) {
  const [text, setText] = useState("");

  const handleSubmit = async (event) => {
    event.preventDefault();
    const trimmed = text.trim();
    if (!trimmed || busy) return;
    await onSubmit(trimmed);
    setText("");
  };

  return (
    <form onSubmit={handleSubmit} className="card-surface p-4">
      <label htmlFor="post-text" className="mb-2 block text-sm font-semibold text-slate-700 dark:text-slate-300">
        Share an update
      </label>
      <textarea
        id="post-text"
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="What are you building today?"
        rows={4}
        className="w-full rounded-xl border border-slate-300 bg-white p-3 text-sm text-slate-900 outline-none transition focus:border-teal-500 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-300 dark:placeholder:text-slate-500 dark:focus:border-teal-400"
      />
      <div className="mt-3 flex justify-end">
        <button
          type="submit"
          disabled={busy || !text.trim()}
          className="brand-button disabled:opacity-60"
        >
          {busy ? "Posting..." : "Post"}
        </button>
      </div>
    </form>
  );
}

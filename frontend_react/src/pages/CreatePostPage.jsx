import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../services/api";

export default function CreatePostPage() {
  const navigate = useNavigate();
  const [content, setContent] = useState("");
  const [imageFile, setImageFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const canSubmit = useMemo(() => content.trim().length > 0 && !submitting, [content, submitting]);

  const onFileChange = (event) => {
    const file = event.target.files?.[0] || null;
    setImageFile(file);
    if (file) {
      setPreviewUrl(URL.createObjectURL(file));
    }
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!canSubmit) return;

    setSubmitting(true);
    setError("");
    try {
      let imageUrl = "";
      
      // Upload image if file selected
      if (imageFile) {
        const formData = new FormData();
        formData.append("file", imageFile);
        const uploadRes = await api.post("/upload", formData, {
          headers: { "Content-Type": "multipart/form-data" }
        });
        imageUrl = String(uploadRes.data?.url || "").trim();
      }

      // Create post with image URL
      await api.post("/posts", {
        content: content.trim(),
        media: "",
        image_url: imageUrl
      });
      navigate("/feed", { replace: true });
    } catch (err) {
      setError(err?.response?.data?.detail || "Failed to create post.");
    } finally {
      setSubmitting(false);
    }
  };

  // Cleanup blob URLs on unmount
  useEffect(() => {
    return () => {
      if (previewUrl) {
        URL.revokeObjectURL(previewUrl);
      }
    };
  }, [previewUrl]);

  return (
    <section className="page-enter space-y-4 pb-20 md:pb-4">
      <div className="page-hero">
        <h1 className="text-3xl font-bold tracking-tight">Create Post</h1>
        <p className="text-sm text-slate-600">Share your thoughts and upload an image with your followers.</p>
      </div>

      <form onSubmit={handleSubmit} className="card-surface card-enter space-y-4 p-5">
        <label className="block">
          <span className="mb-1 block text-sm font-semibold text-slate-700">Caption</span>
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder="What are you building today?"
            rows={5}
            className="w-full rounded-xl border border-slate-300 p-3 text-sm outline-none transition focus:border-teal-500"
          />
        </label>

        <label className="block">
          <span className="mb-1 block text-sm font-semibold text-slate-700">Upload Image (optional)</span>
          <input
            type="file"
            accept="image/*"
            onChange={onFileChange}
            className="w-full rounded-xl border border-slate-300 p-3 text-sm outline-none transition focus:border-teal-500"
          />
          <p className="mt-1 text-xs text-slate-500">Supported: jpg, png, webp, gif up to 5MB.</p>
        </label>

        {previewUrl ? (
          <div className="overflow-hidden rounded-xl border border-slate-200">
            <img
              src={previewUrl}
              alt="Post preview"
              className="max-h-72 w-full object-cover"
            />
          </div>
        ) : null}

        {error ? <p className="rounded-xl bg-rose-100 px-3 py-2 text-sm text-rose-700">{error}</p> : null}

        <button
          type="submit"
          disabled={!canSubmit}
          className="brand-button w-full disabled:opacity-60"
        >
          {submitting ? "Posting..." : "Post"}
        </button>
      </form>
    </section>
  );
}
import { useEffect, useMemo, useRef, useState } from "react";
import { API_BASE, api } from "../services/api";
import { useAuth } from "../state/AuthContext";

export default function MessagesPage() {
  const { token, user } = useAuth();
  const [messages, setMessages] = useState([]);
  const [users, setUsers] = useState([]);
  const [recentRooms, setRecentRooms] = useState([]);
  const [statusMap, setStatusMap] = useState({});
  const [room, setRoom] = useState("global");
  const [roomInput, setRoomInput] = useState("global");
  const [roomMessages, setRoomMessages] = useState([]);
  const [draft, setDraft] = useState("");
  const [wsState, setWsState] = useState("disconnected");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const socketRef = useRef(null);
  const bottomRef = useRef(null);

  const normalizeMessage = (raw) => ({
    id: String(raw?.id || ""),
    from_user: String(raw?.from_user || "room"),
    text: String(raw?.text || ""),
    delivered_to: Array.isArray(raw?.delivered_to) ? raw.delivered_to : [],
    seen_by: Array.isArray(raw?.seen_by) ? raw.seen_by : [],
    created: Number(raw?.created || Date.now()),
  });

  const sendSeenAck = (msg) => {
    const mine = String(user?.email || "").toLowerCase().trim();
    if (!mine) return;
    if (String(msg?.from_user || "").toLowerCase() === mine) return;
    if (!msg?.id) return;
    if (!socketRef.current || socketRef.current.readyState !== WebSocket.OPEN) return;
    socketRef.current.send(
      JSON.stringify({
        type: "seen",
        message_id: msg.id,
      })
    );
  };

  const wsUrl = useMemo(() => {
    if (!token) return "";
    const apiOrigin = API_BASE.replace(/\/api$/, "");
    const wsOrigin = apiOrigin.replace(/^http/, "ws");
    return `${wsOrigin}/ws/chat?token=${encodeURIComponent(token)}&room=${encodeURIComponent(room)}`;
  }, [token, room]);

  const loadMessages = async () => {
    setLoading(true);
    setError("");
    try {
      const { data } = await api.get("/messages/me");
      setMessages(data.messages || []);
    } catch (err) {
      setError(err?.response?.data?.detail || "Failed to load messages.");
    } finally {
      setLoading(false);
    }
  };

  const loadUsers = async () => {
    try {
      const { data } = await api.get("/users", { params: { limit: 100, offset: 0 } });
      setUsers(data.users || []);
    } catch (err) {
      setError(err?.response?.data?.detail || "Failed to load users.");
    }
  };

  const loadRecentRooms = async () => {
    try {
      const { data } = await api.get("/chat/rooms/recent", { params: { limit: 20 } });
      setRecentRooms(data?.rooms || []);
    } catch {
      // Keep page usable even if recent-room lookup fails.
    }
  };

  const loadStatuses = async () => {
    try {
      const { data } = await api.get("/users/status");
      setStatusMap(data || {});
    } catch {
      // Keep chat usable even if status polling fails.
    }
  };

  const loadRoomHistory = async (roomId) => {
    setError("");
    try {
      if (String(roomId || "").startsWith("dm:")) {
        await api.post(`/chat/rooms/${encodeURIComponent(roomId)}/read`);
      }
      const { data } = await api.get(`/chat/messages/${encodeURIComponent(roomId)}`, {
        params: { limit: 30 }
      });
      const normalized = (data.messages || []).map((m) => normalizeMessage(m));
      setRoomMessages(normalized);
    } catch (err) {
      setError(err?.response?.data?.detail || "Failed to load room history.");
    }
  };

  useEffect(() => {
    loadMessages();
    loadUsers();
    loadRecentRooms();
    loadStatuses();
  }, []);

  useEffect(() => {
    const id = setInterval(() => {
      loadStatuses();
    }, 5000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    loadRoomHistory(room);
    loadRecentRooms();
  }, [room]);

  useEffect(() => {
    if (!wsUrl) return;

    setWsState("connecting");
    const socket = new WebSocket(wsUrl);
    socketRef.current = socket;

    socket.onopen = () => {
      setWsState("connected");
      setError("");
    };

    socket.onmessage = (event) => {
      const raw = String(event.data || "").trim();
      if (!raw) return;

      if (raw.startsWith("{")) {
        try {
          const payload = JSON.parse(raw);
          if (payload?.type === "chat_message" && payload?.message) {
            const next = normalizeMessage(payload.message);
            setRoomMessages((prev) => {
              const withoutDuplicate = next.id ? prev.filter((m) => m.id !== next.id) : prev;
              return [...withoutDuplicate, next];
            });
            sendSeenAck(next);
            loadRecentRooms();
            return;
          }
          if (payload?.type === "chat_status" && payload?.message) {
            const updated = normalizeMessage(payload.message);
            setRoomMessages((prev) => prev.map((m) => (m.id && m.id === updated.id ? { ...m, ...updated } : m)));
            loadRecentRooms();
            return;
          }
        } catch {
          // Fall through to plain-text compatibility path.
        }
      }

      const divider = raw.indexOf(": ");
      const from_user = divider >= 0 ? raw.slice(0, divider) : "system";
      const text = divider >= 0 ? raw.slice(divider + 2) : raw;
      setRoomMessages((prev) => [
        ...prev,
        normalizeMessage({
          from_user,
          text,
          created: Date.now(),
        }),
      ]);
    };

    socket.onerror = () => {
      setWsState("error");
      setError("Live chat connection failed.");
    };

    socket.onclose = () => {
      setWsState("disconnected");
    };

    return () => {
      socket.close();
      socketRef.current = null;
    };
  }, [wsUrl]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    roomMessages.forEach((m) => sendSeenAck(m));
  }, [roomMessages]);

  const openRoom = (event) => {
    event.preventDefault();
    setRoom(roomInput.trim() || "global");
  };

  const openDmWith = (targetEmail) => {
    const mine = String(user?.email || "").toLowerCase().trim();
    const theirs = String(targetEmail || "").toLowerCase().trim();
    if (!mine || !theirs || mine === theirs) return;
    const members = [mine, theirs].sort();
    const nextRoom = `dm:${members[0]}|${members[1]}`;
    setRoom(nextRoom);
    setRoomInput(nextRoom);
  };

  const sendRoomMessage = (event) => {
    event.preventDefault();
    const body = draft.trim();
    if (!body) return;
    if (!socketRef.current || socketRef.current.readyState !== WebSocket.OPEN) {
      setError("Live chat is not connected yet.");
      return;
    }
    socketRef.current.send(body);
    setDraft("");
  };

  return (
    <section className="page-enter space-y-4 pb-20 md:pb-4">
      <div className="page-hero">
        <h1 className="text-3xl font-bold tracking-tight">Messages</h1>
        <p className="text-sm text-slate-600">Direct messaging with live status, seen ticks, and unread badges.</p>
      </div>

      {error && <p className="rounded-xl bg-rose-100 px-3 py-2 text-sm text-rose-700">{error}</p>}

      <div className="grid gap-4 lg:grid-cols-3">
        <section className="card-surface p-4">
          <h2 className="text-lg font-bold">Inbox</h2>
          {loading ? (
            <div className="mt-3 space-y-2">
              {[0, 1, 2].map((idx) => (
                <div key={`inbox-skeleton-${idx}`} className="rounded-xl border border-slate-200 bg-white p-3">
                  <div className="skeleton h-3 w-24" />
                  <div className="mt-2 skeleton h-3 w-full" />
                  <div className="mt-2 skeleton h-3 w-2/3" />
                </div>
              ))}
            </div>
          ) : null}
          <div className="mt-3 space-y-2">
            {messages.map((m, idx) => (
              <article key={`${m.created}-${idx}`} className="rounded-xl border border-slate-200 bg-white p-3">
                <p className="text-xs font-bold text-slate-700">{m.from_user}</p>
                <p className="text-sm text-slate-800">{m.text}</p>
                <p className="mt-1 text-xs text-slate-500">{new Date(m.created).toLocaleString()}</p>
              </article>
            ))}
          </div>
          {!loading && messages.length === 0 ? (
            <p className="mt-3 text-sm text-slate-600">No messages yet.</p>
          ) : null}
        </section>

        <section className="card-surface p-4">
          <h2 className="text-lg font-bold">Chats</h2>
          <p className="mt-1 text-xs text-slate-500">Select a user to open a direct room.</p>

          {loading ? (
            <div className="mt-3 space-y-2">
              {[0, 1, 2, 3].map((idx) => (
                <div key={`chat-skeleton-${idx}`} className="rounded-xl border border-slate-200 bg-white p-3">
                  <div className="flex items-center justify-between gap-3">
                    <div className="space-y-2">
                      <div className="skeleton h-3 w-24" />
                      <div className="skeleton h-3 w-36" />
                    </div>
                    <div className="skeleton h-5 w-10 rounded-full" />
                  </div>
                </div>
              ))}
            </div>
          ) : null}

          <div className="mt-3 space-y-2">
            {recentRooms.map((entry) => {
              const partner = String(entry.partner || "").toLowerCase();
              const presence = statusMap[partner] || { status: "offline", last_seen: null };
              const isOnline = presence.status === "online";
              const unreadCount = Number(entry.unread_count || 0);
              return (
                <button
                  key={`recent-${entry.room}`}
                  type="button"
                  onClick={() => {
                    setRoom(String(entry.room || "global"));
                    setRoomInput(String(entry.room || "global"));
                  }}
                  className="w-full rounded-xl border border-teal-200 bg-teal-50/40 p-3 text-left transition hover:bg-teal-50"
                >
                  <div className="flex items-center justify-between gap-3">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-semibold text-slate-900">{entry.partner}</p>
                      <p className="truncate text-xs text-slate-600">{entry.last_from}: {entry.last_text}</p>
                    </div>
                    <div className="shrink-0 text-right">
                      <p className="text-[11px] text-slate-500">
                        {entry.last_created ? new Date(entry.last_created).toLocaleTimeString() : ""}
                      </p>
                      {unreadCount > 0 ? (
                        <p className="mt-1 inline-flex min-w-5 items-center justify-center rounded-full bg-teal-600 px-1.5 py-0.5 text-[10px] font-bold text-white">
                          {unreadCount > 99 ? "99+" : unreadCount}
                        </p>
                      ) : null}
                      <p className={`text-[11px] font-semibold ${isOnline ? "text-emerald-600" : "text-slate-500"}`}>
                        {isOnline ? "Online" : "Offline"}
                      </p>
                    </div>
                  </div>
                </button>
              );
            })}
          </div>

          {recentRooms.length > 0 ? <p className="mt-3 text-xs font-semibold text-slate-500">All users</p> : null}

          <div className="mt-3 space-y-2">
            {users.map((chatUser) => {
              const email = String(chatUser.email || "").toLowerCase();
              const presence = statusMap[email] || { status: "offline", last_seen: null };
              const isOnline = presence.status === "online";
              return (
                <button
                  key={email}
                  type="button"
                  onClick={() => openDmWith(chatUser.email)}
                  className="w-full rounded-xl border border-slate-200 bg-white p-3 text-left transition hover:-translate-y-0.5 hover:bg-slate-50"
                >
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-slate-900">{chatUser.name || chatUser.email}</p>
                      <p className="text-xs text-slate-500">{chatUser.email}</p>
                    </div>
                    <div className="text-right">
                      <p className={`text-xs font-semibold ${isOnline ? "text-emerald-600" : "text-slate-500"}`}>
                        {isOnline ? "Online" : "Offline"}
                      </p>
                      {!isOnline && presence.last_seen ? (
                        <p className="text-[11px] text-slate-400">
                          Last seen {new Date(presence.last_seen).toLocaleTimeString()}
                        </p>
                      ) : null}
                    </div>
                  </div>
                </button>
              );
            })}
          </div>

          {users.length === 0 ? <p className="mt-3 text-sm text-slate-600">No users available.</p> : null}
        </section>

        <section className="card-surface p-4">
          <form onSubmit={openRoom} className="flex items-center justify-between gap-3">
            <h2 className="text-lg font-bold">Room History</h2>
            <input
              value={roomInput}
              onChange={(e) => setRoomInput(e.target.value)}
              className="w-40 rounded-lg border border-slate-300 px-3 py-1.5 text-sm outline-none transition focus:border-teal-500"
            />
            <button
              type="submit"
              className="rounded-lg bg-slate-900 px-3 py-1.5 text-xs font-bold text-white transition hover:bg-slate-800"
            >
              Open
            </button>
          </form>

          <p className="mt-2 text-xs text-slate-500">
            Room: <span className="font-semibold text-slate-700">{room}</span>
            {" | "}
            Live: <span className={`status-chip status-chip-${wsState}`}>{wsState}</span>
          </p>

          <div className="mt-3 max-h-[26rem] space-y-2 overflow-auto pr-1">
            {roomMessages.map((m, idx) => (
              <article
                key={`${m.created || idx}-${idx}`}
                className={`rounded-xl border p-3 ${
                  String(m.from_user || "").toLowerCase() === String(user?.email || "").toLowerCase()
                    ? "ml-10 border-teal-200 bg-teal-50"
                    : "mr-10 border-slate-200 bg-white"
                }`}
              >
                <p className="text-xs font-bold text-slate-700">{m.from_user || "room"}</p>
                <p className="text-sm text-slate-800">{m.text || ""}</p>
                <div className="mt-1 flex items-center justify-between gap-2 text-xs text-slate-500">
                  <span>{m.created ? new Date(m.created).toLocaleString() : "just now"}</span>
                  {String(m.from_user || "").toLowerCase() === String(user?.email || "").toLowerCase() ? (
                    <span className="font-semibold text-slate-500">
                      {(m.seen_by || []).length > 0 ? "\u2714\u2714 Seen" : (m.delivered_to || []).length > 0 ? "\u2714\u2714 Delivered" : "\u2714 Sent"}
                    </span>
                  ) : null}
                </div>
              </article>
            ))}
            <div ref={bottomRef} />
          </div>

          {roomMessages.length === 0 ? (
            <p className="mt-3 text-sm text-slate-600">No room history yet.</p>
          ) : null}

          <form onSubmit={sendRoomMessage} className="mt-3 flex gap-2">
            <input
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              placeholder="Type a live message"
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none transition focus:border-teal-500"
            />
            <button
              type="submit"
              disabled={!draft.trim()}
              className="rounded-lg bg-gradient-to-r from-teal-700 to-teal-500 px-4 py-2 text-sm font-bold text-white transition hover:brightness-105 disabled:opacity-60"
            >
              Send
            </button>
          </form>
        </section>
      </div>
    </section>
  );
}

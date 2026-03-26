import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Link, NavLink, useNavigate } from "react-router-dom";
import toast from "react-hot-toast";
import { api } from "../services/api";
import { useAuth } from "../state/AuthContext";

const navItems = [
  { to: "/feed", label: "Feed" },
  { to: "/create", label: "Create" },
  { to: "/explore", label: "Explore" },
  { to: "/notifications", label: "Notifications" },
  { to: "/messages", label: "Messages" },
  { to: "/profile", label: "Profile" }
];

export default function AppShell({ children }) {
  const navigate = useNavigate();
  const { user, token, logout } = useAuth();
  const [unreadNotifications, setUnreadNotifications] = useState(0);
  const [installPromptEvent, setInstallPromptEvent] = useState(null);
  const [theme, setTheme] = useState(() => {
    const stored = localStorage.getItem("theme");
    if (stored === "dark" || stored === "light") return stored;
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  });

  const loadUnreadNotifications = async () => {
    if (!token) {
      setUnreadNotifications(0);
      return;
    }
    try {
      const { data } = await api.get("/notifications/unread-count");
      setUnreadNotifications(Number(data?.unread_count || 0));
    } catch {
      // Keep shell usable even if count endpoint fails.
    }
  };

  useEffect(() => {
    loadUnreadNotifications();
    const id = setInterval(loadUnreadNotifications, 10000);
    return () => clearInterval(id);
  }, [token]);

  useEffect(() => {
    const isDark = theme === "dark";
    document.documentElement.classList.toggle("dark", isDark);
    localStorage.setItem("theme", theme);
  }, [theme]);

  useEffect(() => {
    const handleBeforeInstallPrompt = (event) => {
      event.preventDefault();
      setInstallPromptEvent(event);
    };
    const handleInstalled = () => {
      setInstallPromptEvent(null);
      toast.success("Pulsegram installed");
    };

    window.addEventListener("beforeinstallprompt", handleBeforeInstallPrompt);
    window.addEventListener("appinstalled", handleInstalled);
    return () => {
      window.removeEventListener("beforeinstallprompt", handleBeforeInstallPrompt);
      window.removeEventListener("appinstalled", handleInstalled);
    };
  }, []);

  const handleLogout = async () => {
    await logout();
    navigate("/login", { replace: true });
  };

  const toggleTheme = () => {
    setTheme((prev) => (prev === "dark" ? "light" : "dark"));
  };

  const installApp = async () => {
    if (!installPromptEvent) return;
    installPromptEvent.prompt();
    const choice = await installPromptEvent.userChoice;
    if (choice?.outcome === "accepted") {
      toast.success("Installing app");
    }
    setInstallPromptEvent(null);
  };

  const renderNavLabel = (item) => {
    if (item.to !== "/notifications") return item.label;
    return (
      <span className="inline-flex items-center gap-1.5">
        <span>{item.label}</span>
        {unreadNotifications > 0 ? (
          <motion.span
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ type: "spring", stiffness: 320, damping: 22 }}
            className="badge-pulse inline-flex min-w-5 items-center justify-center rounded-full bg-rose-600 px-1.5 py-0.5 text-[10px] font-bold text-white"
          >
            {unreadNotifications > 99 ? "99+" : unreadNotifications}
          </motion.span>
        ) : null}
      </span>
    );
  };

  return (
    <div className="app-frame">
      <header className="sticky top-0 z-20 border-b border-slate-200/80 bg-white/75 backdrop-blur-md dark:border-slate-700 dark:bg-slate-900/75">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-3 px-4 py-3">
          <Link to="/feed" className="group inline-flex items-center gap-2">
            <span className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-teal-700 to-teal-500 text-xs font-bold text-white">
              PG
            </span>
            <span className="text-xl font-bold tracking-tight text-slate-900 transition group-hover:text-teal-700 dark:text-white dark:group-hover:text-teal-400">
              Pulsegram
            </span>
          </Link>
          <nav className="hidden gap-1 md:flex">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `interactive rounded-lg px-3 py-2 text-sm font-semibold transition ${
                    isActive
                      ? "bg-gradient-to-r from-teal-700 to-teal-500 text-white shadow"
                      : "text-slate-700 hover:bg-white/90 hover:text-slate-900 dark:text-slate-300 dark:hover:bg-slate-800 dark:hover:text-white"
                  }`
                }
              >
                {renderNavLabel(item)}
              </NavLink>
            ))}
          </nav>
          <div className="flex items-center gap-3">
            <span className="hidden rounded-lg bg-slate-100/90 px-2.5 py-1 text-xs font-semibold text-slate-700 sm:block dark:bg-slate-800 dark:text-slate-300">
              {user?.email || "Signed in"}
            </span>
            <button
              onClick={toggleTheme}
              className="interactive rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm font-semibold text-slate-700 transition hover:border-slate-400 hover:bg-slate-50 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-300 dark:hover:border-slate-500 dark:hover:bg-slate-700"
            >
              {theme === "dark" ? "Light" : "Dark"}
            </button>
            {installPromptEvent ? (
              <button
                onClick={installApp}
                className="interactive rounded-lg border border-teal-300 bg-teal-50 px-3 py-1.5 text-sm font-semibold text-teal-700 transition hover:bg-teal-100 dark:border-teal-600 dark:bg-teal-950 dark:text-teal-300 dark:hover:bg-teal-900"
              >
                Install
              </button>
            ) : null}
            <button
              onClick={handleLogout}
              className="interactive rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm font-semibold text-slate-700 transition hover:border-slate-400 hover:bg-slate-50 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-300 dark:hover:border-slate-500 dark:hover:bg-slate-700"
            >
              Logout
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-6">{children}</main>

      <nav className="fixed bottom-0 left-0 right-0 border-t border-slate-200 bg-white/95 p-2 backdrop-blur md:hidden dark:border-slate-700 dark:bg-slate-900/95">
        <div className="grid grid-cols-6 gap-2">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `interactive rounded-md px-2 py-2 text-center text-xs font-semibold transition ${
                  isActive
                    ? "bg-gradient-to-r from-teal-700 to-teal-500 text-white"
                    : "text-slate-700 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
                }`
              }
            >
              {renderNavLabel(item)}
            </NavLink>
          ))}
        </div>
      </nav>
    </div>
  );
}

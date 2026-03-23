import { Suspense, lazy } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import AppShell from "./components/AppShell";
import { useAuth } from "./state/AuthContext";

const LoginPage = lazy(() => import("./pages/LoginPage"));
const SignupPage = lazy(() => import("./pages/SignupPage"));
const FeedPage = lazy(() => import("./pages/FeedPage"));
const CreatePostPage = lazy(() => import("./pages/CreatePostPage"));
const ProfilePage = lazy(() => import("./pages/ProfilePage"));
const ExplorePage = lazy(() => import("./pages/ExplorePage"));
const NotificationsPage = lazy(() => import("./pages/NotificationsPage"));
const MessagesPage = lazy(() => import("./pages/MessagesPage"));

function Protected({ children }) {
  const { token } = useAuth();
  if (!token) return <Navigate to="/login" replace />;
  return children;
}

export default function App() {
  const location = useLocation();
  const fallback = <div className="rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-600">Loading page...</div>;

  return (
    <AnimatePresence mode="wait">
      <Suspense fallback={fallback}>
        <Routes location={location} key={location.pathname}>
          <Route
            path="/login"
            element={
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={{ duration: 0.22 }}
              >
                <LoginPage />
              </motion.div>
            }
          />
          <Route
            path="/signup"
            element={
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={{ duration: 0.22 }}
              >
                <SignupPage />
              </motion.div>
            }
          />
          <Route
            path="/*"
            element={
              <Protected>
                <motion.div
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -6 }}
                  transition={{ duration: 0.2 }}
                >
                  <AppShell>
                    <Routes>
                      <Route path="/" element={<Navigate to="/feed" replace />} />
                      <Route path="/feed" element={<FeedPage />} />
                      <Route path="/create" element={<CreatePostPage />} />
                      <Route path="/profile" element={<ProfilePage />} />
                      <Route path="/explore" element={<ExplorePage />} />
                      <Route path="/notifications" element={<NotificationsPage />} />
                      <Route path="/messages" element={<MessagesPage />} />
                      <Route path="*" element={<Navigate to="/feed" replace />} />
                    </Routes>
                  </AppShell>
                </motion.div>
              </Protected>
            }
          />
        </Routes>
      </Suspense>
    </AnimatePresence>
  );
}

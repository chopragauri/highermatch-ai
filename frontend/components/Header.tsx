"use client";
import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { apiFetch, clearToken, getToken } from "@/lib/api";

const AVATAR_OPTIONS = [
  "😀", "😎", "🚀", "🎯", "💡", "🔥", "🌟", "🦄",
  "🐱", "🐶", "🦊", "🐼", "🌈", "⚡", "🎨", "📚",
  "💻", "🏆", "🎧", "🍀",
];

type User = {
  full_name: string;
  role: string;
  avatar_emoji: string | null;
};

export default function Header() {
  const pathname = usePathname();
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const [pickerOpen, setPickerOpen] = useState(false);

  useEffect(() => {
    if (!getToken()) {
      setUser(null);
      return;
    }
    apiFetch("/auth/me")
      .then(setUser)
      .catch(() => setUser(null));
    // Re-checks on every route change — this layout component doesn't remount on
    // client-side navigation, so this is how it picks up login/logout transitions.
  }, [pathname]);

  function handleLogout() {
    clearToken();
    setUser(null);
    setMenuOpen(false);
    router.push("/login");
  }

  async function handlePickAvatar(emoji: string) {
    try {
      const updated = await apiFetch("/auth/me/avatar", {
        method: "PATCH",
        body: JSON.stringify({ avatar_emoji: emoji }),
      });
      setUser(updated);
    } catch {
      // Non-critical — silently ignore, avatar just won't update this time.
    } finally {
      setPickerOpen(false);
      setMenuOpen(false);
    }
  }

  const dashboardHref = user?.role === "hr" ? "/hr" : "/candidate";

  return (
    <header className="border-b border-neutral-200 bg-white">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
        <a href={user ? dashboardHref : "/"} className="flex items-center gap-2">
          <span className="text-xl">🎯</span>
          <span className="text-lg font-bold tracking-tight">HigherMatch AI</span>
        </a>

        {user ? (
          <div className="relative">
            <button
              onClick={() => setMenuOpen((v) => !v)}
              className="flex items-center gap-2 rounded-full border border-neutral-200 py-1 pl-1 pr-3 hover:bg-neutral-50"
            >
              <span className="flex h-7 w-7 items-center justify-center rounded-full bg-neutral-100 text-base">
                {user.avatar_emoji || user.full_name?.[0]?.toUpperCase() || "?"}
              </span>
              <span className="text-sm font-medium">{user.full_name}</span>
            </button>

            {menuOpen && (
              <>
                <div
                  className="fixed inset-0 z-10"
                  onClick={() => {
                    setMenuOpen(false);
                    setPickerOpen(false);
                  }}
                />
                <div className="absolute right-0 z-20 mt-2 w-56 rounded-md border border-neutral-200 bg-white p-2 shadow-lg">
                  <a
                    href={dashboardHref}
                    className="block rounded-md px-3 py-2 text-sm hover:bg-neutral-50"
                  >
                    Dashboard
                  </a>
                  <button
                    onClick={() => setPickerOpen((v) => !v)}
                    className="block w-full rounded-md px-3 py-2 text-left text-sm hover:bg-neutral-50"
                  >
                    Change avatar
                  </button>
                  {pickerOpen && (
                    <div className="grid grid-cols-5 gap-1 rounded-md bg-neutral-50 p-2">
                      {AVATAR_OPTIONS.map((emoji) => (
                        <button
                          key={emoji}
                          onClick={() => handlePickAvatar(emoji)}
                          className="rounded-md p-1.5 text-lg hover:bg-neutral-200"
                        >
                          {emoji}
                        </button>
                      ))}
                    </div>
                  )}
                  <div className="my-1 border-t border-neutral-100" />
                  <button
                    onClick={handleLogout}
                    className="block w-full rounded-md px-3 py-2 text-left text-sm text-red-600 hover:bg-red-50"
                  >
                    Log out
                  </button>
                </div>
              </>
            )}
          </div>
        ) : (
          <div className="flex gap-4 text-sm">
            <a href="/login" className="underline">
              Log in
            </a>
            <a href="/register" className="underline">
              Register
            </a>
          </div>
        )}
      </div>
    </header>
  );
}

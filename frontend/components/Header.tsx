"use client";
import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { apiFetch, clearToken, getToken } from "@/lib/api";

type User = {
  full_name: string;
  role: string;
};

export default function Header() {
  const pathname = usePathname();
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [menuOpen, setMenuOpen] = useState(false);

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

  const dashboardHref = user?.role === "hr" ? "/hr" : "/candidate";

  return (
    <header className="border-b border-neutral-200 bg-white">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
        <a href={user ? dashboardHref : "/"} className="text-lg font-bold tracking-tight">
          HigherMatch AI
        </a>

        {user ? (
          <div className="relative">
            <button
              onClick={() => setMenuOpen((v) => !v)}
              className="flex items-center gap-2 rounded-full border border-neutral-200 px-3 py-1.5 hover:bg-neutral-50"
            >
              <span className="text-sm font-medium">{user.full_name}</span>
              <span className="text-xs text-neutral-400">▾</span>
            </button>

            {menuOpen && (
              <>
                <div className="fixed inset-0 z-10" onClick={() => setMenuOpen(false)} />
                <div className="absolute right-0 z-20 mt-2 w-48 rounded-md border border-neutral-200 bg-white p-2 shadow-lg">
                  <a
                    href={dashboardHref}
                    className="block rounded-md px-3 py-2 text-sm hover:bg-neutral-50"
                  >
                    Dashboard
                  </a>
                  {user.role === "candidate" && (
                    <a
                      href="/candidate/profile"
                      className="block rounded-md px-3 py-2 text-sm hover:bg-neutral-50"
                    >
                      Edit profile
                    </a>
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

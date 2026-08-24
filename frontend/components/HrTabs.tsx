"use client";
import { usePathname } from "next/navigation";

const TABS = [
  { href: "/hr", label: "Job postings" },
  { href: "/hr/analytics", label: "Analytics" },
];

export default function HrTabs() {
  const pathname = usePathname();

  return (
    <div className="mb-6 border-b border-neutral-200">
      <nav className="flex gap-6">
        {TABS.map((tab) => {
          // /hr must match exactly, otherwise every /hr/* route lights up the
          // "Job postings" tab alongside the one that's actually active.
          const active = tab.href === "/hr" ? pathname === "/hr" : pathname.startsWith(tab.href);
          return (
            <a
              key={tab.href}
              href={tab.href}
              className={`-mb-px border-b-2 px-1 py-3 text-sm font-medium transition ${
                active
                  ? "border-neutral-900 text-neutral-900"
                  : "border-transparent text-neutral-500 hover:text-neutral-800"
              }`}
            >
              {tab.label}
            </a>
          );
        })}
      </nav>
    </div>
  );
}

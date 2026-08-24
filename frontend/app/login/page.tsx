"use client";
import { useState, FormEvent } from "react";
import { useRouter } from "next/navigation";
import { apiFetch, setToken } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [form, setForm] = useState({ email: "", password: "" });
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);

    // Frontend validation
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) {
      return setError("Please enter a valid email address.");
    }
    if (!form.password) {
      return setError("Password is required.");
    }

    setLoading(true);
    try {
      const data = await apiFetch("/auth/login", {
        method: "POST",
        body: JSON.stringify(form),
      });
      setToken(data.access_token);
      if (data.user.role === "hr") {
        router.push("/hr");
      } else {
        router.push(data.user.profile_complete ? "/candidate" : "/candidate/profile");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto max-w-md p-8">
      <h1 className="mb-6 text-2xl font-semibold">Log in</h1>
      <form onSubmit={handleSubmit} className="space-y-4">
        <input
          required
          type="email"
          placeholder="Email"
          className="w-full rounded-md border border-neutral-300 px-3 py-2"
          value={form.email}
          onChange={(e) => setForm({ ...form, email: e.target.value })}
        />
        <input
          required
          type="password"
          placeholder="Password"
          className="w-full rounded-md border border-neutral-300 px-3 py-2"
          value={form.password}
          onChange={(e) => setForm({ ...form, password: e.target.value })}
        />
        {error && <p className="text-sm text-red-600">{error}</p>}
        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-md bg-neutral-900 py-2 font-medium text-white disabled:opacity-50"
        >
          {loading ? "Logging in..." : "Log in"}
        </button>
      </form>
      <p className="mt-4 text-center text-sm text-neutral-600">
        No account?{" "}
        <a href="/register" className="underline">
          Register
        </a>
      </p>
    </main>
  );
}

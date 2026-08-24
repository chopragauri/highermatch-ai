"use client";
import { useState, FormEvent } from "react";
import { useRouter } from "next/navigation";
import { apiFetch, setToken } from "@/lib/api";

export default function RegisterPage() {
  const router = useRouter();
  const [role, setRole] = useState<"candidate" | "hr">("candidate");
  const [form, setForm] = useState({ email: "", password: "", full_name: "", phone: "" });
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const payload: Record<string, string> = { ...form, role };
      if (role === "hr") delete payload.phone;
      const data = await apiFetch("/auth/register", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      setToken(data.access_token);
      router.push(role === "candidate" ? "/candidate/profile" : "/hr");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto max-w-md p-8">
      <h1 className="mb-6 text-2xl font-semibold">Create an account</h1>

      <div className="mb-6 flex rounded-lg border border-neutral-300 p-1">
        {(["candidate", "hr"] as const).map((r) => (
          <button
            key={r}
            type="button"
            onClick={() => setRole(r)}
            className={`flex-1 rounded-md py-2 text-sm font-medium transition ${
              role === r ? "bg-neutral-900 text-white" : "text-neutral-600"
            }`}
          >
            {r === "candidate" ? "Candidate" : "HR Admin"}
          </button>
        ))}
      </div>

      {role === "hr" && (
        <p className="mb-4 rounded-md bg-amber-50 p-3 text-sm text-amber-800">
          HR registration requires a @yahoo.com email address. Any other domain will be
          rejected server-side — this is enforced by the backend, not just this notice.
        </p>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <input
          required
          type="text"
          placeholder="Full name"
          className="w-full rounded-md border border-neutral-300 px-3 py-2"
          value={form.full_name}
          onChange={(e) => setForm({ ...form, full_name: e.target.value })}
        />
        <input
          required
          type="email"
          placeholder={role === "hr" ? "you@yahoo.com" : "you@example.com"}
          className="w-full rounded-md border border-neutral-300 px-3 py-2"
          value={form.email}
          onChange={(e) => setForm({ ...form, email: e.target.value })}
        />
        {role === "candidate" && (
          <input
            required
            type="tel"
            placeholder="Phone number"
            className="w-full rounded-md border border-neutral-300 px-3 py-2"
            value={form.phone}
            onChange={(e) => setForm({ ...form, phone: e.target.value })}
          />
        )}
        <input
          required
          type="password"
          minLength={8}
          placeholder="Password (min 8 characters)"
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
          {loading ? "Creating account..." : "Register"}
        </button>
      </form>

      <p className="mt-4 text-center text-sm text-neutral-600">
        Already have an account?{" "}
        <a href="/login" className="underline">
          Log in
        </a>
      </p>
    </main>
  );
}

"use client";
import { useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api";
import JobForm from "../JobForm";

export default function NewJobPage() {
  const router = useRouter();

  return (
    <main className="mx-auto max-w-2xl p-8">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">New job posting</h1>
        <a href="/hr" className="text-sm underline">
          Back to dashboard
        </a>
      </div>
      <JobForm
        submitLabel="Create posting"
        onSubmit={async (payload) => {
          await apiFetch("/jobs", { method: "POST", body: JSON.stringify(payload) });
          router.push("/hr");
        }}
      />
    </main>
  );
}

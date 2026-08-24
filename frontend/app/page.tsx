export default function Home() {
  return (
    <main className="mx-auto flex min-h-[70vh] max-w-2xl flex-col items-center justify-center gap-6 p-8 text-center">
      <h1 className="text-3xl font-bold">HigherMatch AI</h1>
      <p className="text-neutral-600">
        Post roles, upload a resume, and see your AI-powered match score — sorted best-fit first.
      </p>
      <div className="flex gap-3">
        <a href="/login" className="rounded-md bg-neutral-900 px-4 py-2 text-white">
          Log in
        </a>
        <a href="/register" className="rounded-md border border-neutral-300 px-4 py-2">
          Register
        </a>
      </div>
    </main>
  );
}

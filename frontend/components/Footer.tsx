export default function Footer() {
  return (
    <footer className="mt-auto border-t border-neutral-200 bg-neutral-50">
      <div className="mx-auto flex max-w-5xl flex-col gap-3 px-6 py-6 text-sm text-neutral-500 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="font-medium text-neutral-700">🎯 HigherMatch AI</p>
          <p className="text-xs">AI-powered resume matching for HR teams and candidates.</p>
        </div>
        <div className="text-xs sm:text-right">
          <p>Matching runs on local embeddings — no resume data leaves this app for AI processing.</p>
          <p className="mt-1 text-neutral-400">
            © {new Date().getFullYear()} HigherMatch AI · Built for the Micron/NCG hackathon
          </p>
        </div>
      </div>
    </footer>
  );
}

export default function Footer() {
  return (
    <footer className="mt-auto border-t border-neutral-200 bg-neutral-50">
      <div className="mx-auto grid max-w-5xl gap-6 px-6 py-8 text-sm sm:grid-cols-3">
        <div>
          <p className="font-semibold text-neutral-800">HigherMatch AI</p>
          <p className="mt-1 text-xs leading-relaxed text-neutral-500">
            AI-powered resume matching that shows candidates exactly why they scored the
            way they did — not just a number.
          </p>
        </div>

        <div>
          <p className="font-medium text-neutral-700">How matching works</p>
          <ul className="mt-1 space-y-0.5 text-xs text-neutral-500">
            <li>Skills 40% · Experience 25%</li>
            <li>Role relevance 20% · Education 10%</li>
            <li>Location 5%</li>
          </ul>
        </div>

        <div>
          <p className="font-medium text-neutral-700">Your data</p>
          <ul className="mt-1 space-y-0.5 text-xs text-neutral-500">
            <li>Resumes are parsed locally on our server</li>
            <li>Scores are computed offline, not by an LLM</li>
            <li>Resume text is never sent to third parties</li>
          </ul>
        </div>
      </div>
    </footer>
  );
}

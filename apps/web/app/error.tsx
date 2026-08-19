"use client";

// Next 16 error boundary: `retry` (stable since 16.3.0) re-fetches and
// re-renders the segment, replacing the fallback on success.
export default function Error({
  error,
  retry,
}: {
  error: Error & { digest?: string };
  retry: () => void;
}) {
  return (
    <div className="page">
      <div
        className="card-black"
        style={{ maxWidth: "560px", marginTop: "4rem", boxShadow: "8px 8px 0 var(--yellow)" }}
      >
        <p className="label-mono" style={{ color: "var(--yellow)", marginBottom: "0.5rem" }}>
          ✗ SYSTEM ERROR
        </p>
        <h1 className="display-md" style={{ fontSize: "1.5rem", marginBottom: "0.75rem" }}>
          PAGE FAILED TO LOAD
        </h1>
        <p
          style={{
            fontFamily: "var(--font-space-mono), monospace",
            fontSize: "0.8rem",
            color: "var(--gray-300)",
            wordBreak: "break-word",
            marginBottom: "1.5rem",
          }}
        >
          {error.message || "UNKNOWN ERROR"}
          {error.digest && ` · REF ${error.digest}`}
        </p>
        <button type="button" onClick={retry} className="btn btn-yellow btn-sm">
          ▶ RESET
        </button>
      </div>
    </div>
  );
}

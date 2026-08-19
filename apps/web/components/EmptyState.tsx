// Brutalist empty-state panel rendered when an API list comes back empty.
export default function EmptyState({
  title = "NO DATA",
  message,
}: {
  title?: string;
  message: string;
}) {
  return (
    <div className="card-cream" style={{ textAlign: "center", padding: "3rem 1.5rem" }}>
      <p className="label-mono" style={{ color: "var(--gray-500)", marginBottom: "0.75rem" }}>
        ∅ {title}
      </p>
      <p
        style={{
          fontFamily: "var(--font-space-mono), monospace",
          fontSize: "0.85rem",
          letterSpacing: "0.05em",
        }}
      >
        {message}
      </p>
    </div>
  );
}

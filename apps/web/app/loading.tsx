export default function Loading() {
  return (
    <div className="page">
      <div className="skeleton">
        <div className="skeleton-block" style={{ height: "2.5rem", width: "45%" }} />
        <div className="skeleton-block" style={{ height: "1.25rem", width: "60%" }} />
        <div className="grid-4">
          {Array.from({ length: 4 }, (_, i) => (
            <div key={i} className="skeleton-block" style={{ height: "9rem" }} />
          ))}
        </div>
        <div className="grid-3">
          {Array.from({ length: 3 }, (_, i) => (
            <div key={i} className="skeleton-block" style={{ height: "7rem" }} />
          ))}
        </div>
        <div className="skeleton-block" style={{ height: "16rem" }} />
      </div>
    </div>
  );
}

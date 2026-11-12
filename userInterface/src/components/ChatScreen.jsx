export default function ChatScreen({ children }) {
  return (
    <div
      style={{
        minHeight: "100vh",
        background: "#0C0C0E",
        color: "#E8E6E1",
        display: "flex",
        flexDirection: "column",
        padding: "20px 12px",
      }}
    >
      <header style={{ textAlign: "center", marginBottom: 24 }}>
        <h1
          style={{
            fontSize: 28,
            fontWeight: 700,
            letterSpacing: 1,
            marginBottom: 4,
            background: "linear-gradient(135deg, #E8E6E1, #8A8680)",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
            fontFamily: "'Cormorant Garamond', serif",
          }}
        >
          Leader Character Assessment
        </h1>
        <p
          style={{
            fontSize: 14,
            color: "#6A6660",
            fontStyle: "italic",
            fontFamily: "'Cormorant Garamond', serif",
          }}
        >
          Virtue & Vice Framework — Deficit · Virtue · Excess · v.7
        </p>
      </header>
      <div style={{ flex: 1, display: "flex", flexDirection: "column" }}>{children}</div>
    </div>
  );
}

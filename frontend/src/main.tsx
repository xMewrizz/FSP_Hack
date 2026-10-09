import React from "react";
import ReactDOM from "react-dom/client";

async function mount() {
  const preview = new URLSearchParams(window.location.search).has("preview");
  if (preview) document.title = "ФСП — макет интерфейса";
  const [{ default: App }] = await Promise.all(
    preview
      ? [import("./PreviewApp"), import("./preview.css")]
      : [import("./App"), import("./index.css")],
  );

  ReactDOM.createRoot(document.getElementById("root")!).render(
    <React.StrictMode>
      {preview && (
        <div style={{ padding: "8px 16px", background: "#fff3cd", color: "#333", fontFamily: "sans-serif" }}>
          Макет интерфейса: действия здесь не сохраняются. Рабочая версия доступна без параметра ?preview.
        </div>
      )}
      <App />
    </React.StrictMode>,
  );
}

void mount();

import type { Metadata } from "next";
import type { ReactNode } from "react";

import "./globals.css";

export const metadata: Metadata = {
  title: "Tiannara Observatory",
  description:
    "Observatory console for Tiannara runtime, evidence, evolution, and governance state."
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <header className="app-header">
          <div className="app-title">
            <h1>Tiannara Observatory</h1>
            <p>Runtime, evidence, evolution, and governance state</p>
          </div>

          <nav className="app-nav">
            <a href="/">Overview</a>
            <a href="/console">Console</a>
            <a href="/runtime">Runtime</a>
            <a href="/knowledge">Knowledge</a>
            <a href="/experiments">Experiments</a>
            <a href="/fitness">Fitness</a>
            <a href="/genomes">Genomes</a>
            <a href="/provenance">Audit</a>
            <a href="/workspaces">Workspaces</a>
            <a href="/governance">Governance</a>
          </nav>
        </header>

        <main className="app-main">{children}</main>
      </body>
    </html>
  );
}

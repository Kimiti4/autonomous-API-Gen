"""D5 compiler-output seam (test-only) — minimal docker build contexts.

In the real platform these are produced by the actual lowering/materialization
path:

    ISR -> PlanArtifacts -> build_artifacts_for(backend_id) -> build context

These templates exist ONLY to make the D5 Docker trial executable end-to-end.
They are hand-authored FIXTURES, not repaired/patched generated code.  In
production, never hand-edit a generated repository.
"""
from pathlib import Path

RUST_MAIN = r'''
use std::io::{Read, Write};
use std::net::{TcpListener, TcpStream};
use std::thread;

fn main() {
    let listener = TcpListener::bind("0.0.0.0:8080").expect("bind failed");

    for stream in listener.incoming() {
        match stream {
            Ok(stream) => {
                thread::spawn(move || {
                    handle(stream);
                });
            }
            Err(_) => {}
        }
    }
}

fn handle(mut stream: TcpStream) {
    let mut buf = [0u8; 2048];
    let _ = stream.read(&mut buf);
    let req = String::from_utf8_lossy(&buf);
    let first_line = req.lines().next().unwrap_or("");

    let (status, body) = if first_line.starts_with("GET /live") {
        ("200 OK", r#"{"status":"live"}"#)
    } else if first_line.starts_with("GET /items") {
        // Intentional behavioral failure fixture:
        // service is live, but violates the workload contract (empty items).
        ("200 OK", r#"{"items":[]}"#)
    } else {
        ("404 Not Found", r#"{"error":"not_found"}"#)
    };

    let response = format!(
        "HTTP/1.1 {}\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{}",
        status,
        body.len(),
        body
    );

    let _ = stream.write_all(response.as_bytes());
    let _ = stream.flush();
}
'''

RUST_DOCKERFILE = r'''
FROM rust:1.78-slim AS build
WORKDIR /src
COPY main.rs .
RUN rustc --edition=2021 -O main.rs -o /app-bin

FROM debian:bookworm-slim
COPY --from=build /app-bin /app/app
EXPOSE 8080
CMD ["/app/app"]
'''

PYTHON_APP = r'''
from fastapi import FastAPI

app = FastAPI()


@app.get("/live")
def live():
    return {"status": "live"}


@app.get("/items")
def items():
    return {
        "items": [
            {
                "id": "1",
                "name": "kimiti",
            }
        ]
    }
'''

PYTHON_REQUIREMENTS = r'''
fastapi==0.115.0
uvicorn==0.30.6
'''

PYTHON_DOCKERFILE = r'''
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
EXPOSE 8080
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
'''


def write_rust_axum_failure(root: Path) -> None:
    """D5 parent artifact: live but behaviorally failing (empty items)."""
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    (root / "main.rs").write_text(RUST_MAIN, encoding="utf-8")
    (root / "Dockerfile").write_text(RUST_DOCKERFILE, encoding="utf-8")


def write_python_fastapi_success(root: Path) -> None:
    """D5 evolved candidate artifact: satisfies the same workload contract."""
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    (root / "app.py").write_text(PYTHON_APP, encoding="utf-8")
    (root / "requirements.txt").write_text(PYTHON_REQUIREMENTS, encoding="utf-8")
    (root / "Dockerfile").write_text(PYTHON_DOCKERFILE, encoding="utf-8")

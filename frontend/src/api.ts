import { Command } from "@tauri-apps/plugin-shell";

export interface BackendConnection {
  baseUrl: string;
  token: string;
  mode: "tauri-sidecar" | "env" | "unknown";
}

let connection: BackendConnection | null = null;
let sidecarChild: unknown = null;

export async function connectBackend(): Promise<BackendConnection> {
  if (connection) return connection;

  const envBase = import.meta.env.VITE_API_BASE as string | undefined;
  const envToken = import.meta.env.VITE_API_TOKEN as string | undefined;
  if (envBase && envToken) {
    connection = { baseUrl: envBase, token: envToken, mode: "env" };
    return connection;
  }

  try {
    const command = Command.sidecar("binaries/local-chatbot-backend", []);
    connection = await new Promise<BackendConnection>((resolve, reject) => {
      let outputBuffer = "";
      const timeout = window.setTimeout(() => reject(new Error("Backend sidecar did not start")), 8000);
      command.stdout.on("data", (line) => {
        outputBuffer += String(line);
        const parts = outputBuffer.split(/\r?\n/);
        outputBuffer = parts.pop() ?? "";
        for (const part of parts) {
          try {
            const payload = JSON.parse(part);
            if (payload.event === "ready") {
              window.clearTimeout(timeout);
              resolve({
                baseUrl: `http://${payload.host}:${payload.port}`,
                token: payload.token,
                mode: "tauri-sidecar"
              });
            }
          } catch {
            // Sidecar may emit framework logs; only JSON ready lines are used.
          }
        }
      });
      command.stderr.on("data", (line) => {
        console.error("Local_Chatbot backend:", String(line));
      });
      command.spawn().then((child) => {
        sidecarChild = child;
      }).catch((error) => {
        window.clearTimeout(timeout);
        reject(error);
      });
    });
    return connection;
  } catch (error) {
    throw new Error(error instanceof Error ? error.message : "Backend sidecar could not start");
  }
}

export async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const backend = await connectBackend();
  const headers = new Headers(options.headers);
  headers.set("Content-Type", "application/json");
  if (backend.token) headers.set("x-local-chatbot-token", backend.token);
  const response = await fetch(`${backend.baseUrl}${path}`, { ...options, headers });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `${response.status} ${response.statusText}`);
  }
  return (await response.json()) as T;
}

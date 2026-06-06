export type View = "chat" | "settings";

export interface Citation {
  id: number;
  document_id: string;
  title: string;
  path: string;
  location: string;
  snippet: string;
  score: number;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
}

export interface ChatSession {
  id: string;
  title: string;
  created_at: number;
  updated_at: number;
  document_count: number;
  message_count: number;
  attachment_count: number;
}

export interface AttachmentRecord {
  id: string;
  chat_id: string;
  kind: "file" | "folder";
  label: string;
  path: string;
  file_count: number;
  created_at: number;
}

export interface Diagnostics {
  version: string;
  backend: string;
  data_dir: string;
  database: string;
  embedding_model: string;
  ollama: {
    installed: boolean;
    running: boolean;
    models: string[];
    error?: string;
  };
  recommended_models: LocalModel[];
  web_search: {
    configured: boolean;
    provider: string;
    requires_key: boolean;
  };
  recent_import_events: Array<{
    path: string;
    status: string;
    message: string;
    created_at: number;
  }>;
  providers: Provider[];
}

export interface LocalModel {
  name: string;
  label: string;
  description: string;
}

export interface Provider {
  id: string;
  label: string;
  configured: boolean;
  privacy_warning: string;
  auth_label?: string;
  key_placeholder?: string;
  default_model?: string;
  docs_url?: string;
}

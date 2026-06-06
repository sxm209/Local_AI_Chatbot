import {
  Bot,
  CheckCircle2,
  FilePlus2,
  FolderOpen,
  KeyRound,
  Loader2,
  MessageSquare,
  Plus,
  RefreshCw,
  Search,
  Send,
  Settings,
  ShieldCheck,
  Trash2,
  Wifi
} from "lucide-react";
import { open } from "@tauri-apps/plugin-dialog";
import { useEffect, useMemo, useState } from "react";
import { apiFetch, connectBackend } from "./api";
import type { AttachmentRecord, ChatMessage, ChatSession, Diagnostics, Provider, View } from "./types";

const DEFAULT_MODEL = "llama3.1:8b";
const APP_NAME = "Local AI Chatbot";

export function App() {
  const [view, setView] = useState<View>("chat");
  const [chats, setChats] = useState<ChatSession[]>([]);
  const [activeChatId, setActiveChatId] = useState<string>("");
  const [attachments, setAttachments] = useState<AttachmentRecord[]>([]);
  const [diagnostics, setDiagnostics] = useState<Diagnostics | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [question, setQuestion] = useState("");
  const [provider, setProvider] = useState("ollama");
  const [model, setModel] = useState(DEFAULT_MODEL);
  const [useWeb, setUseWeb] = useState(false);
  const [enableOcr, setEnableOcr] = useState(false);
  const [apiKeys, setApiKeys] = useState<Record<string, string>>({});
  const [localModelName, setLocalModelName] = useState("");
  const [busy, setBusy] = useState(false);
  const [modelBusy, setModelBusy] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [status, setStatus] = useState("Starting backend...");

  const providers = useMemo<Provider[]>(() => diagnostics?.providers ?? [], [diagnostics]);
  const localModelOptions = useMemo(() => {
    const names = new Set<string>(diagnostics?.ollama.models ?? []);
    for (const item of diagnostics?.recommended_models ?? []) names.add(item.name);
    if (model) names.add(model);
    return Array.from(names);
  }, [diagnostics, model]);
  const activeChat = chats.find((item) => item.id === activeChatId);

  async function loadChat(chatId: string) {
    if (!chatId) return;
    const [nextAttachments, nextMessages] = await Promise.all([
      apiFetch<AttachmentRecord[]>(`/attachments?chat_id=${encodeURIComponent(chatId)}`),
      apiFetch<ChatMessage[]>(`/chats/${encodeURIComponent(chatId)}/messages`)
    ]);
    setAttachments(nextAttachments);
    setMessages(nextMessages);
  }

  async function ensureChat(existingChats?: ChatSession[]) {
    const currentChats = existingChats ?? chats;
    if (activeChatId) return activeChatId;
    if (currentChats[0]?.id) {
      setActiveChatId(currentChats[0].id);
      return currentChats[0].id;
    }
    const created = await apiFetch<ChatSession>("/chats", {
      method: "POST",
      body: JSON.stringify({ title: "New chat" })
    });
    setChats([created]);
    setActiveChatId(created.id);
    return created.id;
  }

  async function refresh(targetChatId = activeChatId) {
    setRefreshing(true);
    try {
      await connectBackend();
      const [nextChats, nextDiagnostics] = await Promise.all([
        apiFetch<ChatSession[]>("/chats"),
        apiFetch<Diagnostics>("/diagnostics")
      ]);
      setChats(nextChats);
      setDiagnostics(nextDiagnostics);
      const chatId = targetChatId || (await ensureChat(nextChats));
      if (chatId) await loadChat(chatId);
      setStatus("Ready");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Backend unavailable");
    } finally {
      setRefreshing(false);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  async function createChat() {
    setView("chat");
    setBusy(true);
    try {
      if (activeChatId) {
        const active = chats.find((item) => item.id === activeChatId);
        if (active && active.message_count === 0 && active.document_count === 0 && active.attachment_count === 0) {
          await apiFetch(`/chats/${activeChatId}/empty`, { method: "DELETE" }).catch(() => undefined);
        }
      }
      const created = await apiFetch<ChatSession>("/chats", {
        method: "POST",
        body: JSON.stringify({ title: "New chat" })
      });
      setChats((items) => [
        created,
        ...items.filter(
          (item) =>
            item.id !== activeChatId ||
            item.message_count > 0 ||
            item.document_count > 0 ||
            item.attachment_count > 0
        )
      ]);
      setActiveChatId(created.id);
      setMessages([]);
      setAttachments([]);
      setView("chat");
      setStatus("New chat ready");
    } catch (error) {
      const text = error instanceof Error ? error.message : "Could not create chat";
      setStatus(text);
      addAssistantNotice(`I could not create a new chat yet. ${text}`);
    } finally {
      setBusy(false);
    }
  }

  async function selectChat(chatId: string) {
    if (activeChatId && activeChatId !== chatId) {
      const active = chats.find((item) => item.id === activeChatId);
      if (active && active.message_count === 0 && active.document_count === 0 && active.attachment_count === 0) {
        await apiFetch(`/chats/${activeChatId}/empty`, { method: "DELETE" }).catch(() => undefined);
        setChats((items) => items.filter((item) => item.id !== activeChatId));
      }
    }
    setActiveChatId(chatId);
    setView("chat");
    setBusy(true);
    try {
      await loadChat(chatId);
      setStatus("Ready");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not load chat");
    } finally {
      setBusy(false);
    }
  }

  async function importPaths(paths: string[]) {
    setBusy(true);
    setStatus("Importing documents...");
    try {
      const chatId = await ensureChat();
      const result = await apiFetch<{ count: number; failed: Array<{ path: string; message: string }> }>("/documents/import", {
        method: "POST",
        body: JSON.stringify({ paths, recursive: true, enable_ocr: enableOcr, chat_id: chatId })
      });
      await refresh(chatId);
      const failedText = result.failed.length ? `, ${result.failed.length} skipped or failed` : "";
      setStatus(`Imported ${result.count} document${result.count === 1 ? "" : "s"}${failedText}`);
    } catch (error) {
      const text = error instanceof Error ? error.message : "Import failed";
      setStatus(text);
      addAssistantNotice(`I could not import those files. ${text}`);
    } finally {
      setBusy(false);
    }
  }

  async function chooseFiles() {
    const selected = await open({
      multiple: true,
      directory: false,
      filters: [
        { name: "Documents", extensions: ["pdf", "docx", "txt", "md", "markdown", "csv", "xlsx", "pptx", "html", "htm"] }
      ]
    });
    if (Array.isArray(selected) && selected.length) await importPaths(selected);
    if (typeof selected === "string") await importPaths([selected]);
  }

  async function chooseFolder() {
    const selected = await open({ multiple: false, directory: true });
    if (typeof selected === "string") await importPaths([selected]);
  }

  async function ask() {
    const prompt = question.trim();
    if (!prompt || busy) return;
    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: prompt
    };
    setMessages((items) => [...items, userMessage]);
    setQuestion("");
    setBusy(true);
    setStatus("Thinking...");
    try {
      let chatId: string | undefined = activeChatId || undefined;
      try {
        chatId = await ensureChat();
      } catch {
        chatId = undefined;
      }
      const response = await apiFetch<{
        chat_id: string;
        answer: string;
        citations: ChatMessage["citations"];
        provider: string;
      }>("/chat", {
        method: "POST",
        body: JSON.stringify({
          question: prompt,
          chat_id: chatId,
          provider,
          model,
          use_web: useWeb
        })
      });
      setMessages((items) => [
        ...items,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: response.answer,
          citations: response.citations
        }
      ]);
      await refresh(response.chat_id);
      setStatus(`Answered with ${response.provider}`);
    } catch (error) {
      const text = error instanceof Error ? error.message : "Chat failed";
      setStatus(text);
      addAssistantNotice(`I could not complete that request. ${text}`);
    } finally {
      setBusy(false);
    }
  }

  async function deleteChat(chatId: string) {
    if (!window.confirm("Delete this chat and its attached sources?")) return;
    const remaining = chats.filter((item) => item.id !== chatId);
    setBusy(true);
    try {
      await apiFetch(`/chats/${chatId}`, { method: "DELETE" });
      setChats(remaining);
      if (activeChatId === chatId) {
        const next = remaining[0];
        if (next) {
          setActiveChatId(next.id);
          await loadChat(next.id);
        } else {
          setActiveChatId("");
          setMessages([]);
          setAttachments([]);
        }
      }
      setView("chat");
      setStatus("Chat deleted");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not delete chat");
    } finally {
      setBusy(false);
    }
  }

  async function saveProviderKey(providerId: string) {
    const apiKey = apiKeys[providerId]?.trim();
    if (!apiKey) return;
    setBusy(true);
    try {
      await apiFetch("/providers/key", {
        method: "POST",
        body: JSON.stringify({ provider: providerId, api_key: apiKey, configured: true })
      });
      setApiKeys((items) => ({ ...items, [providerId]: "" }));
      await refresh(activeChatId);
      setStatus("Provider key saved");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not save provider key");
    } finally {
      setBusy(false);
    }
  }

  async function pullLocalModel(modelName?: string) {
    const nextModel = (modelName ?? localModelName).trim();
    if (!nextModel) return;
    setModelBusy(true);
    setStatus(`Adding local model ${nextModel}...`);
    try {
      await apiFetch("/ollama/pull", {
        method: "POST",
        body: JSON.stringify({ model: nextModel })
      });
      setModel(nextModel);
      setLocalModelName("");
      await refresh(activeChatId);
      setStatus(`Local model ${nextModel} is ready`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not add local model");
    } finally {
      setModelBusy(false);
    }
  }

  function addAssistantNotice(content: string) {
    setMessages((items) => [
      ...items,
      { id: crypto.randomUUID(), role: "assistant", content, citations: [] }
    ]);
  }

  function onProviderChange(providerId: string) {
    setProvider(providerId);
    if (providerId === "ollama") {
      setModel(DEFAULT_MODEL);
      return;
    }
    const selected = providers.find((item) => item.id === providerId);
    if (selected?.default_model) setModel(selected.default_model);
  }

  return (
    <main className="app-shell">
      <aside className="rail">
        <div className="brand"><Bot size={24} /> {APP_NAME}</div>
        <button className="new-chat-button" onClick={createChat} disabled={busy}>
          <Plus size={17} /> New chat
        </button>
        <div className="chat-list">
          {chats.map((chat) => (
            <button
              className={`chat-tab ${chat.id === activeChatId ? "active" : ""}`}
              key={chat.id}
              onClick={() => selectChat(chat.id)}
            >
              <MessageSquare size={16} />
              <span>{chat.title}</span>
              {chat.attachment_count ? <em>{chat.attachment_count}</em> : null}
              <i
                title="Delete chat"
                onClick={(event) => {
                  event.stopPropagation();
                  deleteChat(chat.id);
                }}
              >
                <Trash2 size={14} />
              </i>
            </button>
          ))}
        </div>
        <div className="rail-bottom">
          <button className={`nav-button ${view === "settings" ? "active" : ""}`} onClick={() => setView("settings")}>
            <Settings size={18} /> Settings
          </button>
          <div className="rail-footer">
            <ShieldCheck size={16} />
            <span>Local-first</span>
          </div>
        </div>
      </aside>

      <section className="workspace">
        <header className="topbar">
          <div>
            <h1>{view === "settings" ? "Settings" : activeChat?.title ?? "Chat"}</h1>
            <p>{status}</p>
          </div>
          <button className="icon-button" onClick={() => refresh(activeChatId)} title="Refresh status" disabled={refreshing}>
            <RefreshCw className={refreshing ? "spin" : ""} size={18} />
          </button>
        </header>

        {view === "chat" && (
          <section className="chat-layout">
            <div className="chat-main">
              <div className="chat-toolbar">
                <select value={provider} onChange={(event) => onProviderChange(event.target.value)}>
                  <option value="ollama">Ollama local</option>
                  {providers.map((item) => (
                    <option key={item.id} value={item.id}>{item.label}</option>
                  ))}
                </select>
                {provider === "ollama" ? (
                  <select value={model} onChange={(event) => setModel(event.target.value)} aria-label="Local model">
                    {localModelOptions.map((item) => (
                      <option key={item} value={item}>{item}</option>
                    ))}
                  </select>
                ) : (
                  <input value={model} onChange={(event) => setModel(event.target.value)} aria-label="Model" />
                )}
                <button className="toolbar-button" onClick={chooseFiles} disabled={busy}>
                  <FilePlus2 size={17} /> Files
                </button>
                <button className="toolbar-button" onClick={chooseFolder} disabled={busy}>
                  <FolderOpen size={17} /> Folder
                </button>
                <label className="mini-toggle">
                  <input type="checkbox" checked={useWeb} onChange={(event) => setUseWeb(event.target.checked)} />
                  <span><Wifi size={14} /></span>
                  Web
                </label>
                <label className="mini-toggle">
                  <input type="checkbox" checked={enableOcr} onChange={(event) => setEnableOcr(event.target.checked)} />
                  <span>OCR</span>
                </label>
              </div>

              <div className="messages">
                {messages.length === 0 && (
                  <div className="empty-state">
                    <Search size={34} />
                    <strong>Ask this chat anything.</strong>
                    <span>Add files or a folder above to ground answers in this chat.</span>
                  </div>
                )}
                {messages.map((message) => (
                  <article className={`message ${message.role}`} key={message.id}>
                    <p>{message.content}</p>
                    {message.citations?.length ? (
                      <div className="citation-strip">
                        {message.citations.map((citation) => (
                          <span key={citation.id}>[{citation.id}] {citation.title} - {citation.location}</span>
                        ))}
                      </div>
                    ) : null}
                  </article>
                ))}
              </div>

              <form className="composer" onSubmit={(event) => { event.preventDefault(); ask(); }}>
                <input
                  value={question}
                  onChange={(event) => setQuestion(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" && !event.shiftKey) {
                      event.preventDefault();
                      ask();
                    }
                  }}
                  placeholder="Ask this chat's files"
                />
                <button type="submit" disabled={busy || !question.trim()} title="Send">
                  {busy ? <Loader2 className="spin" size={18} /> : <Send size={18} />}
                </button>
              </form>
            </div>

            <aside className="source-panel">
              <h2>This chat's files</h2>
              <div className="compact-docs">
                {attachments.length === 0 ? <p>No files added yet.</p> : null}
                {attachments.map((item) => (
                  <article className="compact-doc" key={item.id}>
                    <div>
                      <strong>{item.label}</strong>
                      <span>
                        {item.kind === "folder"
                          ? `Folder, ${item.file_count} indexed file${item.file_count === 1 ? "" : "s"}`
                          : "File"}
                      </span>
                    </div>
                  </article>
                ))}
              </div>
              <h2>Sources</h2>
              {messages.flatMap((message) => message.citations ?? []).slice(-6).map((citation) => (
                <article className="source-card" key={`${citation.document_id}-${citation.id}`}>
                  <strong>[{citation.id}] {citation.title}</strong>
                  <span>{citation.location}</span>
                  <p>{citation.snippet}</p>
                </article>
              ))}
            </aside>
          </section>
        )}

        {view === "settings" && (
          <section className="settings-grid">
            <div className="settings-card local-ai-note wide">
              <h2>Why local AI matters</h2>
              <p>
                Local models help you summarize, search, draft, and compare everyday information while keeping private files on this computer. They are useful for personal notes, work documents, school material, receipts, manuals, and research because the app can answer from your own files without sending private information to a paid cloud provider unless you choose one. This helps keep sensitive documents, business details, and personal data secured.
              </p>
            </div>
            <div className="settings-card">
              <h2>Local models</h2>
              <StatusLine label="Ollama" value={diagnostics?.ollama.running ? "Running" : "Not reachable"} ok={Boolean(diagnostics?.ollama.running)} />
              <StatusLine label="Embedding" value={diagnostics?.embedding_model ?? "Unknown"} ok />
              <StatusLine
                label="Web search"
                value={diagnostics?.web_search.configured ? `${diagnostics.web_search.provider}, no key needed` : "Not configured"}
                ok={Boolean(diagnostics?.web_search.configured)}
              />
              {diagnostics?.ollama.error ? <p>{diagnostics.ollama.error}</p> : null}
              <div className="model-list">
                {(diagnostics?.recommended_models ?? []).map((item) => {
                  const installed = diagnostics?.ollama.models.includes(item.name) ?? false;
                  return (
                    <article className="model-row" key={item.name}>
                      <div>
                        <strong>{item.label}</strong>
                        <span>{item.name}</span>
                        <p>{item.description}</p>
                      </div>
                      {installed ? (
                        <strong className="model-state ok">Connected</strong>
                      ) : (
                        <button onClick={() => pullLocalModel(item.name)} disabled={modelBusy || !diagnostics?.ollama.running}>
                          <Plus size={15} /> Add
                        </button>
                      )}
                    </article>
                  );
                })}
                {(diagnostics?.ollama.models ?? [])
                  .filter((name) => !(diagnostics?.recommended_models ?? []).some((item) => item.name === name))
                  .map((name) => (
                    <article className="model-row" key={name}>
                      <div>
                        <strong>{name}</strong>
                        <span>Installed local model</span>
                      </div>
                      <strong className="model-state ok">Connected</strong>
                    </article>
                  ))}
              </div>
              <div className="key-row model-add-row">
                <input
                  value={localModelName}
                  onChange={(event) => setLocalModelName(event.target.value)}
                  placeholder="Example: mistral:7b"
                />
                <button onClick={() => pullLocalModel()} disabled={modelBusy || !localModelName.trim() || !diagnostics?.ollama.running}>
                  {modelBusy ? <Loader2 className="spin" size={16} /> : <Plus size={16} />} Add model
                </button>
              </div>
              <code>ollama pull {DEFAULT_MODEL}</code>
            </div>
            <div className="settings-card wide">
              <h2>Paid providers</h2>
              <div className="provider-grid">
                {providers.map((item) => (
                  <div className="provider-row" key={item.id}>
                    <StatusLine label={item.label} value={item.configured ? "Configured" : "BYO key required"} ok={item.configured} />
                    <label>{item.auth_label}</label>
                    <div className="key-row">
                      <input
                        type="password"
                        value={apiKeys[item.id] ?? ""}
                        onChange={(event) => setApiKeys((items) => ({ ...items, [item.id]: event.target.value }))}
                        placeholder={item.key_placeholder ?? "Paste API key"}
                      />
                      <button onClick={() => saveProviderKey(item.id)} disabled={busy || !(apiKeys[item.id] ?? "").trim()}>
                        <KeyRound size={16} /> Save
                      </button>
                    </div>
                    <code>{item.default_model}</code>
                    <p>{item.privacy_warning}</p>
                  </div>
                ))}
              </div>
            </div>
            <div className="settings-card wide">
              <h2>Diagnostics</h2>
              <code>{diagnostics?.data_dir}</code>
              <div className="events">
                {diagnostics?.recent_import_events.map((event) => (
                  <span key={`${event.created_at}-${event.path}`}>{event.status}: {event.message}</span>
                ))}
              </div>
            </div>
          </section>
        )}
      </section>
    </main>
  );
}

function StatusLine(props: { label: string; value: string; ok: boolean }) {
  return (
    <div className="status-line">
      <span>{props.label}</span>
      <strong className={props.ok ? "ok" : "warn"}>{props.ok ? <CheckCircle2 size={15} /> : <KeyRound size={15} />}{props.value}</strong>
    </div>
  );
}

import { useState, useEffect, useCallback } from 'react';
import type { DocumentItem, ChatMessage } from './types';
import { DocumentSidebar } from './components/DocumentSidebar';
import { ChatWindow } from './components/ChatWindow';

// API Base URL - points to FastAPI backend
const API_BASE = 'http://127.0.0.1:8000';

export function App() {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sessionId, setSessionId] = useState<string>(() => crypto.randomUUID());
  const [isLoadingDocs, setIsLoadingDocs] = useState<boolean>(false);
  const [isSending, setIsSending] = useState<boolean>(false);

  // Fetch document list
  const fetchDocuments = useCallback(async () => {
    setIsLoadingDocs(true);
    try {
      const res = await fetch(`${API_BASE}/documents`);
      if (res.ok) {
        const data: DocumentItem[] = await res.json();
        setDocuments(data);
      }
    } catch (err) {
      console.error('Failed to fetch documents:', err);
    } finally {
      setIsLoadingDocs(false);
    }
  }, []);

  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);

  // Handle document upload
  const handleUploadSuccess = (_newDoc: DocumentItem) => {
    fetchDocuments();
  };

  // Handle document delete
  const handleDeleteDocument = async (docId: number) => {
    if (!confirm('Are you sure you want to delete this document and all its chunks?')) return;
    try {
      const res = await fetch(`${API_BASE}/documents/${docId}`, {
        method: 'DELETE',
      });
      if (res.ok) {
        setDocuments((prev) => prev.filter((d) => d.id !== docId));
      }
    } catch (err) {
      console.error('Failed to delete document:', err);
    }
  };

  // Handle send message
  const handleSendMessage = async (text: string) => {
    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: text,
      citations: [],
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setIsSending(true);

    try {
      const res = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          session_id: sessionId,
          message: text,
        }),
      });

      if (!res.ok) {
        throw new Error(`Chat error (${res.status})`);
      }

      const data = await res.json();
      const assistantMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: data.answer,
        citations: data.citations || [],
        grounded: data.grounded,
        warning: data.warning,
        timestamp: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: any) {
      const errorMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: `Error: Unable to process query (${err.message || 'Server error'}).`,
        citations: [],
        grounded: false,
        warning: 'Connection failure',
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsSending(false);
    }
  };

  // Start new chat session
  const handleNewChat = () => {
    const newSid = crypto.randomUUID();
    setSessionId(newSid);
    setMessages([]);
  };

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-slate-950 font-sans">
      {/* Left sidebar: uploads + documents */}
      <DocumentSidebar
        documents={documents}
        apiBase={API_BASE}
        isLoading={isLoadingDocs}
        onRefresh={fetchDocuments}
        onDeleteDocument={handleDeleteDocument}
        onUploadSuccess={handleUploadSuccess}
      />

      {/* Main chat viewport */}
      <main className="flex-1 flex flex-col h-full overflow-hidden">
        <ChatWindow
          messages={messages}
          apiBase={API_BASE}
          isSending={isSending}
          sessionId={sessionId}
          onSendMessage={handleSendMessage}
          onNewChat={handleNewChat}
        />
      </main>
    </div>
  );
}

export default App;

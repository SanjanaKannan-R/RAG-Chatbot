import React from 'react';
import type { DocumentItem } from '../types';
import { UploadBox } from './UploadBox';
import { FileText, Table, FileSpreadsheet, Trash2, RefreshCw, Database, Layers } from 'lucide-react';

interface DocumentSidebarProps {
  documents: DocumentItem[];
  apiBase: string;
  isLoading: boolean;
  onRefresh: () => void;
  onDeleteDocument: (id: number) => void;
  onUploadSuccess: (doc: DocumentItem) => void;
}

export const DocumentSidebar: React.FC<DocumentSidebarProps> = ({
  documents,
  apiBase,
  isLoading,
  onRefresh,
  onDeleteDocument,
  onUploadSuccess,
}) => {
  const getFileIcon = (fileType: string) => {
    switch (fileType.toLowerCase()) {
      case 'pdf':
        return <FileText className="w-4 h-4 text-rose-400" />;
      case 'csv':
        return <Table className="w-4 h-4 text-emerald-400" />;
      default:
        return <FileSpreadsheet className="w-4 h-4 text-sky-400" />;
    }
  };

  return (
    <aside className="w-80 h-full bg-slate-950 border-r border-slate-800 flex flex-col shrink-0 select-none">
      {/* Brand header */}
      <div className="p-4 border-b border-slate-800 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="p-2 bg-indigo-600/20 border border-indigo-500/40 rounded-lg text-indigo-400">
            <Database className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-sm font-bold text-white tracking-wide">Citation-Grounded RAG</h1>
            <p className="text-[11px] text-slate-400">SQLite + sqlite-vec Store</p>
          </div>
        </div>
      </div>

      {/* Upload section */}
      <div className="p-4 border-b border-slate-800">
        <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2.5 flex items-center justify-between">
          <span>Ingest Knowledge Base</span>
        </div>
        <UploadBox apiBase={apiBase} onUploadSuccess={onUploadSuccess} />
      </div>

      {/* Documents list header */}
      <div className="px-4 py-2.5 border-b border-slate-800/80 flex items-center justify-between bg-slate-900/40">
        <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-400 uppercase tracking-wider">
          <Layers className="w-3.5 h-3.5 text-slate-500" />
          <span>Ingested Documents ({documents.length})</span>
        </div>
        <button
          onClick={onRefresh}
          disabled={isLoading}
          className="p-1 text-slate-400 hover:text-white rounded hover:bg-slate-800 transition-colors cursor-pointer"
          title="Refresh document list"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Documents list items */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {documents.length === 0 ? (
          <div className="text-center py-10 px-4 text-slate-500 text-xs">
            No documents uploaded yet.
            <br />
            Upload PDF, TXT, or CSV files above to start asking grounded questions.
          </div>
        ) : (
          documents.map((doc) => (
            <div
              key={doc.id}
              className="p-2.5 bg-slate-900/70 hover:bg-slate-900 border border-slate-800 rounded-lg transition-all group flex items-start justify-between gap-2"
            >
              <div className="flex items-start gap-2.5 min-w-0">
                <div className="mt-0.5 shrink-0">{getFileIcon(doc.file_type)}</div>
                <div className="min-w-0">
                  <div className="text-xs font-medium text-slate-200 truncate" title={doc.filename}>
                    {doc.filename}
                  </div>
                  <div className="flex items-center gap-1.5 mt-1 text-[11px] text-slate-400">
                    <span className="font-mono text-indigo-400 bg-indigo-950/80 px-1 rounded border border-indigo-900/60">
                      {doc.num_chunks} chunks
                    </span>
                    <span
                      className={`px-1 rounded text-[10px] uppercase font-semibold ${
                        doc.status === 'ready'
                          ? 'text-emerald-400 bg-emerald-950/60'
                          : doc.status === 'processing'
                          ? 'text-amber-400 bg-amber-950/60 animate-pulse'
                          : 'text-rose-400 bg-rose-950/60'
                      }`}
                    >
                      {doc.status}
                    </span>
                  </div>
                </div>
              </div>

              <button
                onClick={() => onDeleteDocument(doc.id)}
                className="opacity-0 group-hover:opacity-100 p-1 text-slate-500 hover:text-rose-400 hover:bg-slate-800 rounded transition-all shrink-0 cursor-pointer"
                title="Delete document and remove all vectors"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
          ))
        )}
      </div>

      {/* Footer system status */}
      <div className="p-3 border-t border-slate-800 text-[11px] text-slate-400 flex items-center justify-between bg-slate-950/90">
        <div className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
          <span>SQLite-Vec ANN Ready</span>
        </div>
        <span className="font-mono text-slate-500">v1.0.0</span>
      </div>
    </aside>
  );
};

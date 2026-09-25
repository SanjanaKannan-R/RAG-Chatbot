import React, { useState, useRef } from 'react';
import { UploadCloud, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';
import type { DocumentItem } from '../types';

interface UploadBoxProps {
  apiBase: string;
  onUploadSuccess: (doc: DocumentItem) => void;
}

export const UploadBox: React.FC<UploadBoxProps> = ({ apiBase, onUploadSuccess }) => {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' } | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      uploadFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      uploadFile(e.target.files[0]);
    }
  };

  const uploadFile = async (file: File) => {
    const ext = file.name.slice(file.name.lastIndexOf('.')).toLowerCase();
    if (!['.pdf', '.txt', '.csv'].includes(ext)) {
      setMessage({
        text: `Unsupported file type: ${ext}. Please upload .pdf, .txt, or .csv files.`,
        type: 'error'
      });
      return;
    }

    setIsUploading(true);
    setMessage(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch(`${apiBase}/documents/upload`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Upload failed' }));
        throw new Error(errorData.detail || `Upload failed with status ${response.status}`);
      }

      const newDoc: DocumentItem = await response.json();
      setMessage({
        text: `"${file.name}" ingested successfully (${newDoc.num_chunks} chunks indexed)`,
        type: 'success'
      });
      onUploadSuccess(newDoc);
    } catch (err: any) {
      setMessage({
        text: err.message || 'Error uploading file',
        type: 'error'
      });
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  return (
    <div className="w-full">
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => !isUploading && fileInputRef.current?.click()}
        className={`relative border-2 border-dashed rounded-xl p-4 text-center cursor-pointer transition-all ${
          isDragging
            ? 'border-indigo-500 bg-indigo-500/10'
            : 'border-slate-700 hover:border-slate-500 bg-slate-900/60 hover:bg-slate-900'
        } ${isUploading ? 'opacity-60 cursor-not-allowed' : ''}`}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.txt,.csv"
          onChange={handleFileChange}
          className="hidden"
          disabled={isUploading}
        />

        <div className="flex flex-col items-center justify-center gap-2">
          {isUploading ? (
            <Loader2 className="w-8 h-8 text-indigo-400 animate-spin" />
          ) : (
            <UploadCloud className="w-8 h-8 text-slate-400 group-hover:text-indigo-400 transition-colors" />
          )}

          <div className="text-xs font-medium text-slate-200">
            {isUploading ? 'Ingesting, chunking & indexing...' : 'Click or drag files here to upload'}
          </div>

          <div className="flex items-center gap-2 text-[10px] text-slate-500">
            <span className="bg-slate-800 px-1.5 py-0.5 rounded font-mono">PDF</span>
            <span className="bg-slate-800 px-1.5 py-0.5 rounded font-mono">TXT</span>
            <span className="bg-slate-800 px-1.5 py-0.5 rounded font-mono">CSV</span>
          </div>
        </div>
      </div>

      {message && (
        <div
          className={`mt-2 p-2 rounded text-xs flex items-start gap-2 ${
            message.type === 'success'
              ? 'bg-emerald-950/60 border border-emerald-800/60 text-emerald-300'
              : 'bg-rose-950/60 border border-rose-800/60 text-rose-300'
          }`}
        >
          {message.type === 'success' ? (
            <CheckCircle className="w-4 h-4 shrink-0 text-emerald-400 mt-0.5" />
          ) : (
            <AlertCircle className="w-4 h-4 shrink-0 text-rose-400 mt-0.5" />
          )}
          <span className="break-all">{message.text}</span>
        </div>
      )}
    </div>
  );
};

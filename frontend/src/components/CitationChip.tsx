import React, { useState } from 'react';
import type { CitationItem, ChunkDetail } from '../types';
import { ChevronDown, ChevronUp, FileText, CheckCircle2, Bookmark } from 'lucide-react';

interface CitationChipProps {
  citation: CitationItem;
  apiBase: string;
}

export const CitationChip: React.FC<CitationChipProps> = ({ citation, apiBase }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [fullDetail, setFullDetail] = useState<ChunkDetail | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  // Determine display label
  const fileName = citation.source_file || `Chunk #${citation.chunk_id}`;
  let locationTag = '';
  if (citation.page_number) {
    locationTag = `p. ${citation.page_number}`;
  } else if (citation.line_or_row_range) {
    locationTag = citation.line_or_row_range;
  }

  const label = locationTag ? `${fileName}, ${locationTag}` : fileName;

  const toggleExpand = async () => {
    const nextState = !isExpanded;
    setIsExpanded(nextState);

    // If expanding and don't have chunk_text, fetch detail from backend
    if (nextState && !citation.chunk_text && !fullDetail && !isLoading) {
      setIsLoading(true);
      try {
        const res = await fetch(`${apiBase}/chunks/${citation.chunk_id}`);
        if (res.ok) {
          const data: ChunkDetail = await res.json();
          setFullDetail(data);
        }
      } catch (err) {
        console.error('Failed to load chunk detail:', err);
      } finally {
        setIsLoading(false);
      }
    }
  };

  const storedText = citation.chunk_text || fullDetail?.chunk_text || '';
  const snippet = citation.quoted_snippet?.trim() || '';

  // Function to render chunk text with highlighted snippet
  const renderHighlightedChunk = (text: string, querySnippet: string) => {
    if (!querySnippet || !text) {
      return <span>{text || 'No chunk text available.'}</span>;
    }

    const lowerText = text.toLowerCase();
    const lowerSnippet = querySnippet.toLowerCase();
    const matchIdx = lowerText.indexOf(lowerSnippet);

    if (matchIdx === -1) {
      // If exact phrase not matched, try matching first 40 chars
      const sub = lowerSnippet.slice(0, 40).trim();
      const partialIdx = sub ? lowerText.indexOf(sub) : -1;
      if (partialIdx !== -1) {
        const before = text.slice(0, partialIdx);
        const highlighted = text.slice(partialIdx, partialIdx + sub.length);
        const after = text.slice(partialIdx + sub.length);
        return (
          <>
            <span>{before}</span>
            <mark className="bg-amber-400/30 text-amber-200 border-b border-amber-400 font-semibold px-1 rounded">
              {highlighted}
            </mark>
            <span>{after}</span>
          </>
        );
      }
      return <span>{text}</span>;
    }

    const before = text.slice(0, matchIdx);
    const highlighted = text.slice(matchIdx, matchIdx + querySnippet.length);
    const after = text.slice(matchIdx + querySnippet.length);

    return (
      <>
        <span>{before}</span>
        <mark className="bg-amber-400/30 text-amber-200 border-b border-amber-400 font-semibold px-1 rounded">
          {highlighted}
        </mark>
        <span>{after}</span>
      </>
    );
  };

  return (
    <div className="inline-block my-1 mr-2">
      {/* Clickable chip */}
      <button
        type="button"
        onClick={toggleExpand}
        className={`inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-md border transition-all ${
          isExpanded
            ? 'bg-indigo-600/30 border-indigo-400 text-indigo-200 shadow-sm'
            : 'bg-slate-800/80 hover:bg-slate-700/80 border-slate-700 text-slate-300 hover:text-white'
        }`}
        title="Click to inspect and verify the literal SQLite chunk text"
      >
        <FileText className="w-3.5 h-3.5 text-indigo-400" />
        <span className="font-mono truncate max-w-[220px]">[{label}]</span>
        {isExpanded ? (
          <ChevronUp className="w-3 h-3 text-slate-400" />
        ) : (
          <ChevronDown className="w-3 h-3 text-slate-400" />
        )}
      </button>

      {/* Expandable card inline beneath the chip */}
      {isExpanded && (
        <div className="mt-2 p-3.5 bg-slate-900 border border-indigo-500/40 rounded-lg text-left shadow-xl max-w-2xl text-xs space-y-2.5 animate-fadeIn">
          {/* Header metadata */}
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <div className="flex items-center gap-2">
              <span className="bg-indigo-950 text-indigo-300 font-mono px-2 py-0.5 rounded border border-indigo-800/60 font-semibold">
                Chunk #{citation.chunk_id}
              </span>
              <span className="text-slate-400 font-medium">{fileName}</span>
              {citation.line_or_row_range && (
                <span className="bg-slate-800 text-slate-300 px-1.5 py-0.5 rounded text-[11px]">
                  {citation.line_or_row_range}
                </span>
              )}
            </div>
            <div className="flex items-center gap-1 text-[11px] text-emerald-400">
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>Verified in SQLite</span>
            </div>
          </div>

          {/* Offsets info if available */}
          {(citation.char_start !== null && citation.char_end !== null) && (
            <div className="text-[11px] text-slate-400 flex items-center gap-2">
              <Bookmark className="w-3 h-3 text-slate-500" />
              <span>
                Document character span: <code className="bg-slate-800 px-1 rounded text-slate-300">{citation.char_start}</code> to <code className="bg-slate-800 px-1 rounded text-slate-300">{citation.char_end}</code>
              </span>
            </div>
          )}

          {/* Quoted claim citation */}
          {citation.quoted_snippet && (
            <div className="bg-slate-950/70 border-l-2 border-amber-400 p-2 rounded">
              <div className="text-[10px] uppercase font-bold text-amber-400 tracking-wider mb-1">
                Claim Grounding Snippet
              </div>
              <div className="text-slate-200 italic font-mono text-[11px]">
                "{citation.quoted_snippet}"
              </div>
            </div>
          )}

          {/* Literal stored chunk text with highlighting */}
          <div>
            <div className="text-[10px] uppercase font-bold text-slate-400 tracking-wider mb-1">
              Literal Stored Chunk Text (Source of Truth)
            </div>
            {isLoading ? (
              <div className="py-3 text-center text-slate-400 animate-pulse">Loading chunk from database...</div>
            ) : (
              <div className="p-2.5 bg-slate-950 rounded border border-slate-800/80 font-mono text-[11px] leading-relaxed text-slate-300 max-h-48 overflow-y-auto whitespace-pre-wrap select-text">
                {renderHighlightedChunk(storedText, snippet)}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

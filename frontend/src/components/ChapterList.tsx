import type { Chapter } from '../types';

interface ChapterListProps {
  chapters: Chapter[];
  currentChapterId?: string;
  onSelect: (chapter: Chapter) => void;
}

export function ChapterList({ chapters, currentChapterId, onSelect }: ChapterListProps) {
  return (
    <div className="space-y-1">
      {chapters.map((ch) => (
        <button
          key={ch.id}
          onClick={() => onSelect(ch)}
          className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors ${
            currentChapterId === ch.id
              ? 'bg-blue-50 text-blue-700'
              : 'hover:bg-gray-50 text-gray-600'
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="truncate">
              {ch.chapter_number}. {ch.title || `第${ch.chapter_number}章`}
            </span>
            <span className="text-xs text-gray-400">{ch.word_count}字</span>
          </div>
          {ch.branch_name !== '主线' && (
            <span className="text-xs text-amber-600 ml-1">[{ch.branch_name}]</span>
          )}
        </button>
      ))}
    </div>
  );
}

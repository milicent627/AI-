import type { Summary } from '../types';

interface SummaryListProps {
  summaries: Summary[];
}

export function SummaryList({ summaries }: SummaryListProps) {
  if (summaries.length === 0) {
    return <p className="text-gray-500 text-sm p-3">暂无总结，归档章节后将自动生成</p>;
  }

  return (
    <div className="space-y-2">
      {summaries.map((s) => (
        <div
          key={s.id}
          className={`bg-gray-950 rounded-lg p-3 text-sm ${
            s.type === 'large' ? 'border border-amber-800' : 'border border-gray-800'
          }`}
        >
          <div className="flex items-center justify-between mb-1">
            <span
              className={`text-xs font-medium ${
                s.type === 'large' ? 'text-amber-400' : 'text-blue-400'
              }`}
            >
              {s.type === 'large' ? `📋 大总结` : `📝 小总结 Lv${s.level}`}
            </span>
            <span className="text-xs text-gray-500">
              {s.word_count_before?.toLocaleString()}→{s.word_count_after?.toLocaleString()}字
            </span>
          </div>
          <p className="text-gray-300 whitespace-pre-wrap">{s.content}</p>
        </div>
      ))}
    </div>
  );
}

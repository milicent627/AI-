import type { Foreshadowing } from '../types';

interface ForeshadowingListProps {
  foreshadowings: Foreshadowing[];
}

const statusConfig: Record<string, { color: string; bg: string; label: string; border: string }> = {
  planted: { color: 'text-blue-400', bg: 'bg-blue-900/30', label: '已埋下', border: 'border-blue-600' },
  developing: { color: 'text-amber-400', bg: 'bg-amber-900/30', label: '推进中', border: 'border-amber-600' },
  revealed: { color: 'text-green-400', bg: 'bg-green-900/30', label: '已揭示', border: 'border-green-600' },
};

export function ForeshadowingList({ foreshadowings }: ForeshadowingListProps) {
  if (foreshadowings.length === 0) {
    return <p className="text-gray-500 text-sm p-3">暂无伏笔，续写后自动检测</p>;
  }

  return (
    <div className="space-y-2">
      {foreshadowings.map((f) => {
        const cfg = statusConfig[f.status] || statusConfig.planted;
        return (
          <div
            key={f.id}
            className={`bg-gray-950 border rounded-lg p-3 text-sm border-l-2 ${cfg.border}`}
          >
            <div className="flex items-center justify-between">
              <span className="font-medium text-gray-100">{f.title}</span>
              <span className={`text-xs px-1.5 py-0.5 rounded ${cfg.bg} ${cfg.color}`}>
                {cfg.label}
              </span>
            </div>
            <p className="mt-1 text-gray-500">{f.description}</p>
          </div>
        );
      })}
    </div>
  );
}

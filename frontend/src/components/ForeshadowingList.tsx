import type { Foreshadowing } from '../types';

interface ForeshadowingListProps {
  foreshadowings: Foreshadowing[];
}

const statusConfig: Record<string, { color: string; bg: string; label: string; border: string }> = {
  planted: { color: 'text-blue-600', bg: 'bg-blue-50', label: '已埋下', border: 'border-blue-400' },
  developing: { color: 'text-amber-600', bg: 'bg-amber-50', label: '推进中', border: 'border-amber-400' },
  revealed: { color: 'text-green-600', bg: 'bg-green-50', label: '已揭示', border: 'border-green-400' },
};

export function ForeshadowingList({ foreshadowings }: ForeshadowingListProps) {
  if (foreshadowings.length === 0) {
    return <p className="text-gray-400 text-sm p-3">暂无伏笔，续写后自动检测</p>;
  }

  return (
    <div className="space-y-2">
      {foreshadowings.map((f) => {
        const cfg = statusConfig[f.status] || statusConfig.planted;
        return (
          <div
            key={f.id}
            className={`bg-white border rounded-lg p-3 text-sm border-l-2 ${cfg.border}`}
          >
            <div className="flex items-center justify-between">
              <span className="font-medium text-gray-800">{f.title}</span>
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

import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Save, ListOrdered } from 'lucide-react';

interface TopToolbarProps {
  title: string;
  storyId: string;
  saveStatus: 'saved' | 'saving' | 'unsaved';
  onSave: () => void;
}

export function TopToolbar({ title, storyId, saveStatus, onSave }: TopToolbarProps) {
  const navigate = useNavigate();

  return (
    <header className="border-b border-gray-200 px-4 py-2 flex items-center justify-between shrink-0 bg-white">
      <div className="flex items-center gap-3">
        <button onClick={() => navigate('/')} className="p-1 hover:bg-gray-100 rounded text-gray-500">
          <ArrowLeft size={18} />
        </button>
        <span className="font-bold text-gray-800">{title || '加载中...'}</span>
        <span className="text-xs text-gray-400">
          {saveStatus === 'saved' ? '✅ 已保存' : saveStatus === 'saving' ? '💾 保存中...' : '📝 未保存'}
        </span>
      </div>
      <div className="flex items-center gap-2">
        <button
          onClick={() => navigate(`/order/${storyId}`)}
          className="px-2 py-1 text-xs border border-gray-200 rounded hover:bg-gray-50 flex items-center gap-1 text-gray-600"
        >
          <ListOrdered size={14} /> 排序
        </button>
        <button
          onClick={onSave}
          className="px-3 py-1 text-xs bg-green-600 text-white rounded hover:bg-green-700 flex items-center gap-1"
        >
          <Save size={14} /> 保存
        </button>
      </div>
    </header>
  );
}

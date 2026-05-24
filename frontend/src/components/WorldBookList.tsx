import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Eye, EyeOff, Edit3, Trash2, Download, Upload, Plus, ChevronUp, ChevronDown } from 'lucide-react';
import type { WorldBookEntry } from '../types';
import { api } from '../api/client';

interface WorldBookListProps {
  entries: WorldBookEntry[];
  storyId: string;
  worldBookName: string;
  onWorldBookNameChange: (name: string) => void;
  onEntriesChange: (entries: WorldBookEntry[]) => void;
}

const categoryIcons: Record<string, string> = {
  character: '👤',
  faction: '🏛',
  location: '📍',
  item: '📦',
  power_system: '⚡',
  catchphrase: '💬',
  custom: '🏷',
};

export function WorldBookList({
  entries,
  storyId,
  worldBookName,
  onWorldBookNameChange,
  onEntriesChange,
}: WorldBookListProps) {
  const navigate = useNavigate();
  const [exportFormat, setExportFormat] = useState<'bookwright' | 'sillytavern'>('bookwright');

  const handleToggleStatus = async (entryId: string, currentStatus: string) => {
    const newStatus = currentStatus === 'active' ? 'inactive' : 'active';
    await api.updateWorldEntry(storyId, entryId, { status: newStatus });
    const d = await api.listWorldEntries(storyId);
    onEntriesChange(d.entries || []);
  };

  const handleMove = async (entryId: string, direction: 'up' | 'down') => {
    const sorted = [...entries].sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0));
    const idx = sorted.findIndex((e) => e.id === entryId);
    if (idx < 0) return;
    if (direction === 'up' && idx === 0) return;
    if (direction === 'down' && idx >= sorted.length - 1) return;
    const targetIdx = direction === 'up' ? idx - 1 : idx + 1;
    [sorted[idx], sorted[targetIdx]] = [sorted[targetIdx], sorted[idx]];
    await api.reorderWorldEntries(storyId, sorted.map((e) => e.id));
    const d = await api.listWorldEntries(storyId);
    onEntriesChange(d.entries || []);
  };

  const handleDelete = async (entryId: string) => {
    if (!confirm('确定删除此条目？')) return;
    await api.deleteWorldEntry(storyId, entryId);
    onEntriesChange(entries.filter((e) => e.id !== entryId));
  };

  const handleExport = () => {
    api.exportWorldBook(storyId, exportFormat).catch((err: Error) =>
      alert(`导出失败: ${err.message}`),
    );
  };

  const handleImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files?.length) return;
    try {
      const result = await api.importWorldBook(storyId, e.target.files[0]);
      alert(`导入完成：新增 ${result.imported} 条，更新 ${result.updated} 条，关系 ${result.relations_imported} 条`);
      const d = await api.listWorldEntries(storyId);
      onEntriesChange(d.entries || []);
    } catch (err: unknown) {
      alert(`导入失败: ${err instanceof Error ? err.message : '未知错误'}`);
    }
    e.target.value = '';
  };

  const sorted = [...entries].sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0));

  return (
    <div className="space-y-1.5">
      <div className="mb-2">
        <input
          className="w-full bg-transparent text-sm font-semibold border-b border-transparent hover:border-gray-600 focus:border-blue-500 outline-none px-1 py-0.5 text-gray-200"
          value={worldBookName}
          placeholder="世界书名称"
          onChange={(e) => onWorldBookNameChange(e.target.value)}
        />
      </div>

      <button
        onClick={() => navigate(`/editor/${storyId}/world/new`)}
        className="w-full flex items-center justify-center gap-1 px-2 py-1.5 text-xs border border-dashed border-gray-700 rounded-lg hover:border-blue-500 hover:text-blue-500 text-gray-500 mb-2"
      >
        <Plus size={14} /> 新增条目
      </button>

      {sorted.map((entry, idx, arr) => (
        <div
          key={entry.id}
          className="bg-gray-900 rounded-lg overflow-hidden text-sm"
        >
          <div className="p-2 flex items-center gap-1.5">
            <div className="flex flex-col gap-0.5">
              <button
                onClick={() => handleMove(entry.id, 'up')}
                disabled={idx === 0}
                className="text-gray-500 hover:text-gray-300 disabled:opacity-20"
              >
                <ChevronUp size={10} />
              </button>
              <button
                onClick={() => handleMove(entry.id, 'down')}
                disabled={idx >= arr.length - 1}
                className="text-gray-500 hover:text-gray-300 disabled:opacity-20"
              >
                <ChevronDown size={10} />
              </button>
            </div>
            <span className="text-xs shrink-0">{categoryIcons[entry.category] || '🏷'}</span>
            <span className="font-medium truncate flex-1 text-xs text-gray-200">{entry.name}</span>
            <span className="text-xs text-amber-500 shrink-0">{'★'.repeat(entry.importance)}</span>
            <button
              onClick={() => handleToggleStatus(entry.id, entry.status)}
              className={`p-0.5 rounded hover:bg-gray-700 ${
                entry.status === 'active' ? 'text-green-500' : 'text-gray-300 hover:text-gray-300'
              }`}
              title={entry.status === 'active' ? '已启用' : '已禁用'}
            >
              {entry.status === 'active' ? <Eye size={10} /> : <EyeOff size={10} />}
            </button>
            <button
              onClick={() => navigate(`/editor/${storyId}/world/${entry.id}`)}
              className="p-0.5 rounded hover:bg-gray-700 text-gray-500 hover:text-gray-300"
            >
              <Edit3 size={10} />
            </button>
            <button
              onClick={() => handleDelete(entry.id)}
              className="p-0.5 rounded hover:bg-red-900/30 text-gray-500 hover:text-red-400"
            >
              <Trash2 size={10} />
            </button>
          </div>

          <div className="border-t border-gray-800 px-3 py-1.5">
            <p className="text-xs text-gray-500 whitespace-pre-wrap line-clamp-3">
              {entry.description || '(无描述)'}
            </p>
            {entry.aliases?.length > 0 && (
              <p className="text-xs text-gray-500 mt-1">别名: {entry.aliases.join(', ')}</p>
            )}
            {entry.attributes && entry.category === 'character' && (
              <div className="mt-1 text-xs text-gray-500 space-y-0.5">
                {entry.attributes.identity && <span>身份: {entry.attributes.identity} </span>}
                {entry.attributes.personality?.length > 0 && (
                  <span>性格: {entry.attributes.personality.join('、')} </span>
                )}
                {entry.attributes.abilities?.length > 0 && (
                  <span>能力: {entry.attributes.abilities.join('、')}</span>
                )}
              </div>
            )}
          </div>
        </div>
      ))}

      {entries.length === 0 && (
        <p className="text-gray-500 text-sm p-3 text-center">暂无世界书条目</p>
      )}

      <div className="flex gap-1 mt-3 pt-3 border-t border-gray-800">
        <select
          value={exportFormat}
          onChange={(e) => setExportFormat(e.target.value as 'bookwright' | 'sillytavern')}
          className="bg-gray-800 border border-gray-800 rounded px-1 py-1 text-xs w-16"
        >
          <option value="bookwright">BW</option>
          <option value="sillytavern">ST</option>
        </select>
        <button
          onClick={handleExport}
          className="flex items-center gap-1 px-2 py-1 text-xs bg-gray-800 border border-gray-800 rounded hover:bg-gray-700 text-gray-300"
        >
          <Download size={12} /> 导出
        </button>
        <button
          onClick={() => document.getElementById('worldbook-import')?.click()}
          className="flex items-center gap-1 px-2 py-1 text-xs bg-gray-800 border border-gray-800 rounded hover:bg-gray-700 text-gray-300"
        >
          <Upload size={12} /> 导入
        </button>
        <input
          id="worldbook-import"
          type="file"
          accept=".json"
          onChange={handleImport}
          className="hidden"
        />
      </div>
    </div>
  );
}

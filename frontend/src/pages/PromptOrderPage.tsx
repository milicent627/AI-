import { useEffect, useState, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import {
  ArrowLeft, Save, GripVertical, ChevronUp, ChevronDown,
  Eye, EyeOff, Plus, Trash2, Sparkles, Wand2, FileText, RefreshCw, X, MessageSquare
} from 'lucide-react';

const FUNCTION_LABELS: Record<string, string> = {
  continuation: '续写',
  polishing: '润色',
  small_summary: '小总结',
  large_summary: '大总结',
  world_analysis: '世界书分析',
  foreshadowing: '伏笔检测',
};

const FUNCTIONS = Object.keys(FUNCTION_LABELS);

interface OrderItem {
  id: string;
  item_type: 'fragment' | 'world_entry' | 'summary' | 'foreshadowing' | 'style_guide';
  source_id: string;
  sort_order: number;
  role: 'system' | 'user';
  is_active: boolean;
  trigger_words: string[] | null;
  content_local?: string;
  content?: string;
  name?: string;
  display_text?: string;
}

export default function PromptOrderPage() {
  const { storyId } = useParams<{ storyId: string }>();
  const navigate = useNavigate();

  const [func, setFunc] = useState<string>('continuation');
  const [items, setItems] = useState<OrderItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [editNumId, setEditNumId] = useState<string | null>(null);
  const [editNumVal, setEditNumVal] = useState('');
  const [editTriggerId, setEditTriggerId] = useState<string | null>(null);
  const [editTriggerVal, setEditTriggerVal] = useState('');

  const [showPreview, setShowPreview] = useState(false);
  const [previewMessages, setPreviewMessages] = useState<any[]>([]);
  const [previewLoading, setPreviewLoading] = useState(false);

  const handlePreview = async () => {
    if (!storyId) return;
    setPreviewLoading(true);
    setShowPreview(true);
    try {
      const data = await api.previewOrder(storyId, func);
      setPreviewMessages(data.messages || []);
    } catch (err: any) {
      alert(`获取预览失败: ${err.message}`);
      setPreviewMessages([]);
    } finally {
      setPreviewLoading(false);
    }
  };

  const loadOrder = useCallback(async () => {
    if (!storyId) return;
    setLoading(true);
    try {
      const data = await api.getOrder(storyId, func);
      const sorted = [...(data.items || [])].sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0));
      setItems(sorted);
    } catch (err: any) {
      console.error('Failed to load order:', err);
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, [storyId, func]);

  useEffect(() => {
    loadOrder();
  }, [loadOrder]);

  const handleSave = async () => {
    if (!storyId) return;
    try {
      await api.saveOrder(storyId, func, items);
      alert('保存成功');
    } catch (err: any) {
      alert(`保存失败: ${err.message}`);
    }
  };

  const handleSeed = async () => {
    if (!storyId) return;
    try {
      await api.seedOrder(storyId, func);
      await loadOrder();
      alert('种子已生成');
    } catch (err: any) {
      alert(`生成失败: ${err.message}`);
    }
  };

  const handleMove = (idx: number, direction: -1 | 1) => {
    const newIdx = idx + direction;
    if (newIdx < 0 || newIdx >= items.length) return;
    const updated = [...items];
    [updated[idx], updated[newIdx]] = [updated[newIdx], updated[idx]];
    const reindexed = updated.map((item, i) => ({ ...item, sort_order: i + 1 }));
    setItems(reindexed);
  };

  const handleToggleActive = (idx: number) => {
    setItems(prev => prev.map((item, i) =>
      i === idx ? { ...item, is_active: !item.is_active } : item
    ));
  };

  const handleChangeNumber = (idx: number, newNum: number) => {
    const num = Math.max(1, Math.floor(newNum));
    setItems(prev => {
      const updated = prev.map((item, i) =>
        i === idx ? { ...item, sort_order: num } : item
      );
      updated.sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0));
      if (updated.every((item, i) => item.sort_order === i + 1)) return updated;
      return updated.map((item, i) => ({ ...item, sort_order: i + 1 }));
    });
  };

  const isFixedItem = (item: OrderItem): boolean => {
    return item.item_type === 'summary' || item.item_type === 'foreshadowing' || item.item_type === 'style_guide';
  };

  const handleDelete = (idx: number) => {
    if (isFixedItem(items[idx])) {
      alert('总结/伏笔/风格指南为固定条目，不能删除');
      return;
    }
    if (!confirm('确定删除此条目？')) return;
    setItems(prev => {
      const updated = prev.filter((_, i) => i !== idx);
      return updated.map((item, i) => ({ ...item, sort_order: i + 1 }));
    });
  };

  const handleAddFragment = () => {
    const newItem: OrderItem = {
      id: `new-fragment-${Date.now()}`,
      item_type: 'fragment',
      source_id: '',
      sort_order: items.length + 1,
      role: 'system',
      is_active: true,
      trigger_words: null,
      content_local: '新提示词条目',
    };
    setItems(prev => [...prev, newItem]);
  };

  const handleEditTriggerWords = (idx: number, words: string) => {
    setItems(prev => prev.map((item, i) =>
      i === idx ? {
        ...item,
        trigger_words: words
          .split(',')
          .map(w => w.trim())
          .filter(Boolean)
      } : item
    ));
  };

  const getDisplayContent = (item: OrderItem): string => {
    if (item.item_type === 'summary') {
      const summaryLabels: Record<string, string> = {
        chapter_content: '正文',
        small_summaries: '小总结',
        large_summary: '大总结',
      };
      return summaryLabels[item.source_id] || `总结 - ${item.source_id}`;
    }
    if (item.item_type === 'foreshadowing') {
      return '活跃伏笔';
    }
    if (item.item_type === 'style_guide') {
      return '风格指南';
    }
    if (item.item_type === 'world_entry') {
      return item.name || item.display_text || item.content_local || '(未命名)';
    }
    return item.content_local || item.content || '';
  };

  const getTypeLabel = (itemType: string): string => {
    switch (itemType) {
      case 'fragment': return '片段';
      case 'world_entry': return '世界书';
      case 'summary': return '总结';
      case 'foreshadowing': return '伏笔';
      case 'style_guide': return '风格';
      default: return itemType;
    }
  };

  const getTypeColor = (itemType: string): string => {
    switch (itemType) {
      case 'fragment': return 'bg-green-900/50 text-green-400 border-green-800';
      case 'world_entry': return 'bg-amber-900/50 text-amber-400 border-amber-800';
      case 'summary': return 'bg-blue-900/50 text-blue-400 border-blue-800';
      case 'foreshadowing': return 'bg-pink-900/50 text-pink-400 border-pink-800';
      case 'style_guide': return 'bg-violet-900/50 text-violet-400 border-violet-800';
      default: return 'bg-gray-800 text-gray-400 border-gray-700';
    }
  };

  return (
    <div className="h-screen flex flex-col bg-gray-950 text-gray-100">
      {/* Header */}
      <header className="border-b border-gray-800 px-4 py-2 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate(`/editor/${storyId}`)}
            className="p-1 hover:bg-gray-800 rounded text-gray-400 hover:text-gray-200 transition-colors"
            title="返回"
          >
            <ArrowLeft size={18} />
          </button>
          <h1 className="font-bold text-sm">提示词排序管理</h1>
          <span className="text-xs text-gray-300">
            {FUNCTION_LABELS[func] || func}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handlePreview}
            className="flex items-center gap-1 px-3 py-1.5 text-xs bg-purple-700/60 border border-purple-700 rounded hover:bg-purple-700 transition-colors"
            title="查看组装后的完整提示词"
          >
            <MessageSquare size={13} /> 查看提示词
          </button>
          <button
            onClick={handleSeed}
            className="flex items-center gap-1 px-3 py-1.5 text-xs bg-amber-700/60 border border-amber-700 rounded hover:bg-amber-700 transition-colors"
            title="从预设生成种子"
          >
            <RefreshCw size={13} /> 从预设生成种子
          </button>
          <button
            onClick={handleSave}
            className="flex items-center gap-1 px-3 py-1.5 text-xs bg-blue-600 rounded hover:bg-blue-700 transition-colors"
          >
            <Save size={13} /> 保存
          </button>
        </div>
      </header>

      {/* Function tabs */}
      <nav className="border-b border-gray-800 px-4 py-1.5 shrink-0 flex items-center gap-1 overflow-x-auto">
        {FUNCTIONS.map((f) => (
          <button
            key={f}
            onClick={() => setFunc(f)}
            className={`px-3 py-1 text-xs rounded-md whitespace-nowrap transition-colors ${
              func === f
                ? 'bg-blue-600 text-white'
                : 'bg-gray-900 text-gray-400 hover:bg-gray-800 hover:text-gray-200 border border-gray-800'
            }`}
          >
            {FUNCTION_LABELS[f]}
          </button>
        ))}
      </nav>

      {/* Toolbar */}
      <div className="border-b border-gray-800 px-4 py-2 shrink-0 flex items-center gap-2">
        <button
          onClick={handleAddFragment}
          className="flex items-center gap-1 px-2.5 py-1.5 text-xs border border-gray-700 rounded-lg hover:border-green-600 hover:text-green-400 text-gray-400 transition-colors"
        >
          <Plus size={13} /> 片段
        </button>
        <div className="flex-1" />
        <span className="text-xs text-gray-300">{items.length} 条</span>
      </div>

      {/* Content */}
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-4xl mx-auto p-4">
          {loading ? (
            <div className="text-center text-gray-500 py-16 text-sm">加载中...</div>
          ) : items.length === 0 ? (
            <div className="text-center text-gray-500 py-16">
              <p className="text-sm">还没有条目，点击「从预设生成种子」或手动添加</p>
            </div>
          ) : (
            <div className="space-y-1">
              {items.map((item, idx) => (
                <div
                  key={item.id}
                  className={`bg-gray-900 border rounded-lg px-3 py-2 flex items-center gap-2 transition-colors ${
                    item.is_active ? 'border-gray-800' : 'border-gray-800/50 opacity-70'
                  }`}
                >
                  {/* Drag handle */}
                  <button
                    className="text-gray-200 hover:text-gray-200 cursor-grab flex-shrink-0"
                    title="拖拽排序"
                  >
                    <GripVertical size={14} />
                  </button>

                  {/* Sort order number */}
                  <div className="flex-shrink-0 w-10">
                    {editNumId === item.id ? (
                      <input
                        autoFocus
                        type="number"
                        min={1}
                        value={editNumVal}
                        onChange={(e) => setEditNumVal(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') {
                            const num = parseInt(editNumVal, 10);
                            if (!isNaN(num) && num >= 1) {
                              handleChangeNumber(idx, num);
                            }
                            setEditNumId(null);
                          }
                          if (e.key === 'Escape') {
                            setEditNumId(null);
                          }
                        }}
                        onBlur={() => setEditNumId(null)}
                        className="w-full bg-gray-800 border border-blue-600 rounded px-1 py-0.5 text-xs text-center outline-none"
                      />
                    ) : (
                      <button
                        onClick={() => {
                          setEditNumId(item.id);
                          setEditNumVal(String(item.sort_order));
                        }}
                        className="w-full text-xs text-gray-500 hover:text-gray-300 bg-gray-800 rounded px-1 py-0.5 cursor-text"
                        title="点击编辑编号"
                      >
                        {String(item.sort_order).padStart(2, '0')}
                      </button>
                    )}
                  </div>

                  {/* Role badge */}
                  <span
                    className={`flex-shrink-0 text-[10px] font-bold px-1.5 py-0.5 rounded ${
                      item.role === 'system'
                        ? 'bg-purple-900/60 text-purple-400'
                        : 'bg-blue-900/60 text-blue-400'
                    }`}
                  >
                    {item.role === 'system' ? 'SYS' : 'USR'}
                  </span>

                  {/* Type badge */}
                  <span
                    className={`flex-shrink-0 text-[10px] px-1.5 py-0.5 rounded border ${getTypeColor(item.item_type)}`}
                  >
                    {getTypeLabel(item.item_type)}
                  </span>

                  {/* Content preview and trigger words */}
                  <div className="flex-1 min-w-0">
                    <div
                      className={`text-xs truncate ${item.is_active ? 'text-gray-300' : 'text-gray-300 italic'}`}
                      title={getDisplayContent(item)}
                    >
                      {getDisplayContent(item)}
                    </div>
                    {item.item_type === 'world_entry' && item.trigger_words && item.trigger_words.length > 0 && (
                      <div className="flex items-center gap-1 mt-0.5 flex-wrap">
                        <span className="text-[10px] text-gray-300">触发:</span>
                        {editTriggerId === item.id ? (
                          <input
                            autoFocus
                            type="text"
                            value={editTriggerVal}
                            onChange={(e) => setEditTriggerVal(e.target.value)}
                            onKeyDown={(e) => {
                              if (e.key === 'Enter') {
                                handleEditTriggerWords(idx, editTriggerVal);
                                setEditTriggerId(null);
                              }
                              if (e.key === 'Escape') {
                                setEditTriggerId(null);
                              }
                            }}
                            onBlur={() => {
                              handleEditTriggerWords(idx, editTriggerVal);
                              setEditTriggerId(null);
                            }}
                            className="flex-1 bg-gray-800 border border-blue-600 rounded px-1 py-0.5 text-[10px] outline-none"
                            placeholder="逗号分隔"
                          />
                        ) : (
                          <button
                            onClick={() => {
                              setEditTriggerId(item.id);
                              setEditTriggerVal((item.trigger_words || []).join(', '));
                            }}
                            className="flex flex-wrap gap-0.5 cursor-text hover:ring-1 hover:ring-blue-600 rounded px-0.5"
                          >
                            {item.trigger_words.map((word, wi) => (
                              <span
                                key={wi}
                                className="text-[9px] bg-amber-900/40 text-amber-400 px-1 py-0.5 rounded"
                              >
                                {word}
                              </span>
                            ))}
                          </button>
                        )}
                      </div>
                    )}
                    {item.item_type === 'world_entry' && (!item.trigger_words || item.trigger_words.length === 0) && (
                      <button
                        onClick={() => {
                          setEditTriggerId(item.id);
                          setEditTriggerVal('');
                        }}
                        className="text-[10px] text-gray-200 hover:text-gray-300 mt-0.5"
                      >
                        + 添加触发词
                      </button>
                    )}
                  </div>

                  {/* Active toggle */}
                  <button
                    onClick={() => handleToggleActive(idx)}
                    className={`flex-shrink-0 p-0.5 rounded hover:bg-gray-800 transition-colors ${
                      item.is_active ? 'text-green-500' : 'text-gray-200 hover:text-gray-300'
                    }`}
                    title={item.is_active ? '已启用' : '已禁用'}
                  >
                    {item.is_active ? <Eye size={14} /> : <EyeOff size={14} />}
                  </button>

                  {/* Up/Down buttons */}
                  <div className="flex-shrink-0 flex flex-col gap-0.5">
                    <button
                      onClick={() => handleMove(idx, -1)}
                      disabled={idx === 0}
                      className="text-gray-300 hover:text-gray-300 disabled:opacity-20 disabled:cursor-not-allowed p-0.5 rounded hover:bg-gray-800"
                      title="上移"
                    >
                      <ChevronUp size={13} />
                    </button>
                    <button
                      onClick={() => handleMove(idx, 1)}
                      disabled={idx >= items.length - 1}
                      className="text-gray-300 hover:text-gray-300 disabled:opacity-20 disabled:cursor-not-allowed p-0.5 rounded hover:bg-gray-800"
                      title="下移"
                    >
                      <ChevronDown size={13} />
                    </button>
                  </div>

                  {/* Delete button */}
                  <button
                    onClick={() => handleDelete(idx)}
                    className="flex-shrink-0 p-0.5 rounded hover:bg-red-900/50 text-gray-300 hover:text-red-400 transition-colors"
                    title="删除"
                  >
                    <Trash2 size={13} />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>

      {/* Preview Modal */}
      {showPreview && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70" onClick={() => setShowPreview(false)}>
          <div className="bg-gray-900 border border-gray-700 rounded-xl w-[900px] max-h-[85vh] flex flex-col shadow-2xl" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between px-5 py-3 border-b border-gray-800 shrink-0">
              <div className="flex items-center gap-2">
                <MessageSquare size={16} className="text-purple-400" />
                <h2 className="font-bold text-sm">组装后的提示词 — {FUNCTION_LABELS[func] || func}</h2>
                <span className="text-xs text-gray-300">{previewMessages.length} 条消息</span>
              </div>
              <button onClick={() => setShowPreview(false)} className="p-1 hover:bg-gray-800 rounded text-gray-400 hover:text-gray-200">
                <X size={18} />
              </button>
            </div>
            <div className="overflow-y-auto p-5 space-y-4 flex-1">
              {previewLoading ? (
                <div className="text-center text-gray-500 py-12">加载中...</div>
              ) : previewMessages.length === 0 ? (
                <div className="text-center text-gray-500 py-12">暂无提示词数据</div>
              ) : (
                previewMessages.map((msg, i) => (
                  <div key={i} className="bg-gray-950 border border-gray-800 rounded-lg overflow-hidden">
                    <div className="flex items-center gap-2 px-4 py-2 bg-gray-900 border-b border-gray-800">
                      <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded ${msg.role === 'system' ? 'bg-blue-900/60 text-blue-300' : 'bg-green-900/60 text-green-300'}`}>
                        {msg.role}
                      </span>
                      <span className={`text-[10px] px-1.5 py-0.5 rounded border ${getTypeColor(msg.item_type)}`}>
                        {getTypeLabel(msg.item_type)}
                      </span>
                      <span className="text-xs text-gray-300 truncate">{msg.name}</span>
                    </div>
                    <pre className="p-4 text-sm text-gray-300 whitespace-pre-wrap break-words font-mono leading-relaxed max-h-64 overflow-y-auto">{msg.content}</pre>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

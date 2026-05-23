import { useEffect, useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import type { ModelConfig, PromptPreset } from '../types';
import { ArrowLeft, Plus, Trash2, Check, Save, Copy, ChevronDown, ChevronUp, GripVertical, EyeOff, Eye, Download, Upload } from 'lucide-react';

const PROVIDERS = [
  { value: 'openai', label: 'OpenAI', models: ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo', 'gpt-3.5-turbo'] },
  { value: 'anthropic', label: 'Anthropic', models: ['claude-sonnet-4-20250514', 'claude-3-5-sonnet-20241022', 'claude-3-5-haiku-20241022', 'claude-3-opus-20240229'] },
  { value: 'deepseek', label: 'DeepSeek', models: ['deepseek-chat', 'deepseek-reasoner'] },
];

const ROLES = [
  { value: 'continuation', label: '续写模型' },
  { value: 'polishing', label: '润色模型' },
  { value: 'small_summary', label: '小总结模型' },
  { value: 'large_summary', label: '大总结模型' },
  { value: 'world_analysis', label: '世界书分析模型' },
  { value: 'foreshadowing', label: '伏笔检测模型' },
];

const PROMPT_ROLES = [
  { value: 'continuation_system', label: '续写 - 系统提示词' },
  { value: 'continuation_user', label: '续写 - 用户提示词' },
  { value: 'polishing_system', label: '润色 - 系统提示词' },
  { value: 'small_summary_user', label: '小总结 - 任务提示词' },
  { value: 'large_summary_user', label: '大总结 - 任务提示词' },
  { value: 'world_analysis_user', label: '世界书分析 - 任务提示词' },
  { value: 'foreshadowing_user', label: '伏笔检测 - 任务提示词' },
];

export default function SettingsPage() {
  const navigate = useNavigate();
  const [tab, setTab] = useState<'models' | 'prompts'>('models');

  // Model state
  const [models, setModels] = useState<ModelConfig[]>([]);
  const [presets, setPresets] = useState<ModelConfig[]>([]);
  const [editing, setEditing] = useState<ModelConfig | null>(null);
  const [form, setForm] = useState({
    name: '', provider: 'openai', model_id: '', api_key: '', base_url: '',
    role: 'continuation', temperature: 0.8, max_tokens: 4096, is_active: true,
  });

  // Prompt preset state
  const [promptPresets, setPromptPresets] = useState<PromptPreset[]>([]);
  const [editingPrompt, setEditingPrompt] = useState<PromptPreset | null>(null);
  const [promptForm, setPromptForm] = useState({ name: '', role: 'continuation_system', content: '' });
  const [expandedPreset, setExpandedPreset] = useState<string | null>(null);
  const [editingFrag, setEditingFrag] = useState<string | null>(null);
  const [fragContent, setFragContent] = useState('');
  const [newFragContent, setNewFragContent] = useState('');

  useEffect(() => {
    api.listModels().then(d => {
      setModels((d.models || []).filter((m: any) => !m.is_preset));
      setPresets((d.models || []).filter((m: any) => m.is_preset));
    }).catch(console.error);
    api.listPromptPresets().then(d => setPromptPresets(d.presets || [])).catch(console.error);
  }, []);

  // --- Model handlers ---
  const saveModel = async () => {
    if (!form.name || !form.api_key) { alert('请填写模型名称和 API Key'); return; }
    if (editing) await api.updateModel(editing.id, form);
    else await api.createModel(form);
    await refreshModels();
    setEditing(null);
    resetForm();
  };

  const saveAsPreset = async () => {
    if (!form.name) { alert('请填写名称'); return; }
    await api.createModel({ ...form, api_key: '', is_preset: true });
    await refreshModels();
    resetForm();
  };

  const loadFromPreset = (preset: ModelConfig) => {
    setForm({
      name: preset.name, provider: preset.provider, model_id: preset.model_id,
      api_key: '', base_url: preset.base_url || '',
      role: preset.role, temperature: preset.temperature, max_tokens: preset.max_tokens, is_active: true,
    });
    setEditing(null);
  };

  const editModel = (m: ModelConfig) => {
    setEditing(m);
    setForm({ name: m.name, provider: m.provider, model_id: m.model_id, api_key: m.api_key, base_url: '', role: m.role, temperature: m.temperature, max_tokens: m.max_tokens, is_active: m.is_active });
  };

  const deleteModel = async (id: string) => {
    if (!confirm('确定删除？')) return;
    await api.deleteModel(id);
    await refreshModels();
  };

  const refreshModels = async () => {
    const d = await api.listModels();
    setModels((d.models || []).filter((m: any) => !m.is_preset));
    setPresets((d.models || []).filter((m: any) => m.is_preset));
  };

  const resetForm = () => {
    setForm({ name: '', provider: 'openai', model_id: '', api_key: '', base_url: '', role: 'continuation', temperature: 0.8, max_tokens: 4096, is_active: true });
  };

  // --- Prompt handlers ---
  const savePrompt = async () => {
    if (!promptForm.name || !promptForm.content) { alert('请填写名称和内容'); return; }
    if (editingPrompt) await api.updatePromptPreset(editingPrompt.id, promptForm);
    else await api.createPromptPreset(promptForm);
    const d = await api.listPromptPresets();
    setPromptPresets(d.presets || []);
    setEditingPrompt(null);
    setPromptForm({ name: '', role: 'continuation_system', content: '' });
  };

  const editPrompt = (p: PromptPreset) => {
    setEditingPrompt(p);
    setPromptForm({ name: p.name, role: p.role, content: p.content });
  };

  const deletePrompt = async (id: string) => {
    if (!confirm('确定删除？')) return;
    await api.deletePromptPreset(id);
    setPromptPresets(promptPresets.filter(p => p.id !== id));
  };

  const refreshPrompts = async () => {
    const d = await api.listPromptPresets();
    setPromptPresets(d.presets || []);
  };

  const [promptExportFormat, setPromptExportFormat] = useState<'bookwright' | 'sillytavern'>('bookwright');
  const handlePromptExport = () => {
    api.exportPromptPresets(undefined, promptExportFormat).catch(err => alert(`导出失败: ${err.message}`));
  };

  const promptImportRef = useRef<HTMLInputElement>(null);

  const handlePromptImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files?.length) return;
    try {
      const result = await api.importPromptPresets(e.target.files[0]);
      alert(`导入完成：新增 ${result.imported} 个预设，更新 ${result.updated} 个预设`);
      refreshPrompts();
    } catch (err: any) {
      alert(`导入失败: ${err.message}`);
    }
    e.target.value = '';
  };

  const providerModels = PROVIDERS.find(p => p.value === form.provider)?.models || [];

  return (
    <div className="flex-1 flex flex-col max-w-3xl mx-auto w-full p-6">
      <input type="file" ref={promptImportRef} onChange={handlePromptImport} accept=".json" className="hidden" />

      <div className="flex items-center gap-3 mb-6">
        <button onClick={() => navigate(-1)} className="p-1 hover:bg-gray-800 rounded"><ArrowLeft size={18} /></button>
        <h1 className="text-xl font-bold">设置</h1>
        <div className="flex gap-1 ml-4">
          <button onClick={() => setTab('models')} className={`px-3 py-1 text-xs rounded ${tab === 'models' ? 'bg-blue-600' : 'bg-gray-800 hover:bg-gray-700'}`}>模型配置</button>
          <button onClick={() => setTab('prompts')} className={`px-3 py-1 text-xs rounded ${tab === 'prompts' ? 'bg-blue-600' : 'bg-gray-800 hover:bg-gray-700'}`}>提示词预设</button>
        </div>
      </div>

      {tab === 'models' && (
        <>
          {/* Model form */}
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 mb-6">
            <h2 className="font-bold mb-4">{editing ? '编辑模型' : '添加新模型'}</h2>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-gray-500">名称</label>
                <input className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm mt-1" placeholder="例如：主力续写"
                  value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} />
              </div>
              <div>
                <label className="text-xs text-gray-500">用途</label>
                <select className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm mt-1" value={form.role}
                  onChange={e => setForm({ ...form, role: e.target.value })}>
                  {ROLES.map(r => <option key={r.value} value={r.value}>{r.label}</option>)}
                </select>
              </div>
              <div>
                <label className="text-xs text-gray-500">提供商</label>
                <select className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm mt-1" value={form.provider}
                  onChange={e => setForm({ ...form, provider: e.target.value, model_id: '' })}>
                  {PROVIDERS.map(p => <option key={p.value} value={p.value}>{p.label}</option>)}
                </select>
              </div>
              <div>
                <label className="text-xs text-gray-500">模型</label>
                <select className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm mt-1" value={form.model_id}
                  onChange={e => setForm({ ...form, model_id: e.target.value })}>
                  <option value="">选择模型...</option>
                  {providerModels.map(m => <option key={m} value={m}>{m}</option>)}
                  <option value="custom">自定义...</option>
                </select>
              </div>
              <div className="col-span-2">
                <label className="text-xs text-gray-500">API Key</label>
                <input type="password" className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm mt-1 font-mono"
                  placeholder="sk-..." value={form.api_key} onChange={e => setForm({ ...form, api_key: e.target.value })} />
              </div>
              <div>
                <label className="text-xs text-gray-500">Temperature ({form.temperature})</label>
                <input type="range" min="0" max="2" step="0.1" className="w-full mt-1"
                  value={form.temperature} onChange={e => setForm({ ...form, temperature: parseFloat(e.target.value) })} />
              </div>
              <div>
                <label className="text-xs text-gray-500">Max Tokens</label>
                <input type="number" className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm mt-1"
                  value={form.max_tokens} onChange={e => setForm({ ...form, max_tokens: parseInt(e.target.value) || 4096 })} />
              </div>
            </div>
            <div className="flex gap-2 mt-4 justify-end">
              {editing && <button onClick={() => { setEditing(null); resetForm(); }} className="px-4 py-1.5 border border-gray-700 rounded-lg text-sm hover:bg-gray-800">取消</button>}
              <button onClick={saveAsPreset} className="flex items-center gap-1 px-3 py-1.5 border border-gray-600 rounded-lg text-sm hover:bg-gray-800">
                <Save size={14} /> 存为预设
              </button>
              <button onClick={saveModel} className="flex items-center gap-1 px-4 py-1.5 bg-blue-600 rounded-lg text-sm font-medium hover:bg-blue-700">
                <Check size={14} /> {editing ? '更新' : '添加'}
              </button>
            </div>
          </div>

          {/* Model presets */}
          {presets.length > 0 && (
            <div className="mb-6">
              <h2 className="font-bold text-sm text-gray-400 uppercase tracking-wider mb-3">模型预设</h2>
              <div className="space-y-2">
                {presets.map(p => (
                  <div key={p.id} className="bg-gray-900 border border-gray-800 rounded-lg p-3 flex items-center justify-between group">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-sm">{p.name}</span>
                        <span className="text-xs text-gray-600">{ROLES.find(r => r.value === p.role)?.label}</span>
                      </div>
                      <div className="text-xs text-gray-500 mt-0.5">{p.provider} — {p.model_id || '(未选模型)'}</div>
                    </div>
                    <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                      <button onClick={() => loadFromPreset(p)} className="flex items-center gap-1 px-2 py-1 text-xs bg-green-700 rounded hover:bg-green-600">
                        <Copy size={12} /> 加载
                      </button>
                      <button onClick={() => deleteModel(p.id)} className="p-1 hover:bg-red-900/50 rounded text-red-400"><Trash2 size={14} /></button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Active models */}
          <div className="space-y-3">
            <h2 className="font-bold text-sm text-gray-400 uppercase tracking-wider">已配置的模型</h2>
            {models.map(m => (
              <div key={m.id} className="bg-gray-900 border border-gray-800 rounded-lg p-4 flex items-center justify-between group">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-medium">{m.name}</span>
                    {m.is_active && <span className="text-xs bg-green-900/50 text-green-400 px-1.5 py-0.5 rounded">活跃</span>}
                    <span className="text-xs text-gray-600">{ROLES.find(r => r.value === m.role)?.label}</span>
                  </div>
                  <div className="text-xs text-gray-500 mt-0.5">{m.provider} — {m.model_id}</div>
                </div>
                <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button onClick={() => editModel(m)} className="p-1.5 hover:bg-gray-800 rounded text-gray-400">✏️</button>
                  <button onClick={() => deleteModel(m.id)} className="p-1.5 hover:bg-red-900/50 rounded text-red-400"><Trash2 size={14} /></button>
                </div>
              </div>
            ))}
            {models.length === 0 && (
              <p className="text-gray-600 text-sm p-4 text-center border border-dashed border-gray-800 rounded-lg">
                还没有配置任何模型
              </p>
            )}
          </div>
        </>
      )}

      {tab === 'prompts' && (
        <>
          {/* New preset form */}
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 mb-6">
            <h2 className="font-bold mb-4">添加自定义提示词预设</h2>
            <div className="flex gap-3">
              <div className="flex-1">
                <label className="text-xs text-gray-500">名称</label>
                <input className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm mt-1"
                  placeholder="我的自定义提示词" value={promptForm.name}
                  onChange={e => setPromptForm({ ...promptForm, name: e.target.value })} />
              </div>
              <div className="flex-1">
                <label className="text-xs text-gray-500">类型</label>
                <select className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm mt-1"
                  value={promptForm.role} onChange={e => setPromptForm({ ...promptForm, role: e.target.value })}>
                  {PROMPT_ROLES.map(r => <option key={r.value} value={r.value}>{r.label}</option>)}
                </select>
              </div>
            </div>
            <div className="flex gap-2 mt-4 justify-end">
              <button onClick={savePrompt} className="flex items-center gap-1 px-4 py-1.5 bg-blue-600 rounded-lg text-sm font-medium hover:bg-blue-700">
                <Check size={14} /> 添加预设
              </button>
            </div>
          </div>

          {/* Prompt presets with fragments */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="font-bold text-sm text-gray-400 uppercase tracking-wider">提示词预设</h2>
              <div className="flex gap-1">
                <select value={promptExportFormat} onChange={e => setPromptExportFormat(e.target.value as any)}
                  className="bg-gray-800 border border-gray-700 rounded px-1 py-1 text-xs w-16">
                  <option value="bookwright">BW</option>
                  <option value="sillytavern">ST</option>
                </select>
                <button onClick={handlePromptExport}
                  className="flex items-center gap-1 px-2 py-1 text-xs bg-gray-800 border border-gray-700 rounded hover:bg-gray-700">
                  <Download size={12} /> 导出
                </button>
                <button onClick={() => promptImportRef.current?.click()}
                  className="flex items-center gap-1 px-2 py-1 text-xs bg-gray-800 border border-gray-700 rounded hover:bg-gray-700">
                  <Upload size={12} /> 导入
                </button>
              </div>
            </div>
            {promptPresets.map(p => {
              const isExpanded = expandedPreset === p.id;
              return (
                <div key={p.id} className="bg-gray-900 border border-gray-800 rounded-lg overflow-hidden">
                  {/* Preset header */}
                  <div
                    className="p-4 flex items-center justify-between cursor-pointer hover:bg-gray-850 group"
                    onClick={() => setExpandedPreset(isExpanded ? null : p.id)}
                  >
                    <div className="flex items-center gap-2">
                      {isExpanded ? <ChevronDown size={14} className="text-gray-500" /> : <ChevronUp size={14} className="text-gray-600" />}
                      <span className="font-medium">{p.name}</span>
                      {p.is_default && <span className="text-xs bg-blue-900/50 text-blue-400 px-1.5 py-0.5 rounded">内置</span>}
                      <span className="text-xs text-gray-600">{PROMPT_ROLES.find(r => r.value === p.role)?.label}</span>
                      <span className="text-xs text-gray-700">({p.fragments?.length || 0} 条)</span>
                    </div>
                    {!p.is_default && (
                      <button onClick={(e) => { e.stopPropagation(); deletePrompt(p.id); }}
                        className="opacity-0 group-hover:opacity-100 p-1 hover:bg-red-900/50 rounded text-red-400">
                        <Trash2 size={14} />
                      </button>
                    )}
                  </div>

                  {/* Expanded fragments editor */}
                  {isExpanded && (
                    <div className="border-t border-gray-800 px-4 py-3 space-y-3">
                      {/* Assembled preview */}
                      <details className="text-xs">
                        <summary className="text-gray-500 cursor-pointer mb-1">组装后的完整提示词预览</summary>
                        <pre className="bg-gray-950 p-3 rounded text-gray-400 whitespace-pre-wrap max-h-48 overflow-y-auto mt-1">{p.content}</pre>
                      </details>

                      {/* Fragment list */}
                      <div className="space-y-1.5">
                        {(p.fragments || []).sort((a, b) => a.sort_order - b.sort_order).map((frag, idx) => (
                          <div key={frag.id} className={`flex items-start gap-2 p-2 rounded ${!frag.is_active ? 'opacity-40' : ''} ${editingFrag === frag.id ? 'bg-gray-800' : 'bg-gray-950'}`}>
                            <div className="flex flex-col items-center gap-0.5 mt-0.5">
                              <button
                                onClick={async () => {
                                  const frags = [...(p.fragments || [])].sort((a, b) => a.sort_order - b.sort_order);
                                  if (idx === 0) return;
                                  [frags[idx - 1], frags[idx]] = [frags[idx], frags[idx - 1]];
                                  const order = frags.map(f => f.id);
                                  await api.reorderFragments(p.id, order);
                                  refreshPrompts();
                                }}
                                disabled={idx === 0}
                                className="text-gray-600 hover:text-gray-300 disabled:opacity-30"
                              ><ChevronUp size={12} /></button>
                              <GripVertical size={12} className="text-gray-700" />
                              <button
                                onClick={async () => {
                                  const frags = [...(p.fragments || [])].sort((a, b) => a.sort_order - b.sort_order);
                                  if (idx >= frags.length - 1) return;
                                  [frags[idx], frags[idx + 1]] = [frags[idx + 1], frags[idx]];
                                  const order = frags.map(f => f.id);
                                  await api.reorderFragments(p.id, order);
                                  refreshPrompts();
                                }}
                                disabled={idx >= (p.fragments || []).length - 1}
                                className="text-gray-600 hover:text-gray-300 disabled:opacity-30"
                              ><ChevronDown size={12} /></button>
                            </div>

                            <button
                              onClick={async () => {
                                await api.updateFragment(p.id, frag.id, { is_active: !frag.is_active });
                                refreshPrompts();
                              }}
                              className="mt-0.5 text-gray-500 hover:text-gray-300"
                              title={frag.is_active ? '禁用此条目' : '启用此条目'}
                            >
                              {frag.is_active ? <Eye size={14} /> : <EyeOff size={14} />}
                            </button>

                            {editingFrag === frag.id ? (
                              <div className="flex-1 flex gap-2">
                                <input
                                  className="flex-1 bg-gray-700 border border-gray-600 rounded px-2 py-1 text-xs"
                                  value={fragContent}
                                  onChange={e => setFragContent(e.target.value)}
                                  autoFocus
                                  onKeyDown={async (e) => {
                                    if (e.key === 'Enter') {
                                      await api.updateFragment(p.id, frag.id, { content: fragContent });
                                      setEditingFrag(null);
                                      refreshPrompts();
                                    }
                                    if (e.key === 'Escape') { setEditingFrag(null); }
                                  }}
                                />
                                <button onClick={async () => { await api.updateFragment(p.id, frag.id, { content: fragContent }); setEditingFrag(null); refreshPrompts(); }}
                                  className="text-xs px-2 py-1 bg-green-700 rounded hover:bg-green-600">保存</button>
                              </div>
                            ) : (
                              <span
                                className="flex-1 text-xs text-gray-400 cursor-pointer hover:text-gray-200"
                                onClick={() => { setEditingFrag(frag.id); setFragContent(frag.content); }}
                                title="点击编辑"
                              >{frag.content.slice(0, 120)}{frag.content.length > 120 ? '...' : ''}</span>
                            )}

                            {!p.is_default && (
                              <button
                                onClick={async () => { await api.deleteFragment(p.id, frag.id); refreshPrompts(); }}
                                className="text-gray-700 hover:text-red-400"
                              ><Trash2 size={12} /></button>
                            )}
                          </div>
                        ))}
                      </div>

                      {/* Add fragment */}
                      <div className="flex gap-2">
                        <input
                          className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-xs"
                          placeholder="添加新的提示词条目..."
                          value={newFragContent}
                          onChange={e => setNewFragContent(e.target.value)}
                          onKeyDown={async (e) => {
                            if (e.key === 'Enter' && newFragContent.trim()) {
                              await api.createFragment(p.id, { content: newFragContent.trim() });
                              setNewFragContent('');
                              refreshPrompts();
                            }
                          }}
                        />
                        <button
                          onClick={async () => {
                            if (!newFragContent.trim()) return;
                            await api.createFragment(p.id, { content: newFragContent.trim() });
                            setNewFragContent('');
                            refreshPrompts();
                          }}
                          className="flex items-center gap-1 px-3 py-1.5 bg-blue-600 rounded-lg text-xs font-medium hover:bg-blue-700"
                        ><Plus size={12} /> 添加</button>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
            {promptPresets.length === 0 && (
              <p className="text-gray-600 text-sm p-4 text-center border border-dashed border-gray-800 rounded-lg">暂无提示词预设</p>
            )}
          </div>
        </>
      )}
    </div>
  );
}

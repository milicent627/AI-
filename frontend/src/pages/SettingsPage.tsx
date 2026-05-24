import { useEffect, useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import type { ModelConfig, PromptPreset } from '../types';
import { ArrowLeft, Plus, Trash2, Check, Save, Copy, ChevronDown, ChevronUp, ChevronRight, GripVertical, EyeOff, Eye, Download, Upload, RefreshCw } from 'lucide-react';

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

  // Model bundle state
  const [bundles, setBundles] = useState<any[]>([]);
  const [editingName, setEditingName] = useState<string | null>(null);
  const [bundleForm, setBundleForm] = useState({ name: '', api_key: '', base_url: '' });
  const [formRoles, setFormRoles] = useState<Record<string, { model_id: string; temperature: number; max_tokens: number }>>(
    Object.fromEntries(ROLES.map(r => [r.value, { model_id: '', temperature: 0.8, max_tokens: 4096 }]))
  );
  const [fetchedModels, setFetchedModels] = useState<string[] | null>(null);
  const [fetchingModels, setFetchingModels] = useState(false);
  const [expandedBundle, setExpandedBundle] = useState<string | null>(null);

  // Prompt preset state
  const [promptPresets, setPromptPresets] = useState<PromptPreset[]>([]);
  const [editingPrompt, setEditingPrompt] = useState<PromptPreset | null>(null);
  const [promptForm, setPromptForm] = useState({ name: '', role: 'continuation_system', content: '' });
  const [expandedPreset, setExpandedPreset] = useState<string | null>(null);
  const [editingFrag, setEditingFrag] = useState<string | null>(null);
  const [fragContent, setFragContent] = useState('');
  const [newFragContent, setNewFragContent] = useState('');
  const [editingPresetName, setEditingPresetName] = useState<string | null>(null);
  const [editPresetNameVal, setEditPresetNameVal] = useState('');

  useEffect(() => {
    refreshBundles();
    api.listPromptPresets().then(d => setPromptPresets(d.presets || [])).catch(console.error);
  }, []);

  // --- Bundle handlers ---
  const refreshBundles = async () => {
    try {
      const d = await api.listBundles();
      setBundles(d.bundles || []);
    } catch (e) {
      // fallback: load individual models and group manually
      const d = await api.listModels();
      const nonPresets = (d.models || []).filter((m: any) => !m.is_preset);
      const map: Record<string, any> = {};
      for (const m of nonPresets) {
        if (!map[m.name]) map[m.name] = { name: m.name, api_key: m.api_key, base_url: m.base_url || '', roles: {} };
        if (m.api_key && !map[m.name].api_key) map[m.name].api_key = m.api_key;
        if (m.base_url && !map[m.name].base_url) map[m.name].base_url = m.base_url;
        map[m.name].roles[m.role] = { id: m.id, model_id: m.model_id, temperature: m.temperature, max_tokens: m.max_tokens, is_active: m.is_active };
      }
      setBundles(Object.values(map));
    }
  };

  const resetBundleForm = () => {
    setBundleForm({ name: '', api_key: '', base_url: '' });
    setFormRoles(Object.fromEntries(ROLES.map(r => [r.value, { model_id: '', temperature: 0.8, max_tokens: 4096 }])));
    setEditingName(null);
    setFetchedModels(null);
  };

  const editBundle = (bundle: any) => {
    setEditingName(bundle.name);
    setBundleForm({ name: bundle.name, api_key: bundle.api_key || '', base_url: bundle.base_url || '' });
    const roles: Record<string, any> = {};
    for (const r of ROLES) {
      const rc = bundle.roles[r.value];
      roles[r.value] = rc ? { model_id: rc.model_id, temperature: rc.temperature, max_tokens: rc.max_tokens } : { model_id: '', temperature: 0.8, max_tokens: 4096 };
    }
    setFormRoles(roles);
  };

  const saveBundle = async () => {
    if (!bundleForm.name) { alert('请填写名称'); return; }
    await api.saveBundle({ ...bundleForm, roles: formRoles });
    await refreshBundles();
    resetBundleForm();
  };

  const deleteBundle = async (name: string) => {
    if (!confirm(`确定删除模型组 "${name}" 吗？这将删除所有6个模型配置。`)) return;
    await api.deleteBundle(name);
    await refreshBundles();
  };

  const handleFetchModels = async () => {
    if (!bundleForm.api_key || !bundleForm.base_url) { alert('请先填写 API Key 和 API URL'); return; }
    setFetchingModels(true);
    setFetchedModels(null);
    try {
      const result = await api.listProviderModels('custom', bundleForm.api_key, bundleForm.base_url);
      setFetchedModels(result.models);
    } catch (err: any) {
      alert(`获取模型列表失败: ${err.message}`);
    } finally {
      setFetchingModels(false);
    }
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
          {/* Bundle form */}
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 mb-6">
            <h2 className="font-bold mb-4">{editingName ? `编辑: ${editingName}` : '添加模型组'}</h2>
            <p className="text-xs text-gray-500 mb-4">一个模型组包含全部 6 个用途的配置。填入 API 连接信息后为每个用途指定模型和参数。</p>

            {/* Shared credentials */}
            <div className="grid grid-cols-3 gap-3 mb-4">
              <div>
                <label className="text-xs text-gray-500">名称</label>
                <input className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm mt-1"
                  placeholder="例如：GPT-4o" value={bundleForm.name}
                  onChange={e => setBundleForm({ ...bundleForm, name: e.target.value })} />
              </div>
              <div>
                <label className="text-xs text-gray-500">API Key</label>
                <input type="password" className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm mt-1 font-mono"
                  placeholder="sk-..." value={bundleForm.api_key}
                  onChange={e => setBundleForm({ ...bundleForm, api_key: e.target.value })} />
              </div>
              <div>
                <label className="text-xs text-gray-500">API URL</label>
                <input type="text" className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm mt-1 font-mono"
                  placeholder="https://api.openai.com" value={bundleForm.base_url}
                  onChange={e => setBundleForm({ ...bundleForm, base_url: e.target.value })} />
              </div>
            </div>

            {/* Fetch models button */}
            <div className="flex items-center gap-2 mb-4">
              <button onClick={handleFetchModels}
                disabled={fetchingModels || !bundleForm.api_key || !bundleForm.base_url}
                className="flex items-center gap-1 px-3 py-1 text-xs bg-gray-700 border border-gray-600 rounded-lg hover:bg-gray-600 disabled:opacity-40 disabled:cursor-not-allowed">
                <RefreshCw size={12} className={fetchingModels ? 'animate-spin' : ''} />
                获取模型列表
              </button>
              {fetchedModels && <span className="text-xs text-gray-500">{fetchedModels.length} 个可用模型</span>}
            </div>

            {/* Per-role configs */}
            <div className="space-y-2">
              {ROLES.map(r => {
                const role = formRoles[r.value] || { model_id: '', temperature: 0.8, max_tokens: 4096 };
                return (
                  <div key={r.value} className="flex items-center gap-2 bg-gray-950 rounded-lg px-3 py-2">
                    <span className="text-xs text-gray-400 w-28 shrink-0">{r.label}</span>
                    {fetchedModels ? (
                      <select className="flex-1 bg-gray-800 border border-gray-700 rounded px-2 py-1 text-xs"
                        value={role.model_id}
                        onChange={e => {
                          const v = e.target.value;
                          setFormRoles(prev => ({ ...prev, [r.value]: { ...prev[r.value], model_id: v === '__custom__' ? '' : v } }));
                        }}>
                        <option value="">默认</option>
                        {fetchedModels.map(m => <option key={m} value={m}>{m}</option>)}
                        <option value="__custom__">自定义...</option>
                      </select>
                    ) : (
                      <input type="text" className="flex-1 bg-gray-800 border border-gray-700 rounded px-2 py-1 text-xs font-mono"
                        placeholder="模型 ID，如 gpt-4o"
                        value={role.model_id}
                        onChange={e => setFormRoles(prev => ({ ...prev, [r.value]: { ...prev[r.value], model_id: e.target.value } }))} />
                    )}
                    <div className="flex items-center gap-1 shrink-0">
                      <span className="text-xs text-gray-600">T</span>
                      <input type="number" className="w-12 bg-gray-800 border border-gray-700 rounded px-1 py-0.5 text-xs text-center"
                        value={role.temperature} step="0.1" min="0" max="2"
                        onChange={e => setFormRoles(prev => ({ ...prev, [r.value]: { ...prev[r.value], temperature: parseFloat(e.target.value) || 0.8 } }))} />
                    </div>
                    <div className="flex items-center gap-1 shrink-0">
                      <span className="text-xs text-gray-600">MT</span>
                      <input type="number" className="w-16 bg-gray-800 border border-gray-700 rounded px-1 py-0.5 text-xs text-center"
                        value={role.max_tokens} step="100"
                        onChange={e => setFormRoles(prev => ({ ...prev, [r.value]: { ...prev[r.value], max_tokens: parseInt(e.target.value) || 4096 } }))} />
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="flex gap-2 mt-4 justify-end">
              {editingName && <button onClick={resetBundleForm} className="px-4 py-1.5 border border-gray-700 rounded-lg text-sm hover:bg-gray-800">取消</button>}
              <button onClick={saveBundle} className="flex items-center gap-1 px-4 py-1.5 bg-blue-600 rounded-lg text-sm font-medium hover:bg-blue-700">
                <Check size={14} /> {editingName ? '更新' : '保存模型组'}
              </button>
            </div>
          </div>

          {/* Bundle list */}
          <div className="space-y-3">
            <h2 className="font-bold text-sm text-gray-400 uppercase tracking-wider">已配置的模型组</h2>
            {bundles.map((b: any) => {
              const isExpanded = expandedBundle === b.name;
              const roleCount = Object.keys(b.roles || {}).length;
              return (
                <div key={b.name} className="bg-gray-900 border border-gray-800 rounded-lg overflow-hidden">
                  <div className="p-3 flex items-center justify-between cursor-pointer hover:bg-gray-850 group"
                    onClick={() => setExpandedBundle(isExpanded ? null : b.name)}>
                    <div className="flex items-center gap-2">
                      {isExpanded ? <ChevronDown size={14} className="text-gray-500" /> : <ChevronRight size={14} className="text-gray-600" />}
                      <span className="font-medium">{b.name}</span>
                      <span className="text-xs text-gray-600">{roleCount}/6 个用途已配置</span>
                    </div>
                    <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity" onClick={e => e.stopPropagation()}>
                      <button onClick={() => editBundle(b)} className="p-1 hover:bg-gray-800 rounded text-gray-400">✏️</button>
                      <button onClick={() => deleteBundle(b.name)} className="p-1 hover:bg-red-900/50 rounded text-red-400"><Trash2 size={14} /></button>
                    </div>
                  </div>
                  {isExpanded && (
                    <div className="border-t border-gray-800 px-4 py-2 space-y-1">
                      <div className="text-xs text-gray-600 mb-1">
                        {b.base_url && <span>API: {b.base_url}</span>}
                      </div>
                      {ROLES.map(r => {
                        const rc = b.roles[r.value];
                        return (
                          <div key={r.value} className="flex items-center gap-2 text-xs">
                            <span className="text-gray-400 w-28">{r.label}</span>
                            {rc ? (
                              <>
                                <span className="text-gray-300 font-mono">{rc.model_id || '(默认)'}</span>
                                <span className="text-gray-600">T: {rc.temperature}</span>
                                <span className="text-gray-600">MT: {rc.max_tokens}</span>
                              </>
                            ) : (
                              <span className="text-gray-700">未配置</span>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              );
            })}
            {bundles.length === 0 && (
              <p className="text-gray-600 text-sm p-4 text-center border border-dashed border-gray-800 rounded-lg">
                还没有配置任何模型组 — 请在上方添加
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
                      {editingPresetName === p.id ? (
                        <input
                          className="bg-gray-700 border border-gray-600 rounded px-2 py-0.5 text-xs font-medium w-40"
                          value={editPresetNameVal}
                          onChange={e => setEditPresetNameVal(e.target.value)}
                          autoFocus
                          onKeyDown={async (e) => {
                            if (e.key === 'Enter') { await api.updatePromptPreset(p.id, { name: editPresetNameVal }); setEditingPresetName(null); refreshPrompts(); }
                            if (e.key === 'Escape') { setEditingPresetName(null); }
                          }}
                          onBlur={async () => {
                            if (editPresetNameVal !== p.name && editPresetNameVal.trim()) {
                              await api.updatePromptPreset(p.id, { name: editPresetNameVal.trim() });
                              refreshPrompts();
                            }
                            setEditingPresetName(null);
                          }}
                          onClick={e => e.stopPropagation()}
                        />
                      ) : (
                        <span className="font-medium cursor-pointer hover:text-blue-400" onClick={(e) => {
                          e.stopPropagation();
                          if (!p.is_default) { setEditingPresetName(p.id); setEditPresetNameVal(p.name); }
                        }} title={p.is_default ? '内置预设不可重命名' : '点击重命名'}>{p.name}</span>
                      )}
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

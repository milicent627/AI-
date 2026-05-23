import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import type { ModelConfig } from '../types';
import { ArrowLeft, Plus, Trash2, Check } from 'lucide-react';

const PROVIDERS = [
  { value: 'openai', label: 'OpenAI', models: ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo', 'gpt-3.5-turbo'] },
  { value: 'anthropic', label: 'Anthropic', models: ['claude-sonnet-4-20250514', 'claude-3-5-sonnet-20241022', 'claude-3-5-haiku-20241022', 'claude-3-opus-20240229'] },
  { value: 'deepseek', label: 'DeepSeek', models: ['deepseek-chat', 'deepseek-reasoner'] },
];

const ROLES = [
  { value: 'continuation', label: '续写模型' },
  { value: 'polishing', label: '润色模型' },
  { value: 'analysis', label: '分析模型' },
];

export default function SettingsPage() {
  const navigate = useNavigate();
  const [models, setModels] = useState<ModelConfig[]>([]);
  const [editing, setEditing] = useState<ModelConfig | null>(null);
  const [form, setForm] = useState({
    name: '', provider: 'openai', model_id: '', api_key: '', base_url: '',
    role: 'continuation', temperature: 0.8, max_tokens: 4096, is_active: true,
  });

  useEffect(() => {
    api.listModels().then(d => setModels(d.models || [])).catch(console.error);
  }, []);

  const saveModel = async () => {
    if (!form.name || !form.api_key) {
      alert('请填写模型名称和 API Key');
      return;
    }
    if (editing) {
      await api.updateModel(editing.id, form);
    } else {
      await api.createModel(form);
    }
    const d = await api.listModels();
    setModels(d.models || []);
    setEditing(null);
    resetForm();
  };

  const editModel = (m: ModelConfig) => {
    setEditing(m);
    setForm({ name: m.name, provider: m.provider, model_id: m.model_id, api_key: m.api_key, base_url: '', role: m.role, temperature: m.temperature, max_tokens: m.max_tokens, is_active: m.is_active });
  };

  const deleteModel = async (id: string) => {
    if (!confirm('确定删除此模型配置？')) return;
    await api.deleteModel(id);
    setModels(models.filter(m => m.id !== id));
  };

  const resetForm = () => {
    setForm({ name: '', provider: 'openai', model_id: '', api_key: '', base_url: '', role: 'continuation', temperature: 0.8, max_tokens: 4096, is_active: true });
  };

  const providerModels = PROVIDERS.find(p => p.value === form.provider)?.models || [];

  return (
    <div className="flex-1 flex flex-col max-w-3xl mx-auto w-full p-6">
      <div className="flex items-center gap-3 mb-6">
        <button onClick={() => navigate(-1)} className="p-1 hover:bg-gray-800 rounded"><ArrowLeft size={18} /></button>
        <h1 className="text-xl font-bold">模型设置</h1>
      </div>

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
          <button onClick={saveModel} className="flex items-center gap-1 px-4 py-1.5 bg-blue-600 rounded-lg text-sm font-medium hover:bg-blue-700">
            <Check size={14} /> {editing ? '更新' : '添加'}
          </button>
        </div>
      </div>

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
            还没有配置任何模型，请先添加一个续写模型
          </p>
        )}
      </div>
    </div>
  );
}

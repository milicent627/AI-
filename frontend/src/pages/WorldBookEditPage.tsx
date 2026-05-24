import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Trash2 } from 'lucide-react';
import { api } from '../api/client';
import type { WorldBookEntry } from '../types';

const CATEGORY_OPTIONS: { value: string; label: string }[] = [
  { value: 'character', label: '角色' },
  { value: 'faction', label: '势力' },
  { value: 'location', label: '地点' },
  { value: 'item', label: '物品' },
  { value: 'power_system', label: '力量体系' },
  { value: 'catchphrase', label: '口头禅' },
  { value: 'custom', label: '自定义' },
];

const STATUS_OPTIONS: { value: string; label: string }[] = [
  { value: 'active', label: '活跃' },
  { value: 'inactive', label: '不活跃' },
  { value: 'dead', label: '已死亡' },
  { value: 'missing', label: '失踪' },
];

interface EntryForm {
  name: string;
  category: string;
  description: string;
  aliases: string;
  importance: number;
  sort_order: number;
  status: string;
  gender: string;
  age: string;
  appearance: string;
  identity: string;
  personality: string;
  abilities: string;
  catchphrases: string;
}

const emptyForm: EntryForm = {
  name: '',
  category: 'character',
  description: '',
  aliases: '',
  importance: 3,
  sort_order: 0,
  status: 'active',
  gender: '',
  age: '',
  appearance: '',
  identity: '',
  personality: '',
  abilities: '',
  catchphrases: '',
};

export default function WorldBookEditPage() {
  const { storyId, entryId } = useParams<{ storyId: string; entryId: string }>();
  const navigate = useNavigate();
  const isNew = !entryId || entryId === 'new';

  const [form, setForm] = useState<EntryForm>(emptyForm);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!isNew && storyId && entryId) {
      api.getWorldEntry(storyId, entryId).then((entry: WorldBookEntry) => {
        const attrs = entry.attributes || {};
        setForm({
          name: entry.name || '',
          category: entry.category || 'character',
          description: entry.description || '',
          aliases: (entry.aliases || []).join(', '),
          importance: entry.importance || 3,
          sort_order: entry.sort_order || 0,
          status: entry.status || 'active',
          gender: attrs.gender || '',
          age: attrs.age || '',
          appearance: attrs.appearance || '',
          identity: attrs.identity || '',
          personality: (attrs.personality || []).join(', '),
          abilities: (attrs.abilities || []).join(', '),
          catchphrases: (attrs.catchphrases || []).join(', '),
        });
      }).catch(() => navigate(-1));
    }
  }, [storyId, entryId]);

  const handleSave = async () => {
    if (!storyId || !form.name.trim()) return;
    setSaving(true);

    const data: Record<string, unknown> = {
      name: form.name.trim(),
      category: form.category,
      description: form.description.trim(),
      aliases: form.aliases.split(',').map((s) => s.trim()).filter(Boolean),
      importance: form.importance,
      sort_order: form.sort_order,
      status: form.status,
    };

    if (form.category === 'character') {
      data.attributes = {
        gender: form.gender,
        age: form.age,
        appearance: form.appearance,
        identity: form.identity,
        personality: form.personality.split(',').map((s) => s.trim()).filter(Boolean),
        abilities: form.abilities.split(',').map((s) => s.trim()).filter(Boolean),
        catchphrases: form.catchphrases.split(',').map((s) => s.trim()).filter(Boolean),
      };
    }

    try {
      if (isNew) {
        await api.createWorldEntry(storyId, data);
      } else {
        await api.updateWorldEntry(storyId, entryId!, data);
      }
      navigate(-1);
    } catch (err: unknown) {
      alert(`保存失败: ${err instanceof Error ? err.message : '未知错误'}`);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!storyId || !entryId || !confirm('确定删除此条目？此操作不可撤消。')) return;
    try {
      await api.deleteWorldEntry(storyId, entryId);
      navigate(`/editor/${storyId}`);
    } catch (err: unknown) {
      alert(`删除失败: ${err instanceof Error ? err.message : '未知错误'}`);
    }
  };

  const update = (key: keyof EntryForm) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    setForm({ ...form, [key]: e.target.value });
  };

  return (
    <div className="h-screen flex flex-col bg-white">
      <header className="border-b border-gray-200 px-6 py-3 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <button onClick={() => navigate(-1)} className="p-1 hover:bg-gray-100 rounded text-gray-500">
            <ArrowLeft size={18} />
          </button>
          <h1 className="text-lg font-semibold text-gray-800">
            {isNew ? '创建新条目' : '编辑条目'}
          </h1>
        </div>
        <div className="flex items-center gap-2">
          {!isNew && (
            <button
              onClick={handleDelete}
              className="flex items-center gap-1 px-3 py-1.5 text-sm border border-red-200 text-red-600 rounded-lg hover:bg-red-50"
            >
              <Trash2 size={14} /> 删除
            </button>
          )}
          <button
            onClick={handleSave}
            disabled={saving || !form.name.trim()}
            className="px-4 py-1.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 text-sm font-medium"
          >
            {saving ? '保存中...' : '保存'}
          </button>
        </div>
      </header>

      <main className="flex-1 overflow-y-auto">
        <div className="max-w-2xl mx-auto p-6 space-y-6">
          {/* Basic info */}
          <section className="space-y-4">
            <div className="grid grid-cols-3 gap-4">
              <div className="col-span-2">
                <label className="block text-xs font-medium text-gray-500 mb-1">名称</label>
                <input
                  value={form.name}
                  onChange={update('name')}
                  className="w-full bg-white border border-gray-200 rounded-lg px-3 py-2 text-sm outline-none focus:border-blue-500 text-gray-800"
                  placeholder="条目名称"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1">重要性</label>
                <select
                  value={form.importance}
                  onChange={(e) => setForm({ ...form, importance: Number(e.target.value) })}
                  className="w-full bg-white border border-gray-200 rounded-lg px-3 py-2 text-sm outline-none focus:border-blue-500 text-gray-800"
                >
                  {[1, 2, 3, 4, 5].map((n) => (
                    <option key={n} value={n}>{'★'.repeat(n)}</option>
                  ))}
                </select>
              </div>
            </div>

            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1">分类</label>
                <select
                  value={form.category}
                  onChange={update('category')}
                  className="w-full bg-white border border-gray-200 rounded-lg px-3 py-2 text-sm outline-none focus:border-blue-500 text-gray-800"
                >
                  {CATEGORY_OPTIONS.map((c) => (
                    <option key={c.value} value={c.value}>{c.label}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1">状态</label>
                <select
                  value={form.status}
                  onChange={update('status')}
                  className="w-full bg-white border border-gray-200 rounded-lg px-3 py-2 text-sm outline-none focus:border-blue-500 text-gray-800"
                >
                  {STATUS_OPTIONS.map((s) => (
                    <option key={s.value} value={s.value}>{s.label}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1">排序</label>
                <input
                  type="number"
                  value={form.sort_order}
                  onChange={(e) => setForm({ ...form, sort_order: Number(e.target.value) })}
                  className="w-full bg-white border border-gray-200 rounded-lg px-3 py-2 text-sm outline-none focus:border-blue-500 text-gray-800"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">描述</label>
              <textarea
                value={form.description}
                onChange={update('description')}
                className="w-full bg-white border border-gray-200 rounded-lg px-3 py-2 text-sm h-32 resize-none outline-none focus:border-blue-500 text-gray-800"
                placeholder="详细描述..."
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">别名（逗号分隔）</label>
              <input
                value={form.aliases}
                onChange={update('aliases')}
                className="w-full bg-white border border-gray-200 rounded-lg px-3 py-2 text-sm outline-none focus:border-blue-500 text-gray-800"
                placeholder="别名1, 别名2"
              />
            </div>
          </section>

          {/* Character-specific fields */}
          {form.category === 'character' && (
            <section className="space-y-4 pt-6 border-t border-gray-100">
              <h2 className="text-sm font-semibold text-gray-600">角色属性</h2>

              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className="block text-xs font-medium text-gray-500 mb-1">性别</label>
                  <select
                    value={form.gender}
                    onChange={update('gender')}
                    className="w-full bg-white border border-gray-200 rounded-lg px-3 py-2 text-sm outline-none focus:border-blue-500 text-gray-800"
                  >
                    <option value="">未知</option>
                    <option value="男">男</option>
                    <option value="女">女</option>
                    <option value="其他">其他</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-500 mb-1">年龄</label>
                  <input
                    value={form.age}
                    onChange={update('age')}
                    className="w-full bg-white border border-gray-200 rounded-lg px-3 py-2 text-sm outline-none focus:border-blue-500 text-gray-800"
                    placeholder="年龄"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-500 mb-1">身份/职业</label>
                  <input
                    value={form.identity}
                    onChange={update('identity')}
                    className="w-full bg-white border border-gray-200 rounded-lg px-3 py-2 text-sm outline-none focus:border-blue-500 text-gray-800"
                    placeholder="身份"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1">外貌描述</label>
                <textarea
                  value={form.appearance}
                  onChange={update('appearance')}
                  className="w-full bg-white border border-gray-200 rounded-lg px-3 py-2 text-sm h-20 resize-none outline-none focus:border-blue-500 text-gray-800"
                  placeholder="外貌特征..."
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1">性格标签（逗号分隔）</label>
                <input
                  value={form.personality}
                  onChange={update('personality')}
                  className="w-full bg-white border border-gray-200 rounded-lg px-3 py-2 text-sm outline-none focus:border-blue-500 text-gray-800"
                  placeholder="勇敢, 善良, 冷酷"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1">能力/技能（逗号分隔）</label>
                <input
                  value={form.abilities}
                  onChange={update('abilities')}
                  className="w-full bg-white border border-gray-200 rounded-lg px-3 py-2 text-sm outline-none focus:border-blue-500 text-gray-800"
                  placeholder="剑术精通, 火焰魔法"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1">口头禅（逗号分隔）</label>
                <input
                  value={form.catchphrases}
                  onChange={update('catchphrases')}
                  className="w-full bg-white border border-gray-200 rounded-lg px-3 py-2 text-sm outline-none focus:border-blue-500 text-gray-800"
                  placeholder='"那就这样吧"'
                />
              </div>
            </section>
          )}
        </div>
      </main>
    </div>
  );
}

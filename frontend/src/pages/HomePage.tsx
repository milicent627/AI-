import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import { useStoryStore } from '../stores/storyStore';
import { Plus, BookOpen, Settings, Trash2 } from 'lucide-react';

export default function HomePage() {
  const navigate = useNavigate();
  const { stories, setStories } = useStoryStore();
  const [showCreate, setShowCreate] = useState(false);
  const [title, setTitle] = useState('');
  const [genre, setGenre] = useState('');
  const [synopsis, setSynopsis] = useState('');

  useEffect(() => {
    api.listStories().then(data => setStories(data.stories || [])).catch(console.error);
  }, []);

  const createStory = async () => {
    if (!title.trim()) return;
    const data = await api.createStory({ title, genre, synopsis });
    setShowCreate(false);
    setTitle(''); setGenre(''); setSynopsis('');
    navigate(`/editor/${data.id}`);
  };

  const deleteStory = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    if (!confirm('确定要删除这个故事吗？此操作不可撤消。')) return;
    await api.deleteStory(id);
    setStories(stories.filter(s => s.id !== id));
  };

  return (
    <div className="flex-1 flex flex-col">
      <header className="border-b border-gray-800 px-6 py-4 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold tracking-wide">BookWright</h1>
          <p className="text-sm text-gray-500">AI小说写作与续写器</p>
        </div>
        <div className="flex gap-3">
          <button onClick={() => navigate('/settings')} className="flex items-center gap-2 px-3 py-1.5 border border-gray-700 rounded-lg hover:bg-gray-800 text-sm">
            <Settings size={16} /> 设置
          </button>
          <button onClick={() => setShowCreate(true)} className="flex items-center gap-2 px-4 py-1.5 bg-blue-600 rounded-lg hover:bg-blue-700 text-sm font-medium">
            <Plus size={16} /> 新建故事
          </button>
        </div>
      </header>

      {showCreate && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
          <div className="bg-gray-900 border border-gray-700 rounded-xl p-6 w-full max-w-md">
            <h2 className="text-lg font-bold mb-4">新建故事</h2>
            <input className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 mb-3 text-sm" placeholder="书名" value={title} onChange={e => setTitle(e.target.value)} />
            <input className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 mb-3 text-sm" placeholder="类型（玄幻/都市/科幻…）" value={genre} onChange={e => setGenre(e.target.value)} />
            <textarea className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 mb-4 text-sm h-24 resize-none" placeholder="故事梗概（可选）" value={synopsis} onChange={e => setSynopsis(e.target.value)} />
            <div className="flex gap-3 justify-end">
              <button onClick={() => setShowCreate(false)} className="px-4 py-1.5 border border-gray-700 rounded-lg text-sm hover:bg-gray-800">取消</button>
              <button onClick={createStory} className="px-4 py-1.5 bg-blue-600 rounded-lg text-sm font-medium hover:bg-blue-700">创建</button>
            </div>
          </div>
        </div>
      )}

      <main className="flex-1 overflow-auto p-6">
        {stories.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-gray-600">
            <BookOpen size={64} strokeWidth={1} />
            <p className="mt-4 text-lg">还没有故事，点击上方按钮创建一个吧</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {stories.map(story => (
              <div key={story.id} onClick={() => navigate(`/editor/${story.id}`)} className="bg-gray-900 border border-gray-800 rounded-xl p-5 cursor-pointer hover:border-gray-600 transition-colors group">
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <h3 className="font-bold text-lg truncate">{story.title}</h3>
                    <p className="text-sm text-gray-500 mt-1">{story.genre || '未分类'} · {story.chapters_count || 0}章 · {story.current_total_words?.toLocaleString() || 0}字</p>
                  </div>
                  <button onClick={(e) => deleteStory(e, story.id)} className="opacity-0 group-hover:opacity-100 p-1 hover:bg-red-900/50 rounded text-red-400 transition-all">
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}

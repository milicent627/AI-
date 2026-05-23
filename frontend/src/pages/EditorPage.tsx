import { useEffect, useState, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import { useStoryStore } from '../stores/storyStore';
import type { Chapter, WorldBookEntry, Foreshadowing, Summary } from '../types';
import {
  ArrowLeft, Send, GitBranch, Sparkles, BookOpen, Users, Eye, FileText,
  ChevronDown, Save, Wand2, MessageSquare, X
} from 'lucide-react';

export default function EditorPage() {
  const { storyId } = useParams<{ storyId: string }>();
  const navigate = useNavigate();
  const {
    currentStory, setCurrentStory,
    currentChapter, setCurrentChapter,
    chapters, setChapters,
  } = useStoryStore();

  const [content, setContent] = useState('');
  const [streamingText, setStreamingText] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [instruction, setInstruction] = useState('');
  const [direction, setDirection] = useState('');
  const [targetWords, setTargetWords] = useState(800);
  const [abortController, setAbortController] = useState<AbortController | null>(null);

  const [worldEntries, setWorldEntries] = useState<WorldBookEntry[]>([]);
  const [foreshadowings, setForeshadowings] = useState<Foreshadowing[]>([]);
  const [summaries, setSummaries] = useState<Summary[]>([]);
  const [activePanel, setActivePanel] = useState<'chapters' | 'world' | 'foreshadowing' | 'summaries' | 'assist'>('chapters');
  const [saveStatus, setSaveStatus] = useState<'saved' | 'saving' | 'unsaved'>('saved');

  // AI Assistant chat state
  const [chatMessages, setChatMessages] = useState<{ role: string; content: string }[]>([]);
  const [chatInput, setChatInput] = useState('');
  const [isChatLoading, setIsChatLoading] = useState(false);
  const chatAbortRef = useRef<AbortController | null>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const chatContentRef = useRef('');

  const contentRef = useRef(content);
  contentRef.current = content;
  const streamingRef = useRef('');
  streamingRef.current = streamingText;

  useEffect(() => {
    if (!storyId) return;
    Promise.all([
      api.getStory(storyId),
      api.listChapters(storyId),
      api.listWorldEntries(storyId),
      api.listForeshadowings(storyId),
      api.listSummaries(storyId),
    ]).then(([story, chData, worldData, fpData, sumData]) => {
      setCurrentStory(story);
      setChapters(chData.chapters || []);
      setWorldEntries(worldData.entries || []);
      setForeshadowings(fpData.foreshadowings || []);
      setSummaries(sumData.summaries || []);

      const lastChapter = (chData.chapters || []).slice(-1)[0];
      if (lastChapter) {
        loadChapterContent(lastChapter);
      }
    }).catch(console.error);
  }, [storyId]);

  const loadChapterContent = async (chapter: any) => {
    const ch = await api.getChapter(storyId!, chapter.id);
    setCurrentChapter(ch);
    setContent(ch.content || '');
    setSaveStatus('saved');
  };

  const saveChapter = useCallback(async () => {
    if (!storyId || !currentChapter || saveStatus === 'saving') return;
    setSaveStatus('saving');
    await api.updateChapter(storyId, currentChapter.id, { content: contentRef.current });
    setSaveStatus('saved');
  }, [storyId, currentChapter, saveStatus]);

  // WebSocket for analysis notifications
  useEffect(() => {
    if (!storyId) return;
    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const host = window.location.host;
    const ws = new WebSocket(`${protocol}://${host}/api/continuation/ws/${storyId}`);

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.event === 'analysis_complete') {
        api.listWorldEntries(storyId!).then(d => setWorldEntries(d.entries || [])).catch(() => {});
        api.listForeshadowings(storyId!).then(d => setForeshadowings(d.foreshadowings || [])).catch(() => {});
        api.listSummaries(storyId!).then(d => setSummaries(d.summaries || [])).catch(() => {});
      }
    };

    return () => ws.close();
  }, [storyId]);

  // Auto-save every 5 seconds
  useEffect(() => {
    if (saveStatus !== 'unsaved') return;
    const timer = setTimeout(saveChapter, 5000);
    return () => clearTimeout(timer);
  }, [saveStatus, saveChapter]);

  // Keyboard shortcut: Ctrl+S
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault();
        saveChapter();
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [saveChapter]);

  const handleContentChange = (newContent: string) => {
    setContent(newContent);
    setSaveStatus('unsaved');
  };

  const startContinuation = (type: 'normal' | 'directed' | 'branch') => {
    if (!storyId || !currentChapter || isStreaming) return;

    setIsStreaming(true);
    setStreamingText('');

    const data: any = {
      story_id: storyId,
      chapter_id: currentChapter.id,
      target_words: targetWords,
    };

    if (type === 'directed') {
      data.direction = direction;
      setDirection('');
    } else if (type === 'branch') {
      data.branch_point = instruction;
      data.branch_direction = direction || '走向不同的发展';
      setInstruction('');
      setDirection('');
    } else {
      data.instruction = instruction;
      setInstruction('');
    }

    const ctrl = api.continueStream(
      data,
      (chunk) => setStreamingText(prev => prev + chunk),
      () => {
        const collected = streamingRef.current;
        setIsStreaming(false);
        setContent(prev => prev + '\n\n' + collected);
        setStreamingText('');
        api.listChapters(storyId!).then(d => setChapters(d.chapters || [])).catch(() => {});
      },
      (err) => {
        setIsStreaming(false);
        alert(`续写出错: ${err}`);
      },
    );
  };

  const startPolishing = () => {
    if (!storyId || isStreaming) return;
    const textToPolish = content.slice(-5000);
    if (!textToPolish) return;

    setIsStreaming(true);
    setStreamingText('');

    api.polishStream(
      { story_id: storyId, chapter_id: currentChapter?.id, text: textToPolish },
      (chunk) => setStreamingText(prev => prev + chunk),
      () => {
        const polished = streamingRef.current;
        setIsStreaming(false);
        setStreamingText('');
        if (polished && confirm('润色完成，是否应用润色结果？')) {
          setContent(prev => {
            const keepLen = Math.max(0, prev.length - 5000);
            return prev.slice(0, keepLen) + polished;
          });
          setSaveStatus('unsaved');
        }
      },
      (err) => { setIsStreaming(false); alert(`润色出错: ${err}`); },
    );
  };

  const sendChatMessage = () => {
    if (!storyId || !chatInput.trim() || isChatLoading) return;

    const userMsg = { role: 'user', content: chatInput.trim() };
    const updated = [...chatMessages, userMsg];
    setChatMessages(updated);
    setChatInput('');
    setIsChatLoading(true);
    chatContentRef.current = '';

    const assistantMsg = { role: 'assistant', content: '' };
    setChatMessages(prev => [...prev, assistantMsg]);

    chatAbortRef.current = api.assistStream(
      storyId,
      updated,
      (chunk) => {
        chatContentRef.current += chunk;
        setChatMessages(prev => {
          const copy = [...prev];
          const last = copy[copy.length - 1];
          if (last && last.role === 'assistant') {
            last.content = chatContentRef.current;
          }
          return copy;
        });
      },
      () => {
        setIsChatLoading(false);
      },
      (err) => {
        setIsChatLoading(false);
        setChatMessages(prev => {
          const copy = [...prev];
          const last = copy[copy.length - 1];
          if (last && last.role === 'assistant') {
            last.content = `[错误] ${err}`;
          }
          return copy;
        });
      },
    );
  };

  // Auto-scroll chat to bottom
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages]);

  const panelContent = () => {
    switch (activePanel) {
      case 'chapters':
        return (
          <div className="space-y-1">
            {chapters.map(ch => (
              <button key={ch.id}
                onClick={() => loadChapterContent(ch)}
                className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors ${currentChapter?.id === ch.id ? 'bg-blue-900/50 text-blue-300' : 'hover:bg-gray-800 text-gray-400'}`}
              >
                <div className="flex items-center justify-between">
                  <span className="truncate">{ch.chapter_number}. {ch.title || `第${ch.chapter_number}章`}</span>
                  <span className="text-xs text-gray-600">{ch.word_count}字</span>
                </div>
                {ch.branch_name !== '主线' && (
                  <span className="text-xs text-amber-500 ml-1">[{ch.branch_name}]</span>
                )}
              </button>
            ))}
          </div>
        );
      case 'world':
        return (
          <div className="space-y-2">
            {worldEntries.map(e => (
              <details key={e.id} className="bg-gray-900 rounded-lg p-3 text-sm">
                <summary className="cursor-pointer font-medium flex items-center gap-2">
                  {e.category === 'character' ? '👤' : e.category === 'faction' ? '🏛' : e.category === 'location' ? '📍' : '📦'}
                  {e.name}
                  <span className="text-xs text-gray-600 ml-auto">{'★'.repeat(e.importance)}</span>
                </summary>
                <p className="mt-2 text-gray-400 whitespace-pre-wrap">{e.description}</p>
                {e.attributes && e.category === 'character' && (
                  <div className="mt-1 text-xs text-gray-500 space-y-0.5">
                    {e.attributes.identity && <div>身份: {e.attributes.identity}</div>}
                    {e.attributes.personality?.length > 0 && <div>性格: {e.attributes.personality.join('、')}</div>}
                    {e.attributes.abilities?.length > 0 && <div>能力: {e.attributes.abilities.join('、')}</div>}
                    {e.attributes.catchphrases?.length > 0 && <div>口头禅: {e.attributes.catchphrases.join('、')}</div>}
                  </div>
                )}
              </details>
            ))}
            {worldEntries.length === 0 && <p className="text-gray-600 text-sm p-3">暂无世界书条目，续写后自动分析</p>}
          </div>
        );
      case 'foreshadowing':
        return (
          <div className="space-y-2">
            {foreshadowings.map(f => (
              <div key={f.id} className={`bg-gray-900 rounded-lg p-3 text-sm border-l-2 ${f.status === 'revealed' ? 'border-green-500' : f.status === 'developing' ? 'border-amber-500' : 'border-blue-500'}`}>
                <div className="flex items-center justify-between">
                  <span className="font-medium">{f.title}</span>
                  <span className={`text-xs px-1.5 py-0.5 rounded ${f.status === 'planted' ? 'bg-blue-900/50 text-blue-400' : f.status === 'developing' ? 'bg-amber-900/50 text-amber-400' : 'bg-green-900/50 text-green-400'}`}>
                    {f.status === 'planted' ? '已埋下' : f.status === 'developing' ? '推进中' : '已揭示'}
                  </span>
                </div>
                <p className="mt-1 text-gray-400">{f.description}</p>
              </div>
            ))}
            {foreshadowings.length === 0 && <p className="text-gray-600 text-sm p-3">暂无伏笔，续写后自动检测</p>}
          </div>
        );
      case 'summaries':
        return (
          <div className="space-y-2">
            {summaries.map(s => (
              <div key={s.id} className={`bg-gray-900 rounded-lg p-3 text-sm ${s.type === 'large' ? 'border border-amber-700/50' : ''}`}>
                <div className="flex items-center justify-between mb-1">
                  <span className={`text-xs font-medium ${s.type === 'large' ? 'text-amber-400' : 'text-blue-400'}`}>
                    {s.type === 'large' ? '📋 大总结' : `📝 小总结 Lv${s.level}`}
                  </span>
                  <span className="text-xs text-gray-600">{s.word_count_before.toLocaleString()}→{s.word_count_after.toLocaleString()}字</span>
                </div>
                <p className="text-gray-400 whitespace-pre-wrap">{s.content}</p>
              </div>
            ))}
            {summaries.length === 0 && <p className="text-gray-600 text-sm p-3">暂无总结，归档章节后将自动生成</p>}
          </div>
        );
      case 'assist':
        return (
          <div className="flex flex-col h-full">
            <div className="flex-1 overflow-y-auto space-y-3 p-3">
              {chatMessages.length === 0 && (
                <div className="text-center text-gray-500 text-xs py-8">
                  <MessageSquare size={32} className="mx-auto mb-2 opacity-50" />
                  <p>AI 世界观构建助手</p>
                  <p className="mt-1">可以问我：设计角色、构建势力、完善设定等</p>
                </div>
              )}
              {chatMessages.map((msg, i) => (
                <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-[90%] rounded-lg px-3 py-2 text-xs leading-relaxed whitespace-pre-wrap ${
                    msg.role === 'user'
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-800 text-gray-300'
                  }`}>
                    {msg.content || (msg.role === 'assistant' && isChatLoading ? (
                      <span className="inline-flex gap-1">
                        <span className="w-1.5 h-3 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                        <span className="w-1.5 h-3 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                        <span className="w-1.5 h-3 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                      </span>
                    ) : null)}
                  </div>
                </div>
              ))}
              <div ref={chatEndRef} />
            </div>
            <div className="border-t border-gray-800 p-2 flex gap-2">
              <input
                value={chatInput}
                onChange={e => setChatInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && !e.shiftKey && sendChatMessage()}
                placeholder="问AI关于世界观的问题..."
                className="flex-1 bg-gray-900 border border-gray-700 rounded-lg px-3 py-1.5 text-xs outline-none focus:border-blue-600"
                disabled={isChatLoading}
              />
              <button
                onClick={sendChatMessage}
                disabled={isChatLoading || !chatInput.trim()}
                className="px-3 py-1.5 bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50 text-xs flex items-center gap-1"
              >
                <Send size={12} />
              </button>
            </div>
          </div>
        );
    }
  };

  return (
    <div className="h-screen flex flex-col">
      {/* Toolbar */}
      <header className="border-b border-gray-800 px-4 py-2 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <button onClick={() => navigate('/')} className="p-1 hover:bg-gray-800 rounded">
            <ArrowLeft size={18} />
          </button>
          <span className="font-bold">{currentStory?.title || '加载中...'}</span>
          <span className="text-xs text-gray-600">
            {saveStatus === 'saved' ? '✅ 已保存' : saveStatus === 'saving' ? '💾 保存中...' : '📝 未保存'}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => setActivePanel(activePanel === 'chapters' ? 'world' : 'chapters')}
            className="px-2 py-1 text-xs border border-gray-700 rounded hover:bg-gray-800 flex items-center gap-1">
            <BookOpen size={14} /> 章节
          </button>
          <button onClick={() => setActivePanel('world')}
            className={`px-2 py-1 text-xs border rounded hover:bg-gray-800 flex items-center gap-1 ${activePanel === 'world' ? 'border-blue-600 bg-blue-900/30' : 'border-gray-700'}`}>
            <Users size={14} /> 世界书
          </button>
          <button onClick={() => setActivePanel('foreshadowing')}
            className={`px-2 py-1 text-xs border rounded hover:bg-gray-800 flex items-center gap-1 ${activePanel === 'foreshadowing' ? 'border-blue-600 bg-blue-900/30' : 'border-gray-700'}`}>
            <Eye size={14} /> 伏笔
          </button>
          <button onClick={() => setActivePanel('summaries')}
            className={`px-2 py-1 text-xs border rounded hover:bg-gray-800 flex items-center gap-1 ${activePanel === 'summaries' ? 'border-blue-600 bg-blue-900/30' : 'border-gray-700'}`}>
            <FileText size={14} /> 总结
          </button>
          <button onClick={() => setActivePanel(activePanel === 'assist' ? 'chapters' : 'assist')}
            className={`px-2 py-1 text-xs border rounded hover:bg-gray-800 flex items-center gap-1 ${activePanel === 'assist' ? 'border-purple-600 bg-purple-900/30' : 'border-gray-700'}`}>
            <MessageSquare size={14} /> AI助手
          </button>
          <button onClick={saveChapter} className="px-3 py-1 text-xs bg-green-700 rounded hover:bg-green-600 flex items-center gap-1">
            <Save size={14} /> 保存
          </button>
        </div>
      </header>

      <div className="flex-1 flex overflow-hidden">
        {/* Sidebar */}
        <aside className="w-64 border-r border-gray-800 overflow-y-auto p-3 shrink-0">
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2 px-1">
            {activePanel === 'chapters' ? '📚 章节列表' : activePanel === 'world' ? '🌍 世界书' : activePanel === 'foreshadowing' ? '🔮 伏笔管理' : activePanel === 'assist' ? '🤖 AI助手' : '📊 总结'}
          </h3>
          {panelContent()}
        </aside>

        {/* Editor area */}
        <main className="flex-1 flex flex-col overflow-hidden">
          <div className="flex-1 overflow-y-auto p-6">
            <textarea
              value={content}
              onChange={e => handleContentChange(e.target.value)}
              className="w-full h-full bg-transparent resize-none outline-none text-base leading-8 text-gray-200 font-serif"
              placeholder="在这里开始你的故事，或点击下方续写按钮让 AI 帮你写..."
              style={{ fontFamily: '"Noto Serif SC", "Source Han Serif SC", "SimSun", serif' }}
            />

            {isStreaming && (
              <div className="mt-4 p-4 bg-blue-950/30 border border-blue-800/50 rounded-xl">
                <div className="flex items-center gap-2 text-sm text-blue-400 mb-2">
                  <Sparkles size={14} /> AI 正在续写...
                </div>
                <div className="text-gray-300 leading-8 whitespace-pre-wrap streaming-cursor" style={{ fontFamily: '"Noto Serif SC", serif' }}>
                  {streamingText}
                </div>
              </div>
            )}
          </div>

          {/* Continuation controls */}
          <div className="border-t border-gray-800 p-4 shrink-0">
            <div className="flex gap-2 mb-2">
              <input
                value={instruction}
                onChange={e => setInstruction(e.target.value)}
                placeholder="续写指令（如：主角遇到了一个神秘老人）"
                className="flex-1 bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm outline-none focus:border-blue-600"
                disabled={isStreaming}
              />
              <input
                value={direction}
                onChange={e => setDirection(e.target.value)}
                placeholder="定向方向（可选）"
                className="w-48 bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm outline-none focus:border-blue-600"
                disabled={isStreaming}
              />
              <select
                value={targetWords}
                onChange={e => setTargetWords(Number(e.target.value))}
                className="bg-gray-900 border border-gray-700 rounded-lg px-2 py-1 text-sm"
                disabled={isStreaming}
              >
                <option value={300}>300字</option>
                <option value={500}>500字</option>
                <option value={800}>800字</option>
                <option value={1200}>1200字</option>
                <option value={2000}>2000字</option>
              </select>
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => startContinuation('normal')}
                disabled={isStreaming}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50 text-sm font-medium"
              >
                <Send size={14} /> 续写
              </button>
              <button
                onClick={() => startContinuation('directed')}
                disabled={isStreaming}
                className="flex items-center gap-2 px-4 py-2 bg-purple-600 rounded-lg hover:bg-purple-700 disabled:opacity-50 text-sm"
              >
                <Sparkles size={14} /> 定向续写
              </button>
              <button
                onClick={() => startContinuation('branch')}
                disabled={isStreaming}
                className="flex items-center gap-2 px-4 py-2 bg-amber-600 rounded-lg hover:bg-amber-700 disabled:opacity-50 text-sm"
              >
                <GitBranch size={14} /> 分支续写
              </button>
              <div className="flex-1" />
              <button
                onClick={startPolishing}
                disabled={isStreaming || !content}
                className="flex items-center gap-2 px-4 py-2 border border-gray-700 rounded-lg hover:bg-gray-800 disabled:opacity-50 text-sm"
              >
                <Wand2 size={14} /> 润色
              </button>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}

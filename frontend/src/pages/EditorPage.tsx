import { useEffect, useState, useRef, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { api } from '../api/client';
import { useStoryStore } from '../stores/storyStore';
import { useEditorStore } from '../stores/editorStore';
import { TopToolbar } from '../components/TopToolbar';
import { AccordionSidebar } from '../components/AccordionSidebar';
import { ChapterList } from '../components/ChapterList';
import { WorldBookList } from '../components/WorldBookList';
import { ForeshadowingList } from '../components/ForeshadowingList';
import { SummaryList } from '../components/SummaryList';
import { AIAssistDialog } from '../components/AIAssistDialog';
import { ContinuationControls, type ContinuationData } from '../components/ContinuationControls';
import { TiptapEditor, type TiptapEditorHandle } from '../components/TiptapEditor';
import { useSplitPane } from '../hooks/useSplitPane';
import {
  BookOpen, Users, Eye, FileText,
} from 'lucide-react';
import type { Chapter } from '../types';

export default function EditorPage() {
  const { storyId } = useParams<{ storyId: string }>();
  const {
    currentStory, setCurrentStory,
    currentChapter, setCurrentChapter,
    chapters, setChapters,
  } = useStoryStore();

  const {
    activeSection, setActiveSection,
    worldEntries, setWorldEntries,
    foreshadowings, setForeshadowings,
    summaries, setSummaries,
    isAIDialogOpen, setAIDialogOpen,
  } = useEditorStore();

  // Editor state
  const [editorHTML, setEditorHTML] = useState('');
  const [saveStatus, setSaveStatus] = useState<'saved' | 'saving' | 'unsaved'>('saved');
  const [isStreaming, setIsStreaming] = useState(false);
  const [wordCount, setWordCount] = useState(0);
  const editorRef = useRef<TiptapEditorHandle>(null);
  const htmlRef = useRef(editorHTML);
  htmlRef.current = editorHTML;

  // Split pane
  const { size: sidebarWidth, isDragging, containerRef, onMouseDown } = useSplitPane({
    initialSize: 280,
    minSize: 220,
    maxRatio: 0.45,
  });

  // Fetch all data on mount
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

  const loadChapterContent = async (chapter: Chapter) => {
    const ch = await api.getChapter(storyId!, chapter.id);
    setCurrentChapter(ch);
    setEditorHTML(ch.content || '');
    setSaveStatus('saved');
    if (editorRef.current) {
      editorRef.current.setContent(ch.content || '');
    }
  };

  // Save
  const saveChapter = useCallback(async () => {
    if (!storyId || !currentChapter || saveStatus === 'saving') return;
    setSaveStatus('saving');
    const html = editorRef.current?.getHTML() || htmlRef.current;
    await api.updateChapter(storyId, currentChapter.id, { content: html });
    setSaveStatus('saved');
  }, [storyId, currentChapter, saveStatus]);

  // WebSocket for analysis notifications
  useEffect(() => {
    if (!storyId) return;
    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const host = window.location.host;
    const ws = new WebSocket(`${protocol}://${host}/api/continuation/ws/${storyId}`);

    ws.onmessage = () => {
      api.listWorldEntries(storyId!).then((d) => setWorldEntries(d.entries || [])).catch(() => {});
      api.listForeshadowings(storyId!).then((d) => setForeshadowings(d.foreshadowings || [])).catch(() => {});
      api.listSummaries(storyId!).then((d) => setSummaries(d.summaries || [])).catch(() => {});
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

  const handleEditorChange = (html: string) => {
    setEditorHTML(html);
    setSaveStatus('unsaved');
    setWordCount(html.replace(/<[^>]*>/g, '').length);
  };

  // Continuation
  const handleContinue = (data: ContinuationData) => {
    if (!storyId || !currentChapter || isStreaming) return;

    setIsStreaming(true);
    const pos = editorRef.current?.insertAICard({ content: '', status: 'streaming' });
    let accumulated = '';

    api.continueStream(
      data,
      (chunk) => {
        accumulated += chunk;
        if (pos != null) {
          editorRef.current?.updateAICard(pos, { content: accumulated });
        }
      },
      () => {
        if (pos != null) {
          editorRef.current?.updateAICard(pos, { content: accumulated, status: 'complete' });
        }
        setIsStreaming(false);
        api.listChapters(storyId!).then((d) => setChapters(d.chapters || [])).catch(() => {});
      },
      (err) => {
        if (pos != null) {
          editorRef.current?.updateAICard(pos, { status: 'rejected', content: err });
        }
        setIsStreaming(false);
        alert(`续写出错: ${err}`);
      },
    );
  };

  // Polish
  const handlePolish = () => {
    if (!storyId || isStreaming) return;
    const textToPolish = editorRef.current?.getHTML() || editorHTML;
    if (!textToPolish) return;

    setIsStreaming(true);
    api.polishStream(
      { story_id: storyId, chapter_id: currentChapter?.id, text: textToPolish.slice(-5000) },
      () => {},
      () => {
        setIsStreaming(false);
        setSaveStatus('unsaved');
      },
      (err) => {
        setIsStreaming(false);
        alert(`润色出错: ${err}`);
      },
    );
  };

  // Sidebar sections
  const sections = [
    {
      id: 'chapters' as const,
      label: '章节列表',
      icon: <BookOpen size={16} />,
      content: (
        <ChapterList
          chapters={chapters}
          currentChapterId={currentChapter?.id}
          onSelect={loadChapterContent}
        />
      ),
      badge: chapters.length,
    },
    {
      id: 'world' as const,
      label: '世界书',
      icon: <Users size={16} />,
      content: (
        <WorldBookList
          entries={worldEntries}
          storyId={storyId!}
          worldBookName={currentStory?.world_book_name || ''}
          onWorldBookNameChange={async (name) => {
            if (!storyId || !currentStory) return;
            setCurrentStory({ ...currentStory, world_book_name: name });
            await api.updateStory(storyId, { world_book_name: name });
          }}
          onEntriesChange={setWorldEntries}
        />
      ),
      badge: worldEntries.length,
    },
    {
      id: 'foreshadowing' as const,
      label: '伏笔',
      icon: <Eye size={16} />,
      content: <ForeshadowingList foreshadowings={foreshadowings} />,
      badge: foreshadowings.length,
    },
    {
      id: 'summaries' as const,
      label: '总结',
      icon: <FileText size={16} />,
      content: <SummaryList summaries={summaries} />,
      badge: summaries.length,
    },
  ];

  return (
    <div className="h-screen flex flex-col bg-white">
      <TopToolbar
        title={currentStory?.title || '加载中...'}
        storyId={storyId || ''}
        saveStatus={saveStatus}
        onSave={saveChapter}
      />

      <div
        ref={containerRef}
        className="flex-1 flex overflow-hidden"
        style={{ cursor: isDragging ? 'col-resize' : 'default' }}
      >
        {/* Sidebar */}
        <aside style={{ width: sidebarWidth, flexShrink: 0 }} className="overflow-hidden">
          <AccordionSidebar
            sections={sections}
            activeSection={activeSection}
            onSectionChange={setActiveSection}
            onAIAssistClick={() => setAIDialogOpen(true)}
          />
        </aside>

        {/* Splitter */}
        <div
          onMouseDown={onMouseDown}
          className={`w-1 cursor-col-resize shrink-0 transition-colors ${
            isDragging ? 'bg-blue-500' : 'bg-gray-200 hover:bg-blue-400'
          }`}
        />

        {/* Editor */}
        <main className="flex-1 flex flex-col overflow-hidden">
          <TiptapEditor
            ref={editorRef}
            content={editorHTML}
            onChange={handleEditorChange}
            placeholder="在这里开始你的故事，或点击下方续写按钮让 AI 帮你写..."
            editable={!isStreaming}
          />

          <ContinuationControls
            isStreaming={isStreaming}
            hasContent={!!editorHTML}
            storyId={storyId || ''}
            chapterId={currentChapter?.id || ''}
            wordCount={wordCount}
            onContinue={handleContinue}
            onPolish={handlePolish}
          />
        </main>
      </div>

      <AIAssistDialog
        isOpen={isAIDialogOpen}
        onClose={() => setAIDialogOpen(false)}
        storyId={storyId || ''}
      />
    </div>
  );
}

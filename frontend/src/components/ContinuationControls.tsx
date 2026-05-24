import { useState } from 'react';
import { Send, Sparkles, GitBranch, Wand2, ChevronDown, ChevronUp } from 'lucide-react';

export interface ContinuationData {
  story_id: string;
  chapter_id: string;
  instruction?: string;
  direction?: string;
  branch_point?: string;
  branch_direction?: string;
  target_words: number;
  type: 'normal' | 'directed' | 'branch';
}

interface ContinuationControlsProps {
  isStreaming: boolean;
  hasContent: boolean;
  storyId: string;
  chapterId: string;
  wordCount: number;
  onContinue: (data: ContinuationData) => void;
  onPolish: () => void;
}

export function ContinuationControls({
  isStreaming,
  hasContent,
  storyId,
  chapterId,
  wordCount,
  onContinue,
  onPolish,
}: ContinuationControlsProps) {
  const [instruction, setInstruction] = useState('');
  const [direction, setDirection] = useState('');
  const [targetWords, setTargetWords] = useState(800);
  const [showAdvanced, setShowAdvanced] = useState(false);

  const start = (type: 'normal' | 'directed' | 'branch') => {
    if (!storyId || !chapterId || isStreaming) return;

    const data: ContinuationData = {
      story_id: storyId,
      chapter_id: chapterId,
      target_words: targetWords,
      type,
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

    onContinue(data);
  };

  return (
    <div className="border-t border-gray-800 p-4 shrink-0">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-xs text-gray-500 shrink-0">
          {wordCount.toLocaleString()} 字
        </span>
        <div className="flex-1" />
        <select
          value={targetWords}
          onChange={(e) => setTargetWords(Number(e.target.value))}
          className="bg-gray-900 border border-gray-800 rounded-lg px-2 py-1.5 text-xs text-gray-300"
          disabled={isStreaming}
        >
          <option value={300}>300字</option>
          <option value={500}>500字</option>
          <option value={800}>800字</option>
          <option value={1200}>1200字</option>
          <option value={2000}>2000字</option>
        </select>
      </div>

      <div className="flex gap-2 mb-2">
        <input
          value={instruction}
          onChange={(e) => setInstruction(e.target.value)}
          placeholder="续写指令（如：主角遇到了一个神秘老人）"
          className="flex-1 bg-gray-900 border border-gray-800 rounded-lg px-3 py-2 text-sm outline-none focus:border-blue-500 text-gray-200"
          disabled={isStreaming}
        />
      </div>

      <div className="flex gap-2">
        <button
          onClick={() => start('normal')}
          disabled={isStreaming}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 text-sm font-medium"
        >
          <Send size={14} /> 续写
        </button>

        <button
          onClick={() => setShowAdvanced(!showAdvanced)}
          className={`flex items-center gap-1 px-3 py-2 text-xs border rounded-lg hover:bg-gray-800 transition-colors ${
            showAdvanced ? 'border-blue-400 text-blue-400 bg-blue-900/30' : 'border-gray-800 text-gray-400'
          }`}
        >
          {showAdvanced ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          高级
        </button>

        <div className="flex-1" />

        <button
          onClick={onPolish}
          disabled={isStreaming || !hasContent}
          className="flex items-center gap-2 px-4 py-2 border border-gray-800 rounded-lg hover:bg-gray-800 disabled:opacity-50 text-sm text-gray-300"
        >
          <Wand2 size={14} /> 润色
        </button>
      </div>

      {showAdvanced && (
        <div className="flex gap-2 mt-2 pt-2 border-t border-gray-800">
          <input
            value={direction}
            onChange={(e) => setDirection(e.target.value)}
            placeholder="定向方向（可选）"
            className="flex-1 bg-gray-900 border border-gray-800 rounded-lg px-3 py-2 text-sm outline-none focus:border-purple-500 text-gray-200"
            disabled={isStreaming}
          />
          <button
            onClick={() => start('directed')}
            disabled={isStreaming}
            className="flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 text-sm shrink-0"
          >
            <Sparkles size={14} /> 定向续写
          </button>
          <button
            onClick={() => start('branch')}
            disabled={isStreaming}
            className="flex items-center gap-2 px-4 py-2 bg-amber-600 text-white rounded-lg hover:bg-amber-700 disabled:opacity-50 text-sm shrink-0"
          >
            <GitBranch size={14} /> 分支续写
          </button>
        </div>
      )}
    </div>
  );
}

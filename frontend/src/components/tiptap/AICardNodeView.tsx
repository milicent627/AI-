import { NodeViewProps, NodeViewWrapper } from '@tiptap/react';
import { Sparkles, Check, X } from 'lucide-react';

export function AICardNodeView({ node, updateAttributes, editor, getPos, deleteNode }: NodeViewProps) {
  const { content, status } = node.attrs as { content: string; status: string; instruction?: string };

  const handleAccept = () => {
    const pos = getPos();
    editor
      .chain()
      .focus()
      .deleteRange({ from: pos, to: pos + node.nodeSize })
      .insertContentAt(pos, content)
      .run();
  };

  const handleReject = () => {
    const pos = getPos();
    editor
      .chain()
      .focus()
      .deleteRange({ from: pos, to: pos + node.nodeSize })
      .run();
  };

  const isComplete = status === 'complete';
  const isStreaming = status === 'streaming';

  return (
    <NodeViewWrapper as="div" className="ai-card my-4 rounded-xl border border-blue-800 bg-blue-900/20 p-4" data-ai-card="">
      <div className="flex items-center gap-2 text-sm text-blue-400 mb-3">
        <Sparkles size={14} className={isStreaming ? 'animate-pulse' : ''} />
        <span className="font-medium">
          {isStreaming ? 'AI 正在生成...' : 'AI 生成完成'}
        </span>
      </div>

      <div className="text-gray-200 leading-8 whitespace-pre-wrap font-serif text-base">
        {content || (isStreaming && (
          <span className="inline-flex items-center gap-1 text-blue-400">
            <span className="animate-bounce" style={{ animationDelay: '0ms' }}>.</span>
            <span className="animate-bounce" style={{ animationDelay: '150ms' }}>.</span>
            <span className="animate-bounce" style={{ animationDelay: '300ms' }}>.</span>
          </span>
        ))}
      </div>

      {isComplete && (
        <div className="flex items-center gap-2 mt-3 pt-3 border-t border-blue-900/50">
          <button
            onClick={handleAccept}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            <Check size={12} /> 采纳
          </button>
          <button
            onClick={handleReject}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs border border-gray-700 text-gray-300 rounded-lg hover:bg-gray-800 transition-colors"
          >
            <X size={12} /> 放弃
          </button>
        </div>
      )}
    </NodeViewWrapper>
  );
}

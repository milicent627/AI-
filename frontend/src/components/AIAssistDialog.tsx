import { useState, useRef, useEffect } from 'react';
import { MessageSquare, Send, X } from 'lucide-react';
import { useSSEStream } from '../hooks/useSSEStream';
import type { AIAssistMessage } from '../types/editor';

interface AIAssistDialogProps {
  isOpen: boolean;
  onClose: () => void;
  storyId: string;
}

const BASE = '/api';

export function AIAssistDialog({ isOpen, onClose, storyId }: AIAssistDialogProps) {
  const [messages, setMessages] = useState<AIAssistMessage[]>([]);
  const [input, setInput] = useState('');
  const { isStreaming, content, error, start } = useSSEStream();
  const chatEndRef = useRef<HTMLDivElement>(null);
  const assistantMsgRef = useRef(false);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    if (!isStreaming && assistantMsgRef.current && content) {
      setMessages((prev) => {
        const copy = [...prev];
        const last = copy[copy.length - 1];
        if (last && last.role === 'assistant') {
          last.content = content;
        }
        return copy;
      });
    }
  }, [isStreaming, content]);

  const sendMessage = () => {
    if (!input.trim() || isStreaming) return;

    const userMsg: AIAssistMessage = { role: 'user', content: input.trim() };
    setMessages((prev) => {
      const assistantMsg: AIAssistMessage = { role: 'assistant', content: '' };
      const updated = [...prev, userMsg, assistantMsg];
      assistantMsgRef.current = true;
      start(`${BASE}/world-book/${storyId}/assist-stream`, { messages: updated });
      return updated;
    });
    setInput('');
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-end p-4 pt-16">
      <div className="absolute inset-0 bg-black/20" onClick={onClose} />
      <div className="relative bg-white rounded-2xl shadow-xl border border-gray-200 w-full max-w-md h-[520px] flex flex-col">
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
          <div className="flex items-center gap-2 text-sm font-semibold text-gray-700">
            <MessageSquare size={16} /> AI 写作助手
          </div>
          <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded text-gray-400">
            <X size={16} />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {messages.length === 0 && (
            <div className="text-center text-gray-400 text-sm py-12">
              <MessageSquare size={32} className="mx-auto mb-2 opacity-30" />
              <p>AI 世界观构建助手</p>
              <p className="mt-1">可以问我：设计角色、构建势力、完善设定等</p>
            </div>
          )}
          {messages.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div
                className={`max-w-[90%] rounded-xl px-3 py-2 text-sm leading-relaxed whitespace-pre-wrap ${
                  msg.role === 'user'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-700'
                }`}
              >
                {msg.content || (msg.role === 'assistant' && isStreaming && i === messages.length - 1 ? (
                  <span className="inline-flex gap-1">
                    <span className="w-1.5 h-3 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                    <span className="w-1.5 h-3 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                    <span className="w-1.5 h-3 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                  </span>
                ) : null)}
              </div>
            </div>
          ))}
          {error && (
            <div className="text-center text-red-500 text-xs py-2">错误: {error}</div>
          )}
          <div ref={chatEndRef} />
        </div>

        <div className="border-t border-gray-100 p-3 flex gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && sendMessage()}
            placeholder="问 AI 关于世界观的问题..."
            className="flex-1 bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 text-sm outline-none focus:border-blue-500"
            disabled={isStreaming}
          />
          <button
            onClick={sendMessage}
            disabled={isStreaming || !input.trim()}
            className="px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 text-sm flex items-center gap-1"
          >
            <Send size={14} />
          </button>
        </div>
      </div>
    </div>
  );
}

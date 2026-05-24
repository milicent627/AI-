import { Node } from '@tiptap/core';
import { ReactNodeViewRenderer } from '@tiptap/react';
import { AICardNodeView } from './AICardNodeView';

export interface AICardAttributes {
  content: string;
  status: 'streaming' | 'complete' | 'rejected';
  instruction?: string;
}

export const AICardNode = Node.create({
  name: 'aiCard',

  group: 'block',

  atom: true,

  addAttributes() {
    return {
      content: { default: '' },
      status: { default: 'streaming' },
      instruction: { default: '' },
    };
  },

  parseHTML() {
    return [{ tag: 'div[data-ai-card]' }];
  },

  renderHTML({ HTMLAttributes }) {
    return ['div', { 'data-ai-card': '', ...HTMLAttributes }];
  },

  addNodeView() {
    return ReactNodeViewRenderer(AICardNodeView);
  },
});

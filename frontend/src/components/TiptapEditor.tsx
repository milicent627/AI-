import { forwardRef, useImperativeHandle, useCallback } from 'react';
import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import Placeholder from '@tiptap/extension-placeholder';
import { SmartPunctuation } from './tiptap/SmartPunctuation';
import { AICardNode, type AICardAttributes } from './tiptap/AICardNode';

export interface TiptapEditorHandle {
  getHTML: () => string;
  insertAICard: (attrs: AICardAttributes) => number | null;
  updateAICard: (pos: number, attrs: Partial<AICardAttributes>) => void;
  setContent: (html: string) => void;
}

interface TiptapEditorProps {
  content: string;
  onChange: (html: string) => void;
  placeholder?: string;
  editable?: boolean;
}

function contentToHtml(content: string): string {
  if (/<[a-z][\s\S]*>/i.test(content)) return content;
  return content
    .split('\n\n')
    .filter(Boolean)
    .map((p) => `<p>${p.replace(/\n/g, '<br>')}</p>`)
    .join('');
}

export const TiptapEditor = forwardRef<TiptapEditorHandle, TiptapEditorProps>(
  function TiptapEditor({ content, onChange, placeholder, editable = true }, ref) {
    const editor = useEditor({
      extensions: [
        StarterKit.configure({ heading: { levels: [1, 2, 3] } }),
        Placeholder.configure({ placeholder: placeholder || '在这里开始你的故事...' }),
        SmartPunctuation,
        AICardNode,
      ],
      content: contentToHtml(content),
      editable,
      onUpdate: ({ editor: ed }) => onChange(ed.getHTML()),
      editorProps: {
        attributes: {
          class: 'prose prose-base max-w-none',
        },
      },
    });

    useImperativeHandle(
      ref,
      () => ({
        getHTML: () => editor?.getHTML() || '',

        insertAICard: (attrs: AICardAttributes) => {
          if (!editor) return null;
          const { state } = editor;
          const { from } = state.selection;
          editor.chain().focus().insertContent({ type: 'aiCard', attrs }).run();
          return from;
        },

        updateAICard: (pos: number, attrs: Partial<AICardAttributes>) => {
          if (!editor) return;
          try {
            editor
              .chain()
              .command(({ tr }) => {
                const node = tr.doc.nodeAt(pos);
                if (node && node.type.name === 'aiCard') {
                  tr.setNodeMarkup(pos, undefined, { ...node.attrs, ...attrs });
                  return true;
                }
                return false;
              })
              .run();
          } catch {
            // Node may have been removed
          }
        },

        setContent: (html: string) => {
          editor?.commands.setContent(contentToHtml(html));
        },
      }),
      [editor],
    );

    return (
      <div className="tiptap-editor flex-1 overflow-y-auto px-8 py-6">
        <EditorContent editor={editor} />
      </div>
    );
  },
);

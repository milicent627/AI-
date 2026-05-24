import { Extension } from '@tiptap/core';
import { InputRule } from '@tiptap/core';

function countQuotes(text: string): { open: number; close: number } {
  const open = (text.match(/“/g) || []).length;
  const close = (text.match(/”/g) || []).length;
  return { open, close };
}

const smartDoubleQuote = new InputRule({
  find: /"$/,
  handler: ({ state, range }) => {
    const before = state.doc.textBetween(0, range.from);
    const { open, close } = countQuotes(before);
    const replacement = open === close ? '“' : '”';
    state.tr.replaceWith(range.from, range.to, state.schema.text(replacement));
  },
});

const smartSingleQuote = new InputRule({
  find: /'$/,
  handler: ({ state, range }) => {
    const before = state.doc.textBetween(0, range.from);
    const open = (before.match(/‘/g) || []).length;
    const close = (before.match(/’/g) || []).length;
    const replacement = open === close ? '‘' : '’';
    state.tr.replaceWith(range.from, range.to, state.schema.text(replacement));
  },
});

const ellipsisRule = new InputRule({
  find: /\.\.\.$/,
  handler: ({ state, range }) => {
    state.tr.replaceWith(range.from, range.to, state.schema.text('…'));
  },
});

const emDashRule = new InputRule({
  find: /---$/,
  handler: ({ state, range }) => {
    state.tr.replaceWith(range.from, range.to, state.schema.text('—'));
  },
});

export const SmartPunctuation = Extension.create({
  name: 'smartPunctuation',

  addInputRules() {
    return [smartDoubleQuote, smartSingleQuote, ellipsisRule, emDashRule];
  },
});

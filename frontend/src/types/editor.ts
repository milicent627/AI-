export type AccordionSection = 'chapters' | 'world' | 'foreshadowing' | 'summaries';

export interface AIAssistMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface AICardAttrs {
  content: string;
  status: 'streaming' | 'complete' | 'accepted' | 'rejected';
  instruction?: string;
}

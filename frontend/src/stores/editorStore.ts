import { create } from 'zustand';
import type { AccordionSection } from '../types/editor';
import type { WorldBookEntry, Foreshadowing, Summary } from '../types';

interface EditorState {
  activeSection: AccordionSection | null;
  setActiveSection: (section: AccordionSection | null) => void;

  worldEntries: WorldBookEntry[];
  setWorldEntries: (entries: WorldBookEntry[]) => void;

  foreshadowings: Foreshadowing[];
  setForeshadowings: (foreshadowings: Foreshadowing[]) => void;

  summaries: Summary[];
  setSummaries: (summaries: Summary[]) => void;

  isAIDialogOpen: boolean;
  setAIDialogOpen: (open: boolean) => void;

  sidebarWidth: number;
  setSidebarWidth: (width: number) => void;
}

export const useEditorStore = create<EditorState>((set) => ({
  activeSection: 'chapters',
  setActiveSection: (section) => set({ activeSection: section }),

  worldEntries: [],
  setWorldEntries: (entries) => set({ worldEntries: entries }),

  foreshadowings: [],
  setForeshadowings: (foreshadowings) => set({ foreshadowings }),

  summaries: [],
  setSummaries: (summaries) => set({ summaries }),

  isAIDialogOpen: false,
  setAIDialogOpen: (open) => set({ isAIDialogOpen: open }),

  sidebarWidth: 280,
  setSidebarWidth: (width) => set({ sidebarWidth: width }),
}));

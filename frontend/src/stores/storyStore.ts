import { create } from 'zustand';
import type { Story, Chapter } from '../types';

interface StoryState {
  stories: Story[];
  currentStory: Story | null;
  currentChapter: Chapter | null;
  chapters: Chapter[];
  loading: boolean;

  setStories: (stories: Story[]) => void;
  setCurrentStory: (story: Story | null) => void;
  setCurrentChapter: (chapter: Chapter | null) => void;
  setChapters: (chapters: Chapter[]) => void;
  setLoading: (loading: boolean) => void;
}

export const useStoryStore = create<StoryState>((set) => ({
  stories: [],
  currentStory: null,
  currentChapter: null,
  chapters: [],
  loading: false,

  setStories: (stories) => set({ stories }),
  setCurrentStory: (story) => set({ currentStory: story }),
  setCurrentChapter: (chapter) => set({ currentChapter: chapter }),
  setChapters: (chapters) => set({ chapters }),
  setLoading: (loading) => set({ loading }),
}));

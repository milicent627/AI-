export interface Story {
  id: string;
  title: string;
  author: string;
  genre: string;
  synopsis: string;
  style_guide: string;
  target_chapter_words: number;
  small_summary_chapter_count: number;
  large_summary_merge_count: number;
  auto_hide_summarized: boolean;
  current_total_words: number;
  status: 'ongoing' | 'completed' | 'paused';
  chapters_count?: number;
  created_at: string;
  updated_at: string;
}

export interface Chapter {
  id: string;
  chapter_number: number;
  title: string;
  content: string;
  word_count: number;
  status: 'draft' | 'polished' | 'archived';
  is_archived: boolean;
  hidden: boolean;
  branch_name: string;
  parent_chapter_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface Summary {
  id: string;
  type: 'small' | 'large';
  level: number;
  content: string;
  word_count_before: number;
  word_count_after: number;
  covered_chapter_ids: string[];
  created_at: string;
}

export interface WorldBookEntry {
  id: string;
  category: 'character' | 'faction' | 'location' | 'item' | 'power_system' | 'catchphrase' | 'custom';
  name: string;
  description: string;
  aliases: string[];
  attributes: CharacterAttributes | Record<string, any>;
  importance: number;
  sort_order: number;
  status: string;
  version: number;
  source_chapter_id: string | null;
  relations?: Relation[];
  updated_at: string;
}

export interface CharacterAttributes {
  gender?: string;
  age?: string;
  appearance?: string;
  identity?: string;
  personality?: string[];
  abilities?: string[];
  catchphrases?: string[];
  status_note?: string;
  [key: string]: any;
}

export interface Relation {
  id: string;
  other_name: string;
  other_id: string;
  relation_type: string;
  description: string;
  intensity: number;
  direction: 'outgoing' | 'incoming';
}

export interface Foreshadowing {
  id: string;
  title: string;
  description: string;
  plant_chapter_id: string | null;
  reveal_chapter_id: string | null;
  status: 'planted' | 'developing' | 'revealed' | 'abandoned';
  priority: number;
  related_entries: string[];
  notes: string;
  created_at: string;
  updated_at: string;
}

export interface ModelConfig {
  id: string;
  name: string;
  provider: 'openai' | 'anthropic' | 'deepseek' | 'ollama';
  model_id: string;
  role: 'continuation' | 'polishing' | 'small_summary' | 'large_summary' | 'world_analysis' | 'foreshadowing';
  temperature: number;
  max_tokens: number;
  is_active: boolean;
  api_key: string;
}

export interface PromptFragment {
  id: string;
  content: string;
  sort_order: number;
  is_active: boolean;
}

export interface PromptPreset {
  id: string;
  name: string;
  role: string;
  content: string;
  is_default: boolean;
  created_at: string;
  fragments: PromptFragment[];
}

export interface ContinuationRequest {
  story_id: string;
  chapter_id: string;
  instruction?: string;
  direction?: string;
  branch_point?: string;
  branch_direction?: string;
  target_words?: number;
}

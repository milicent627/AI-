import type { ReactNode } from 'react';
import { MessageSquare, ChevronRight } from 'lucide-react';
import type { AccordionSection } from '../types/editor';

interface AccordionSectionConfig {
  id: AccordionSection;
  label: string;
  icon: ReactNode;
  content: ReactNode;
  badge?: number;
}

interface AccordionSidebarProps {
  sections: AccordionSectionConfig[];
  activeSection: AccordionSection | null;
  onSectionChange: (sectionId: AccordionSection | null) => void;
  onAIAssistClick: () => void;
}

export function AccordionSidebar({
  sections,
  activeSection,
  onSectionChange,
  onAIAssistClick,
}: AccordionSidebarProps) {
  return (
    <div className="flex flex-col h-full bg-gray-50">
      <div className="flex-1 overflow-y-auto border-r border-gray-200">
        {sections.map((section) => {
          const isOpen = activeSection === section.id;
          return (
            <div key={section.id} className="border-b border-gray-200">
              <button
                onClick={() => onSectionChange(isOpen ? null : section.id)}
                className={`w-full flex items-center justify-between px-3 py-2.5 text-sm transition-colors ${
                  isOpen
                    ? 'bg-white text-gray-800 font-medium'
                    : 'text-gray-600 hover:bg-gray-100'
                }`}
              >
                <span className="flex items-center gap-2">
                  <span className="shrink-0">{section.icon}</span>
                  <span>{section.label}</span>
                  {section.badge != null && section.badge > 0 && (
                    <span className="text-xs bg-gray-200 text-gray-500 px-1.5 py-0.5 rounded-full">
                      {section.badge}
                    </span>
                  )}
                </span>
                <ChevronRight
                  size={16}
                  className={`transition-transform ${isOpen ? 'rotate-90' : ''}`}
                />
              </button>
              {isOpen && (
                <div className="px-3 pb-3 max-h-[60vh] overflow-y-auto">
                  {section.content}
                </div>
              )}
            </div>
          );
        })}
      </div>

      <div className="border-t border-r border-gray-200 p-2">
        <button
          onClick={onAIAssistClick}
          className="w-full flex items-center justify-center gap-2 px-3 py-2 text-sm text-blue-600 bg-blue-50 rounded-lg hover:bg-blue-100 transition-colors"
        >
          <MessageSquare size={16} /> AI助手
        </button>
      </div>
    </div>
  );
}

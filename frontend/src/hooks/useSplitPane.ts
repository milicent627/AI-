import { useState, useRef, useCallback, useEffect } from 'react';

interface UseSplitPaneOptions {
  initialSize: number;
  minSize: number;
  maxRatio: number;
}

export function useSplitPane(options: UseSplitPaneOptions) {
  const [size, setSize] = useState(options.initialSize);
  const [isDragging, setIsDragging] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const onMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  useEffect(() => {
    if (!isDragging) return;

    const onMouseMove = (e: MouseEvent) => {
      if (!containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const newSize = e.clientX - rect.left;
      const clamped = Math.max(
        options.minSize,
        Math.min(newSize, rect.width * options.maxRatio),
      );
      setSize(clamped);
    };

    const onMouseUp = () => setIsDragging(false);

    document.addEventListener('mousemove', onMouseMove);
    document.addEventListener('mouseup', onMouseUp);
    return () => {
      document.removeEventListener('mousemove', onMouseMove);
      document.removeEventListener('mouseup', onMouseUp);
    };
  }, [isDragging, options.minSize, options.maxRatio]);

  return { size, isDragging, containerRef, onMouseDown };
}

import { useState, useRef, useEffect } from "react";
import "./ScheduleEditor.css";

interface ScheduleBlock {
  id: number;
  type: "study" | "break";
  class_name: string;
  start_time: string;
  end_time: string;
}

interface UserPreferences {
  total_weekly_hours_goal: number;
  earliest_study_time: string;
  latest_study_time: string;
  break_frequency: number;
  break_duration: number;
}

interface ClassData {
  class_name: string;
  class_start_time: string;
  class_end_time: string;
  class_days: string[];
  priority_level: number;
  syllabus_url: string;
  is_completed: boolean;
}

interface ScheduleState {
  blocks: ScheduleBlock[];
  user: UserPreferences;
  classes: ClassData[];
}

interface ScheduleEditorProps {
  scheduleData: ScheduleState;
  onBack: () => void;
}

interface DragState {
  blockId: number;
  originalTime: string;
  isResizing: boolean;
  startY: number;
}

export function ScheduleEditor({ scheduleData, onBack }: ScheduleEditorProps) {
  const [blocks, setBlocks] = useState<ScheduleBlock[]>(scheduleData.blocks);
  const [dragState, setDragState] = useState<DragState | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const gridRef = useRef<HTMLDivElement>(null);

  const HOURS_START = 6;
  const HOURS_END = 24;
  const MIN_SLOT = 15; // 15-minute increments
  const PIXEL_HEIGHT_PER_MINUTE = 1; // 1 pixel per minute

  // Load saved schedule from localStorage on component mount
  useEffect(() => {
    const savedSchedule = localStorage.getItem("studySchedule");
    if (savedSchedule) {
      try {
        const parsed = JSON.parse(savedSchedule);
        setBlocks(parsed);
      } catch (e) {
        console.error("Failed to load saved schedule:", e);
      }
    }
  }, []);

  const formatTime = (dateTimeString: string): string => {
    const date = new Date(dateTimeString);
    return date.toLocaleTimeString("en-US", {
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const getBlockPosition = (block: ScheduleBlock) => {
    const startDate = new Date(block.start_time);
    const endDate = new Date(block.end_time);

    const startMinutes = startDate.getHours() * 60 + startDate.getMinutes();
    const endMinutes = endDate.getHours() * 60 + endDate.getMinutes();

    const duration = endMinutes - startMinutes;
    const topOffset =
      (startMinutes - HOURS_START * 60) * PIXEL_HEIGHT_PER_MINUTE;
    const height = duration * PIXEL_HEIGHT_PER_MINUTE;

    return { topOffset, height, startMinutes, endMinutes, duration };
  };

  const snapToGrid = (minutes: number): number => {
    return Math.round(minutes / MIN_SLOT) * MIN_SLOT;
  };

  const handleBlockMouseDown = (
    e: React.MouseEvent<HTMLDivElement>,
    block: ScheduleBlock,
    isResize: boolean = false,
  ) => {
    if (isResize) {
      e.preventDefault();
      setDragState({
        blockId: block.id,
        originalTime: block.end_time,
        isResizing: true,
        startY: e.clientY,
      });
    } else {
      e.preventDefault();
      setDragState({
        blockId: block.id,
        originalTime: block.start_time,
        isResizing: false,
        startY: e.clientY,
      });
    }
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!dragState || !gridRef.current) return;

    const deltaY = e.clientY - dragState.startY;
    const deltaMinutes = snapToGrid(deltaY / PIXEL_HEIGHT_PER_MINUTE);

    const block = blocks.find((b) => b.id === dragState.blockId);
    if (!block) return;

    if (dragState.isResizing) {
      // Resize: change end_time
      const originalEndDate = new Date(block.end_time);
      const originalEndMinutes =
        originalEndDate.getHours() * 60 + originalEndDate.getMinutes();
      const newEndMinutes = Math.max(
        originalEndMinutes + deltaMinutes,
        parseInt(block.start_time.split("T")[1].split(":")[0]) * 60 +
          parseInt(block.start_time.split("T")[1].split(":")[1]) +
          MIN_SLOT,
      );

      const newEndDate = new Date(block.end_time);
      newEndDate.setHours(Math.floor(newEndMinutes / 60));
      newEndDate.setMinutes(newEndMinutes % 60);

      // Validate no overlap with next block
      const nextBlock = blocks.find(
        (b) => b.start_time > block.end_time && b.id !== block.id,
      );
      if (!nextBlock || newEndDate <= new Date(nextBlock.start_time)) {
        setBlocks((prevBlocks) =>
          prevBlocks.map((b) =>
            b.id === dragState.blockId
              ? {
                  ...b,
                  end_time: newEndDate.toISOString().split(".")[0],
                }
              : b,
          ),
        );
      }
    } else {
      // Drag: change start_time and end_time
      const startDate = new Date(block.start_time);
      const endDate = new Date(block.end_time);
      const duration =
        (new Date(block.end_time).getTime() -
          new Date(block.start_time).getTime()) /
        (1000 * 60);

      const newStartMinutes = snapToGrid(
        startDate.getHours() * 60 + startDate.getMinutes() + deltaMinutes,
      );
      const maxMinutes = HOURS_END * 60;

      if (
        newStartMinutes >= HOURS_START * 60 &&
        newStartMinutes + duration <= maxMinutes
      ) {
        // Check for overlaps
        const hasOverlap = blocks.some((b) => {
          if (b.id === dragState.blockId) return false;

          const bStart = new Date(b.start_time);
          const bEnd = new Date(b.end_time);
          const bStartMinutes = bStart.getHours() * 60 + bStart.getMinutes();
          const bEndMinutes = bEnd.getHours() * 60 + bEnd.getMinutes();

          return !(
            newStartMinutes + duration <= bStartMinutes ||
            newStartMinutes >= bEndMinutes
          );
        });

        if (!hasOverlap) {
          const newStart = new Date(block.start_time);
          const newEnd = new Date(block.end_time);

          newStart.setHours(Math.floor(newStartMinutes / 60));
          newStart.setMinutes(newStartMinutes % 60);

          const newEndMinutes = newStartMinutes + duration;
          newEnd.setHours(Math.floor(newEndMinutes / 60));
          newEnd.setMinutes(newEndMinutes % 60);

          setBlocks((prevBlocks) =>
            prevBlocks.map((b) =>
              b.id === dragState.blockId
                ? {
                    ...b,
                    start_time: newStart.toISOString().split(".")[0],
                    end_time: newEnd.toISOString().split(".")[0],
                  }
                : b,
            ),
          );
        }
      }
    }
  };

  const handleMouseUp = () => {
    setDragState(null);
  };

  const handleSave = () => {
    setIsSaving(true);

    // Save to localStorage
    localStorage.setItem("studySchedule", JSON.stringify(blocks));

    setTimeout(() => {
      setIsSaving(false);
      alert("Schedule saved successfully!");
    }, 500);
  };

  const getTimeSlots = (): number[] => {
    const slots: number[] = [];
    for (let i = HOURS_START; i < HOURS_END; i++) {
      slots.push(i);
    }
    return slots;
  };

  const getDayLabel = (dateTimeString: string): string => {
    const date = new Date(dateTimeString);
    const days = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
    return days[date.getDay()];
  };

  // Group blocks by day (simplified: assuming one day for demo)
  const getBlocksForDay = (): ScheduleBlock[] => {
    return blocks.sort(
      (a, b) =>
        new Date(a.start_time).getTime() - new Date(b.start_time).getTime(),
    );
  };

  const dayDate =
    blocks.length > 0 ? new Date(blocks[0].start_time) : new Date();
  const dayLabel = getDayLabel(
    blocks[0]?.start_time || new Date().toISOString(),
  );

  return (
    <div
      className="schedule-editor-container"
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
    >
      {/* Top Bar */}
      <div className="schedule-editor-header">
        <button className="btn btn-back-editor" onClick={onBack}>
          ← Back
        </button>
        <h1 className="schedule-editor-title">Schedule Editor</h1>
        <p className="schedule-editor-date">
          {dayDate.toLocaleDateString("en-US", {
            weekday: "long",
            month: "short",
            day: "numeric",
          })}
        </p>
        <div className="header-spacer"></div>
        <button
          className="btn btn-save-editor"
          onClick={handleSave}
          disabled={isSaving}
        >
          {isSaving ? "Saving..." : "Save Changes"}
        </button>
      </div>

      {/* Calendar Grid */}
      <div className="calendar-grid-wrapper">
        <div className="time-axis">
          <div className="time-axis-header"></div>
          {getTimeSlots().map((hour) => (
            <div
              key={hour}
              className="time-slot"
              style={{ height: `${60 * PIXEL_HEIGHT_PER_MINUTE}px` }}
            >
              <span className="time-label">
                {String(hour).padStart(2, "0")}:00
              </span>
            </div>
          ))}
        </div>

        <div className="calendar-grid" ref={gridRef}>
          <div className="day-column">
            <div className="day-header">
              <span className="day-name">{dayLabel}</span>
            </div>
            <div className="day-slots-container">
              {getTimeSlots().map((hour) => (
                <div key={`slot-${hour}`} className="hour-row">
                  {[0, 15, 30, 45].map((min) => (
                    <div
                      key={`slot-${hour}-${min}`}
                      className="quarter-slot"
                    ></div>
                  ))}
                </div>
              ))}

              {/* Render Schedule Blocks */}
              {getBlocksForDay().map((block) => {
                const { topOffset, height } = getBlockPosition(block);
                const isStudy = block.type === "study";

                return (
                  <div
                    key={block.id}
                    className={`schedule-block ${isStudy ? "study-block" : "break-block"}`}
                    style={{
                      top: `${topOffset}px`,
                      height: `${Math.max(height, 40)}px`,
                    }}
                    onMouseDown={(e) => handleBlockMouseDown(e, block, false)}
                  >
                    <div className="block-content">
                      <p className="block-title">{block.class_name}</p>
                      <p className="block-time">
                        {formatTime(block.start_time)} -{" "}
                        {formatTime(block.end_time)}
                      </p>
                    </div>

                    {/* Resize Handle */}
                    <div
                      className="resize-handle"
                      onMouseDown={(e) => handleBlockMouseDown(e, block, true)}
                    ></div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      {/* Instructions */}
      <div className="schedule-editor-footer">
        <p className="instructions">
          💡 Tip: Drag blocks to move them, drag the bottom edge to resize.
          15-minute increments.
        </p>
      </div>
    </div>
  );
}

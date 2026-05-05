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
  startY: number;
  isResizing: boolean;
  originalStartTime: string;
  originalEndTime: string;
}

export function ScheduleEditor({ scheduleData, onBack }: ScheduleEditorProps) {
  const [blocks, setBlocks] = useState<ScheduleBlock[]>(scheduleData.blocks);
  const [dragState, setDragState] = useState<DragState | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const HOURS_START = 6;
  const HOURS_END = 24;
  const MIN_SLOT = 15; // 15-minute increments
  const HOUR_HEIGHT = 60; // pixels per hour

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

  const getWeekStart = (date: Date): Date => {
    const d = new Date(date);
    const day = d.getDay();
    const diff = d.getDate() - day;
    return new Date(d.setDate(diff));
  };

  const getTimePosition = (dateTimeString: string): number => {
    const date = new Date(dateTimeString);
    const minutes = date.getHours() * 60 + date.getMinutes();
    const offsetMinutes = minutes - HOURS_START * 60;
    return (offsetMinutes / 60) * HOUR_HEIGHT;
  };

  const getDuration = (startTime: string, endTime: string): number => {
    const start = new Date(startTime);
    const end = new Date(endTime);
    return (end.getTime() - start.getTime()) / (1000 * 60);
  };

  const snapToGrid = (minutes: number): number => {
    return Math.round(minutes / MIN_SLOT) * MIN_SLOT;
  };

  const handleBlockMouseDown = (
    e: React.MouseEvent<HTMLDivElement>,
    block: ScheduleBlock,
    isResize: boolean = false,
  ) => {
    e.preventDefault();
    e.stopPropagation();

    const scrollOffset = containerRef.current?.scrollTop || 0;

    setDragState({
      blockId: block.id,
      startY: e.clientY + scrollOffset,
      isResizing: isResize,
      originalStartTime: block.start_time,
      originalEndTime: block.end_time,
    });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!dragState) return;

    const scrollOffset = containerRef.current?.scrollTop || 0;
    const deltaY = e.clientY + scrollOffset - dragState.startY;
    const deltaMinutes = snapToGrid(deltaY / (HOUR_HEIGHT / 60));

    const block = blocks.find((b) => b.id === dragState.blockId);
    if (!block) return;

    const originalStart = new Date(dragState.originalStartTime);
    const originalEnd = new Date(dragState.originalEndTime);
    const duration = getDuration(
      dragState.originalStartTime,
      dragState.originalEndTime,
    );

    if (dragState.isResizing) {
      // Resize: adjust end_time only
      const newEndMinutes =
        originalEnd.getHours() * 60 + originalEnd.getMinutes() + deltaMinutes;

      if (
        newEndMinutes -
          (originalStart.getHours() * 60 + originalStart.getMinutes()) >=
        MIN_SLOT
      ) {
        const newEnd = new Date(originalEnd);
        newEnd.setHours(Math.floor(newEndMinutes / 60));
        newEnd.setMinutes(newEndMinutes % 60);

        // Check no overlap
        const hasOverlap = blocks.some((b) => {
          if (b.id === dragState.blockId) return false;

          const bStart = new Date(b.start_time);
          const bEnd = new Date(b.end_time);
          const blockStart = new Date(dragState.originalStartTime);

          if (bStart.toDateString() !== blockStart.toDateString()) return false;

          return !(
            newEnd <= bStart || new Date(dragState.originalStartTime) >= bEnd
          );
        });

        if (!hasOverlap) {
          setBlocks((prevBlocks) =>
            prevBlocks.map((b) =>
              b.id === dragState.blockId
                ? { ...b, end_time: newEnd.toISOString().split(".")[0] }
                : b,
            ),
          );
        }
      }
    } else {
      // Drag: move both start and end times
      const newStartMinutes =
        originalStart.getHours() * 60 +
        originalStart.getMinutes() +
        deltaMinutes;
      const newEndMinutes = newStartMinutes + duration;

      // Check bounds
      if (
        newStartMinutes >= HOURS_START * 60 &&
        newEndMinutes <= HOURS_END * 60
      ) {
        // Check for overlaps
        const hasOverlap = blocks.some((b) => {
          if (b.id === dragState.blockId) return false;

          const bStart = new Date(b.start_time);
          const bEnd = new Date(b.end_time);
          const blockStart = new Date(dragState.originalStartTime);

          if (bStart.toDateString() !== blockStart.toDateString()) return false;

          const newStart = new Date(dragState.originalStartTime);
          const newEnd = new Date(dragState.originalStartTime);

          newStart.setHours(Math.floor(newStartMinutes / 60));
          newStart.setMinutes(newStartMinutes % 60);
          newEnd.setHours(Math.floor(newEndMinutes / 60));
          newEnd.setMinutes(newEndMinutes % 60);

          return !(newEnd <= bStart || newStart >= bEnd);
        });

        if (!hasOverlap) {
          const newStart = new Date(originalStart);
          const newEnd = new Date(originalEnd);

          newStart.setHours(Math.floor(newStartMinutes / 60));
          newStart.setMinutes(newStartMinutes % 60);
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
    localStorage.setItem("studySchedule", JSON.stringify(blocks));

    setTimeout(() => {
      setIsSaving(false);
      alert("Schedule saved successfully!");
    }, 500);
  };

  const getWeekDays = (): Date[] => {
    if (blocks.length === 0) return [];

    const firstBlockDate = new Date(blocks[0].start_time);
    const weekStart = getWeekStart(firstBlockDate);
    const days: Date[] = [];

    for (let i = 0; i < 7; i++) {
      const day = new Date(weekStart);
      day.setDate(day.getDate() + i);
      days.push(day);
    }

    return days;
  };

  const getBlocksForDay = (date: Date): ScheduleBlock[] => {
    return blocks
      .filter((block) => {
        const blockDate = new Date(block.start_time);
        return blockDate.toDateString() === date.toDateString();
      })
      .sort(
        (a, b) =>
          new Date(a.start_time).getTime() - new Date(b.start_time).getTime(),
      );
  };

  const getTimeSlots = (): number[] => {
    const slots: number[] = [];
    for (let i = HOURS_START; i < HOURS_END; i++) {
      slots.push(i);
    }
    return slots;
  };

  const weekDays = getWeekDays();
  const dayLabels = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
  const weekStart = weekDays.length > 0 ? weekDays[0] : new Date();

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
          Week of{" "}
          {weekStart.toLocaleDateString("en-US", {
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
      <div className="calendar-grid-wrapper" ref={containerRef}>
        {/* Time Axis */}
        <div className="time-axis">
          <div className="time-axis-header"></div>
          {getTimeSlots().map((hour) => (
            <div
              key={hour}
              className="time-slot"
              style={{ height: `${HOUR_HEIGHT}px` }}
            >
              <span className="time-label">
                {String(hour).padStart(2, "0")}:00
              </span>
            </div>
          ))}
        </div>

        {/* Day Columns */}
        <div className="calendar-grid">
          {weekDays.map((date, dayIndex) => {
            const dayBlocksList = getBlocksForDay(date);
            const dayLabel = dayLabels[date.getDay()];

            return (
              <div key={dayIndex} className="day-column">
                <div className="day-header">
                  <span className="day-name">{dayLabel}</span>
                  <span className="day-date">{date.getDate()}</span>
                </div>
                <div className="day-slots-container">
                  {/* Background Grid */}
                  {getTimeSlots().map((hour) => (
                    <div
                      key={`slot-${hour}`}
                      className="hour-row"
                      style={{ height: `${HOUR_HEIGHT}px` }}
                    >
                      {[0, 15, 30, 45].map((min) => (
                        <div
                          key={`slot-${hour}-${min}`}
                          className="quarter-slot"
                        ></div>
                      ))}
                    </div>
                  ))}

                  {/* Schedule Blocks */}
                  {dayBlocksList.map((block) => {
                    const topOffset = getTimePosition(block.start_time);
                    const duration = getDuration(
                      block.start_time,
                      block.end_time,
                    );
                    const height = (duration / 60) * HOUR_HEIGHT;
                    const isStudy = block.type === "study";

                    return (
                      <div
                        key={block.id}
                        className={`schedule-block ${isStudy ? "study-block" : "break-block"}`}
                        style={{
                          top: `${topOffset}px`,
                          height: `${Math.max(height, 35)}px`,
                        }}
                        onMouseDown={(e) =>
                          handleBlockMouseDown(e, block, false)
                        }
                      >
                        <div className="block-content">
                          <p className="block-title">{block.class_name}</p>
                          <p className="block-time">
                            {formatTime(block.start_time)} -{" "}
                            {formatTime(block.end_time)}
                          </p>
                        </div>
                        <div
                          className="resize-handle"
                          onMouseDown={(e) =>
                            handleBlockMouseDown(e, block, true)
                          }
                        ></div>
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Instructions */}
      <div className="schedule-editor-footer">
        <p className="instructions">
          Tip: Drag blocks to move them, drag the bottom edge to resize.
          15-minute increments.
        </p>
      </div>
    </div>
  );
}

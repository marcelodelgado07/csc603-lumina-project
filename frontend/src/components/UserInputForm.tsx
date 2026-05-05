import { useState } from "react";
import "./UserInputForm.css";

interface ClassData {
  id: string;
  class_name: string;
  class_start_time: string;
  class_end_time: string;
  class_days: string[];
  priority_level: number;
  syllabus_url: string;
  is_completed: boolean;
}

interface UserPreferences {
  total_weekly_hours_goal: number;
  earliest_study_time: string;
  latest_study_time: string;
  break_frequency: number;
  break_duration: number;
}

interface FormData {
  user: UserPreferences;
  classes: ClassData[];
}

interface ExpandedClassId {
  [key: string]: boolean;
}

interface UserInputFormProps {
  onBack?: () => void;
  onSubmit?: (data: FormData) => void;
}

interface ScheduleBlock {
  id: number;
  type: "study" | "break";
  class_name: string;
  start_time: string;
  end_time: string;
}

export function UserInputForm({ onBack, onSubmit }: UserInputFormProps) {
  const [formData, setFormData] = useState<FormData>({
    user: {
      total_weekly_hours_goal: 0,
      earliest_study_time: "08:00:00",
      latest_study_time: "22:00:00",
      break_frequency: 50,
      break_duration: 10,
    },
    classes: [],
  });

  const [newClassName, setNewClassName] = useState("");
  const [expandedTimePreferences, setExpandedTimePreferences] = useState(false);
  const [expandedBreakSettings, setExpandedBreakSettings] = useState(false);
  const [expandedClassDetails, setExpandedClassDetails] =
    useState<ExpandedClassId>({});
  const [isLoading, setIsLoading] = useState(false);

  const WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"];

  // ─── USER PREFERENCES HANDLERS ───
  const handleStudyHoursChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = Math.max(0, parseInt(e.target.value) || 0);
    setFormData((prev) => ({
      ...prev,
      user: { ...prev.user, total_weekly_hours_goal: value },
    }));
  };

  const handleTimeChange = (
    field: "earliest_study_time" | "latest_study_time",
    value: string,
  ) => {
    setFormData((prev) => ({
      ...prev,
      user: { ...prev.user, [field]: value },
    }));
  };

  const handleBreakChange = (
    field: "break_frequency" | "break_duration",
    value: number,
  ) => {
    setFormData((prev) => ({
      ...prev,
      user: { ...prev.user, [field]: value },
    }));
  };

  // ─── CLASS HANDLERS ───
  const handleAddClass = () => {
    if (newClassName.trim() === "") {
      alert("Please enter a class name");
      return;
    }

    const newClass: ClassData = {
      id: Date.now().toString(),
      class_name: newClassName,
      class_start_time: "",
      class_end_time: "",
      class_days: [],
      priority_level: 3,
      syllabus_url: "",
      is_completed: false,
    };

    setFormData((prev) => ({
      ...prev,
      classes: [...prev.classes, newClass],
    }));

    setNewClassName("");
  };

  const handleRemoveClass = (id: string) => {
    setFormData((prev) => ({
      ...prev,
      classes: prev.classes.filter((cls) => cls.id !== id),
    }));
    setExpandedClassDetails((prev) => {
      const updated = { ...prev };
      delete updated[id];
      return updated;
    });
  };

  const handleUpdateClass = (
    id: string,
    field: keyof ClassData,
    value: unknown,
  ) => {
    setFormData((prev) => ({
      ...prev,
      classes: prev.classes.map((cls) =>
        cls.id === id ? { ...cls, [field]: value } : cls,
      ),
    }));
  };

  const handleDayToggle = (classId: string, day: string) => {
    setFormData((prev) => ({
      ...prev,
      classes: prev.classes.map((cls) => {
        if (cls.id === classId) {
          const days = cls.class_days.includes(day)
            ? cls.class_days.filter((d) => d !== day)
            : [...cls.class_days, day];
          return { ...cls, class_days: days };
        }
        return cls;
      }),
    }));
  };

  const toggleClassDetails = (id: string) => {
    setExpandedClassDetails((prev) => ({
      ...prev,
      [id]: !prev[id],
    }));
  };

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();

    if (formData.user.total_weekly_hours_goal <= 0) {
      alert("Please enter a valid number of study hours");
      return;
    }

    if (formData.classes.length === 0) {
      alert("Please add at least one class");
      return;
    }

    // Set loading state
    setIsLoading(true);

    // Prepare data for backend (remove internal id field)
    const submissionData = {
      user: {
        total_weekly_hours_goal: formData.user.total_weekly_hours_goal,
        earliest_study_time: formData.user.earliest_study_time,
        latest_study_time: formData.user.latest_study_time,
        break_frequency: formData.user.break_frequency,
        break_duration: formData.user.break_duration,
      },
      classes: formData.classes.map((cls) => ({
        class_name: cls.class_name,
        class_start_time: cls.class_start_time,
        class_end_time: cls.class_end_time,
        class_days: cls.class_days,
        priority_level: cls.priority_level,
        syllabus_url: cls.syllabus_url,
        is_completed: cls.is_completed,
      })),
    };

    console.log("Form submitted:", submissionData);

    // Simulate API call with timeout
    setTimeout(() => {
      // Generate a mock schedule for demonstration
      const mockSchedule: ScheduleBlock[] = [
        {
          id: 1,
          type: "study",
          class_name: formData.classes[0]?.class_name || "Study Session",
          start_time: "2025-07-07T08:00:00",
          end_time: "2025-07-07T08:50:00",
        },
        {
          id: 2,
          type: "break",
          class_name: "Rest",
          start_time: "2025-07-07T08:50:00",
          end_time: "2025-07-07T09:00:00",
        },
      ];

      if (onSubmit) {
        onSubmit(submissionData as any);
      } else {
        alert("Form data ready (check console). Hook up to backend.");
      }

      setIsLoading(false);
    }, 2000); // 2 second delay to simulate API call
  };

  return (
    <div className={`form-container ${isLoading ? "loading" : ""}`}>
      {isLoading && (
        <div className="loading-overlay">
          <div className="loading-spinner"></div>
          <p className="loading-text">Generating your study schedule...</p>
        </div>
      )}
      {onBack && (
        <button
          type="button"
          className="btn btn-back"
          onClick={onBack}
          disabled={isLoading}
        >
          ← Back to Home
        </button>
      )}
      <h1>Study Schedule Builder</h1>
      <p className="subtitle">
        Tell us about your courses and study availability
      </p>

      <form onSubmit={handleSubmit} className="user-form">
        {/* BASIC SETTINGS */}
        <div className="form-section">
          <label htmlFor="studyHours">
            <strong>Available Study Hours Per Week *</strong>
          </label>
          <div className="input-group">
            <input
              id="studyHours"
              type="number"
              min="0"
              max="168"
              value={formData.user.total_weekly_hours_goal}
              onChange={handleStudyHoursChange}
              placeholder="e.g., 20"
              className="input-field"
              required
            />
            <span className="unit">hours</span>
          </div>
          <small className="helper-text">
            How many hours per week can you dedicate to studying?
          </small>
        </div>

        {/* YOUR CLASSES */}
        <div className="form-section">
          <h2>Your Classes *</h2>
          <div className="add-class-form">
            <div className="class-input-row">
              <input
                type="text"
                value={newClassName}
                onChange={(e) => setNewClassName(e.target.value)}
                placeholder="Class name (e.g., CSC 603)"
                className="input-field class-name-input"
              />
              <button
                type="button"
                onClick={handleAddClass}
                className="btn btn-add"
              >
                Add Class
              </button>
            </div>
          </div>

          {formData.classes.length === 0 ? (
            <p className="empty-state">
              No classes added yet. Add your first class above!
            </p>
          ) : (
            <div className="classes-list">
              {formData.classes.map((cls) => (
                <div key={cls.id} className="class-item">
                  <div className="class-item-header">
                    <div className="class-item-info">
                      <strong>{cls.class_name}</strong>
                      <span className="priority-badge">
                        Priority: {cls.priority_level}
                      </span>
                    </div>
                    <div className="class-item-actions">
                      <button
                        type="button"
                        className="btn btn-toggle-details"
                        onClick={() => toggleClassDetails(cls.id)}
                      >
                        {expandedClassDetails[cls.id]
                          ? "▼ Hide Details"
                          : "▶ Show Details"}
                      </button>
                      <button
                        type="button"
                        onClick={() => handleRemoveClass(cls.id)}
                        className="btn btn-remove"
                      >
                        Remove
                      </button>
                    </div>
                  </div>

                  {expandedClassDetails[cls.id] && (
                    <div className="class-item-details">
                      <div className="detail-row">
                        <label>Class Start Time</label>
                        <input
                          type="time"
                          value={cls.class_start_time}
                          onChange={(e) =>
                            handleUpdateClass(
                              cls.id,
                              "class_start_time",
                              e.target.value,
                            )
                          }
                          className="input-field"
                        />
                      </div>

                      <div className="detail-row">
                        <label>Class End Time</label>
                        <input
                          type="time"
                          value={cls.class_end_time}
                          onChange={(e) =>
                            handleUpdateClass(
                              cls.id,
                              "class_end_time",
                              e.target.value,
                            )
                          }
                          className="input-field"
                        />
                      </div>

                      <div className="detail-row">
                        <label>Class Days</label>
                        <div className="days-picker">
                          {WEEKDAYS.map((day) => (
                            <label key={day} className="day-checkbox">
                              <input
                                type="checkbox"
                                checked={cls.class_days.includes(day)}
                                onChange={() => handleDayToggle(cls.id, day)}
                              />
                              {day.slice(0, 3)}
                            </label>
                          ))}
                        </div>
                      </div>

                      <div className="detail-row">
                        <label htmlFor={`priority-${cls.id}`}>
                          Priority Level
                        </label>
                        <div className="priority-slider-container">
                          <input
                            id={`priority-${cls.id}`}
                            type="range"
                            min="1"
                            max="5"
                            value={cls.priority_level}
                            onChange={(e) =>
                              handleUpdateClass(
                                cls.id,
                                "priority_level",
                                parseInt(e.target.value),
                              )
                            }
                            className="priority-slider"
                          />
                          <span className="priority-value">
                            {cls.priority_level}
                          </span>
                        </div>
                        <small className="helper-text">1 = Low, 5 = High</small>
                      </div>

                      <div className="detail-row">
                        <label htmlFor={`syllabus-${cls.id}`}>
                          Syllabus URL
                        </label>
                        <input
                          id={`syllabus-${cls.id}`}
                          type="text"
                          placeholder="https://..."
                          value={cls.syllabus_url}
                          onChange={(e) =>
                            handleUpdateClass(
                              cls.id,
                              "syllabus_url",
                              e.target.value,
                            )
                          }
                          className="input-field"
                        />
                      </div>

                      <div className="detail-row">
                        <label className="checkbox-label">
                          <input
                            type="checkbox"
                            checked={cls.is_completed}
                            onChange={(e) =>
                              handleUpdateClass(
                                cls.id,
                                "is_completed",
                                e.target.checked,
                              )
                            }
                          />
                          Mark as completed
                        </label>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* TIME PREFERENCES (OPTIONAL) */}
        <div className="collapsible-section">
          <button
            type="button"
            className="collapsible-header"
            onClick={() => setExpandedTimePreferences(!expandedTimePreferences)}
          >
            <span className="collapsible-icon">
              {expandedTimePreferences ? "▼" : "▶"}
            </span>
            <span className="collapsible-title">⏰ Time Preferences</span>
            <span className="collapsible-subtitle">(Optional)</span>
          </button>

          {expandedTimePreferences && (
            <div className="collapsible-content">
              <div className="detail-row">
                <label htmlFor="earliestTime">Earliest Study Time</label>
                <input
                  id="earliestTime"
                  type="time"
                  value={formData.user.earliest_study_time}
                  onChange={(e) =>
                    handleTimeChange("earliest_study_time", e.target.value)
                  }
                  className="input-field"
                />
                <small className="helper-text">Default: 08:00 AM</small>
              </div>

              <div className="detail-row">
                <label htmlFor="latestTime">Latest Study Time</label>
                <input
                  id="latestTime"
                  type="time"
                  value={formData.user.latest_study_time}
                  onChange={(e) =>
                    handleTimeChange("latest_study_time", e.target.value)
                  }
                  className="input-field"
                />
                <small className="helper-text">Default: 10:00 PM</small>
              </div>
            </div>
          )}
        </div>

        {/* BREAK SETTINGS (OPTIONAL) */}
        <div className="collapsible-section">
          <button
            type="button"
            className="collapsible-header"
            onClick={() => setExpandedBreakSettings(!expandedBreakSettings)}
          >
            <span className="collapsible-icon">
              {expandedBreakSettings ? "▼" : "▶"}
            </span>
            <span className="collapsible-title">☕ Break Settings</span>
            <span className="collapsible-subtitle">(Optional)</span>
          </button>

          {expandedBreakSettings && (
            <div className="collapsible-content">
              <div className="detail-row">
                <label htmlFor="breakFrequency">
                  Study Duration Before Break
                </label>
                <div className="input-group">
                  <input
                    id="breakFrequency"
                    type="number"
                    min="5"
                    max="120"
                    value={formData.user.break_frequency}
                    onChange={(e) =>
                      handleBreakChange(
                        "break_frequency",
                        parseInt(e.target.value) || 50,
                      )
                    }
                    className="input-field"
                  />
                  <span className="unit">minutes</span>
                </div>
                <small className="helper-text">Default: 50 minutes</small>
              </div>

              <div className="detail-row">
                <label htmlFor="breakDuration">Break Duration</label>
                <div className="input-group">
                  <input
                    id="breakDuration"
                    type="number"
                    min="1"
                    max="60"
                    value={formData.user.break_duration}
                    onChange={(e) =>
                      handleBreakChange(
                        "break_duration",
                        parseInt(e.target.value) || 10,
                      )
                    }
                    className="input-field"
                  />
                  <span className="unit">minutes</span>
                </div>
                <small className="helper-text">Default: 10 minutes</small>
              </div>
            </div>
          )}
        </div>

        <button type="submit" className="btn btn-submit" disabled={isLoading}>
          Generate Study Schedule
        </button>
      </form>

      <p className="form-note">* Required fields</p>
    </div>
  );
}

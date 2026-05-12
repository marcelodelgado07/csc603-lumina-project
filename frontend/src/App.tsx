import { useState } from "react";
import { UserInputForm } from "./components/UserInputForm";
import { HomePage } from "./components/HomePage";
import { ScheduleEditor } from "./components/ScheduleEditor";
import "./App.css";

type Page = "home" | "form" | "schedule-editor";

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

function App() {
  const [currentPage, setCurrentPage] = useState<Page>("home");
  const [scheduleData, setScheduleData] = useState<ScheduleState | null>(null);

  const handleFormSubmit = (formData: any) => {
    setScheduleData({
      blocks: formData.schedule,
      user: formData.user,
      classes: formData.classes,
    });
    setCurrentPage("schedule-editor");
  };

  return (
    <div className="app">
      {currentPage === "home" && (
        <HomePage onNavigateToForm={() => setCurrentPage("form")} />
      )}
      {currentPage === "form" && (
        <UserInputForm
          onBack={() => setCurrentPage("home")}
          onSubmit={handleFormSubmit}
        />
      )}
      {currentPage === "schedule-editor" && scheduleData && (
        <ScheduleEditor
          scheduleData={scheduleData}
          onBack={() => setCurrentPage("form")}
        />
      )}
    </div>
  );
}

export default App;

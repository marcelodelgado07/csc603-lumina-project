import { useState } from "react";

interface StudyTileProps {
  classTitle: string;
  task: string;
  studyTime: number;
  isDone: boolean;
}

function StudyTile(props: StudyTileProps) {
  const [isDone, setIsDone] = useState(props.isDone);

  return (
    <div onClick={() => setIsDone(!isDone)}>
      <h3>{props.classTitle}</h3>
      <p>{props.studyTime} minutes</p>
      <p>{props.task}</p>
      <p>{isDone ? "Completed" : "Start"}</p>
    </div>
  );
}

export default StudyTile;

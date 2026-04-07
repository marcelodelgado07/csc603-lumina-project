import { UserInputForm } from "./components/UserInputForm";
import "./App.css";
import StudyTile from "./components/StudyTile";

function App() {
  return (
    <div className="app">
      <UserInputForm />
      <StudyTile
        classTitle="Math"
        task="Review algebra"
        studyTime={30}
        isDone={false}
      />
    </div>
  );
}

export default App;

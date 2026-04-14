import { useState } from "react";
import { UserInputForm } from "./components/UserInputForm";
import { HomePage } from "./components/HomePage";
import "./App.css";

type Page = "home" | "form";

function App() {
  const [currentPage, setCurrentPage] = useState<Page>("home");

  return (
    <div className="app">
      {currentPage === "home" && (
        <HomePage onNavigateToForm={() => setCurrentPage("form")} />
      )}
      {currentPage === "form" && (
        <UserInputForm onBack={() => setCurrentPage("home")} />
      )}
    </div>
  );
}

export default App;

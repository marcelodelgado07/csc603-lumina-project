import "./HomePage.css";

interface HomePageProps {
  onNavigateToForm: () => void;
}

export function HomePage({ onNavigateToForm }: HomePageProps) {
  return (
    <div className="home-container">
      <div className="home-content">
        <h1 className="home-title">Lumina</h1>
        <p className="home-subtitle">Your AI Study Planner</p>
        <p className="home-description">
          Let AI create a personalized study schedule tailored to your courses
          and availability.
        </p>
        <button className="btn btn-primary" onClick={onNavigateToForm}>
          Create Your Study Plan
        </button>
      </div>
    </div>
  );
}

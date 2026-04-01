import { useState } from 'react';
import './UserInputForm.css';

interface ClassInfo {
  id: string;
  name: string;
  credits: number;
}

interface FormData {
  studyHoursPerWeek: number;
  classes: ClassInfo[];
}

export function UserInputForm() {
  const [formData, setFormData] = useState<FormData>({
    studyHoursPerWeek: 0,
    classes: [],
  });

  const [newClassName, setNewClassName] = useState('');
  const [newClassCredits, setNewClassCredits] = useState(0);

  const handleStudyHoursChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = Math.max(0, parseInt(e.target.value) || 0);
    setFormData((prev) => ({
      ...prev,
      studyHoursPerWeek: value,
    }));
  };

  const handleAddClass = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (newClassName.trim() === '') {
      alert('Please enter a class name');
      return;
    }
    if (newClassCredits <= 0) {
      alert('Please enter valid credit hours');
      return;
    }

    const newClass: ClassInfo = {
      id: Date.now().toString(),
      name: newClassName,
      credits: newClassCredits,
    };

    setFormData((prev) => ({
      ...prev,
      classes: [...prev.classes, newClass],
    }));

    setNewClassName('');
    setNewClassCredits(0);
  };

  const handleRemoveClass = (id: string) => {
    setFormData((prev) => ({
      ...prev,
      classes: prev.classes.filter((cls) => cls.id !== id),
    }));
  };

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (formData.classes.length === 0) {
      alert('Please add at least one class');
      return;
    }

    console.log('Form submitted:', formData);
    // TODO: Send this data to your backend API
    alert('Form submitted! Check console for data.');
  };

  return (
    <div className="form-container">
      <h1>Study Schedule Builder</h1>
      <p className="subtitle">Tell us about your courses and study availability</p>

      <form onSubmit={handleSubmit} className="user-form">
        <div className="form-section">
          <label htmlFor="studyHours">
            <strong>Available Study Hours Per Week</strong>
          </label>
          <div className="input-group">
            <input
              id="studyHours"
              type="number"
              min="0"
              max="168"
              value={formData.studyHoursPerWeek}
              onChange={handleStudyHoursChange}
              placeholder="e.g., 20"
              className="input-field"
            />
            <span className="unit">hours</span>
          </div>
          <small className="helper-text">
            How many hours per week can you dedicate to studying?
          </small>
        </div>

        <div className="form-section">
          <h2>Your Classes</h2>
          <form onSubmit={handleAddClass} className="add-class-form">
            <div className="class-input-row">
              <input
                type="text"
                value={newClassName}
                onChange={(e) => setNewClassName(e.target.value)}
                placeholder="Class name (e.g., CSC 603)"
                className="input-field class-name-input"
              />
              <input
                type="number"
                min="0"
                max="5"
                step="0.5"
                value={newClassCredits}
                onChange={(e) => setNewClassCredits(parseFloat(e.target.value) || 0)}
                placeholder="Credits"
                className="input-field credits-input"
              />
              <button type="submit" className="btn btn-add">
                Add Class
              </button>
            </div>
          </form>

          {formData.classes.length === 0 ? (
            <p className="empty-state">No classes added yet. Add your first class above!</p>
          ) : (
            <div className="classes-list">
              <table className="classes-table">
                <thead>
                  <tr>
                    <th>Class Name</th>
                    <th>Credits</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {formData.classes.map((cls) => (
                    <tr key={cls.id}>
                      <td>{cls.name}</td>
                      <td>{cls.credits}</td>
                      <td>
                        <button
                          type="button"
                          onClick={() => handleRemoveClass(cls.id)}
                          className="btn btn-remove"
                        >
                          Remove
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <p className="total-credits">
                Total Credits: <strong>{formData.classes.reduce((sum, cls) => sum + cls.credits, 0)}</strong>
              </p>
            </div>
          )}
        </div>

        <button type="submit" className="btn btn-submit">
          Generate Study Schedule
        </button>
      </form>
    </div>
  );
}

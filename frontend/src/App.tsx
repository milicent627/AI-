import { Routes, Route } from 'react-router-dom';
import HomePage from './pages/HomePage';
import EditorPage from './pages/EditorPage';
import SettingsPage from './pages/SettingsPage';
import PromptOrderPage from './pages/PromptOrderPage';

export default function App() {
  return (
    <div className="h-screen flex flex-col bg-gray-950 text-gray-100">
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/editor/:storyId" element={<EditorPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/order/:storyId" element={<PromptOrderPage />} />
      </Routes>
    </div>
  );
}

import { useState } from 'react';
import Sidebar from './components/sidebar/Sidebar';
import ChatWindow from './components/chat/ChatWindow';
import { useChat } from './hooks/useChat';
import './index.css';

// Layout wrapper styles directly inlined (no separate module needed for this thin wrapper)
const layoutStyle = {
  display: 'flex',
  height: '100vh',
  width: '100vw',
  overflow: 'hidden',
  background: 'var(--bg-color)',
};

export default function App() {
  const {
    sessions,
    activeSession,
    activeSessionId,
    setActiveSessionId,
    createNewSession,
    addMessage,
    isLoading,
    setIsLoading,
  } = useChat();

  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  return (
    <div style={layoutStyle}>
      <Sidebar
        sessions={sessions}
        activeSessionId={activeSessionId}
        onSelectSession={setActiveSessionId}
        onNewChat={createNewSession}
        isCollapsed={sidebarCollapsed}
      />
      <ChatWindow
        session={activeSession}
        onAddMessage={addMessage}
        isLoading={isLoading}
        setIsLoading={setIsLoading}
        onToggleSidebar={() => setSidebarCollapsed((c) => !c)}
      />
    </div>
  );
}

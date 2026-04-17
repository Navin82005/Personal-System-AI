import { useState } from 'react';
import Sidebar from './components/sidebar/Sidebar';
import ChatWindow from './components/chat/ChatWindow';
import InsightsWindow from './components/insights/InsightsWindow';
import IndexingPage from './components/indexing/IndexingPage';
import { useChat } from './hooks/useChat';
import { useRoute } from './hooks/useRoute';
import './index.css';

// Layout wrapper styles directly inlined (no separate module needed for this thin wrapper)
const layoutStyle = {
  display: 'flex',
  height: '100vh',
  width: '100vw',
  overflow: 'hidden',
  background: 'transparent',
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
  const { pathname, navigate } = useRoute();

  const activeView =
    pathname === '/chat' ? 'chat' : pathname === '/indexing' ? 'indexing' : 'insights';

  return (
    <div style={layoutStyle}>
      <Sidebar
        sessions={sessions}
        activeSessionId={activeSessionId}
        onSelectSession={(id) => {
          setActiveSessionId(id);
          navigate('/chat');
        }}
        onNewChat={() => {
          createNewSession();
          navigate('/chat');
        }}
        isCollapsed={sidebarCollapsed}
        activeView={activeView}
        onNavigate={(view) => navigate(`/${view}`)}
      />
      {activeView === 'insights' ? (
        <InsightsWindow onToggleSidebar={() => setSidebarCollapsed((c) => !c)} />
      ) : activeView === 'indexing' ? (
        <IndexingPage onToggleSidebar={() => setSidebarCollapsed((c) => !c)} />
      ) : (
        <ChatWindow
          session={activeSession}
          onAddMessage={addMessage}
          isLoading={isLoading}
          setIsLoading={setIsLoading}
          onToggleSidebar={() => setSidebarCollapsed((c) => !c)}
        />
      )}
    </div>
  );
}

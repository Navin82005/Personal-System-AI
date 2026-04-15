import { useState, useEffect } from 'react';

const STORAGE_KEY = 'copilot_chat_sessions';

export const useChat = () => {
  const [sessions, setSessions] = useState(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    return saved ? JSON.parse(saved) : [{ id: Date.now(), title: 'New Chat', messages: [] }];
  });

  const [activeSessionId, setActiveSessionId] = useState(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      const parsed = JSON.parse(saved);
      return parsed.length > 0 ? parsed[0].id : Date.now();
    }
    return sessions[0].id;
  });

  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions));
  }, [sessions]);

  const activeSession = sessions.find(s => s.id === activeSessionId) || sessions[0];

  const createNewSession = () => {
    const newSession = { id: Date.now(), title: 'New Chat', messages: [] };
    setSessions([newSession, ...sessions]);
    setActiveSessionId(newSession.id);
  };

  const addMessage = (message) => {
    setSessions(prev => prev.map(session => {
      if (session.id === activeSessionId) {
        // Auto-generate title from first message
        const title = session.messages.length === 0 && message.sender === 'user'
          ? message.text.substring(0, 25) + '...'
          : session.title;

        return {
          ...session,
          title,
          messages: [...session.messages, message]
        };
      }
      return session;
    }));
  };

  return {
    sessions,
    activeSession,
    activeSessionId,
    setActiveSessionId,
    createNewSession,
    addMessage,
    isLoading,
    setIsLoading
  };
};

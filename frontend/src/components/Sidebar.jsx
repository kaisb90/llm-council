import { useState } from 'react';
import SettingsPanel from './SettingsPanel';
import './Sidebar.css';

export default function Sidebar({
  conversations,
  currentConversationId,
  onSelectConversation,
  onNewConversation,
}) {
  const [showSettings, setShowSettings] = useState(false);

  return (
    <>
      <div className="sidebar">
        <div className="sidebar-header">
          <h1>🧠 LLM Rat</h1>
          <button className="new-conversation-btn" onClick={onNewConversation}>
            + Neue Konversation
          </button>
          <button
            className="settings-btn"
            onClick={() => setShowSettings(true)}
            title="Einstellungen öffnen"
          >
            ⚙️ Einstellungen
          </button>
        </div>

        <div className="conversations-list">
          {conversations.length === 0 ? (
            <div className="empty-state">
              <p>Noch keine Konversationen</p>
              <p className="hint">Klicken Sie auf "Neue Konversation", um zu beginnen</p>
            </div>
          ) : (
            conversations.map((conv) => (
              <div
                key={conv.id}
                className={`conversation-item ${
                  conv.id === currentConversationId ? 'active' : ''
                }`}
                onClick={() => onSelectConversation(conv.id)}
              >
                <div className="conversation-title">{conv.title}</div>
                <div className="conversation-meta">
                  {conv.message_count} Nachrichten · {new Date(conv.created_at).toLocaleDateString()}
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {showSettings && <SettingsPanel onClose={() => setShowSettings(false)} />}
    </>
  );
}

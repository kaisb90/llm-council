const API_BASE = 'http://localhost:8001/api';

// Conversation endpoints
export async function getConversations() {
  const response = await fetch(`${API_BASE}/conversations`);
  if (!response.ok) throw new Error('Failed to fetch conversations');
  return response.json();
}

export async function createConversation() {
  const response = await fetch(`${API_BASE}/conversations`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({})
  });
  if (!response.ok) throw new Error('Failed to create conversation');
  return response.json();
}

export async function getConversation(id) {
  const response = await fetch(`${API_BASE}/conversations/${id}`);
  if (!response.ok) throw new Error('Failed to fetch conversation');
  return response.json();
}

export async function sendMessage(conversationId, content) {
  const response = await fetch(`${API_BASE}/conversations/${conversationId}/message`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content })
  });
  if (!response.ok) throw new Error('Failed to send message');
  return response.json();
}

export function sendMessageStream(conversationId, content) {
  return new EventSource(
    `${API_BASE}/conversations/${conversationId}/message/stream?content=${encodeURIComponent(content)}`
  );
}

// Provider management endpoints
export async function getProviders() {
  const response = await fetch(`${API_BASE}/providers`);
  if (!response.ok) throw new Error('Failed to fetch providers');
  return response.json();
}

export async function updateProvider(providerName, config) {
  const response = await fetch(`${API_BASE}/providers/${providerName}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config)
  });
  if (!response.ok) throw new Error('Failed to update provider');
  return response.json();
}

export async function getProviderModels(providerName) {
  const response = await fetch(`${API_BASE}/providers/${providerName}/models`);
  if (!response.ok) throw new Error('Failed to fetch provider models');
  return response.json();
}

// Council configuration endpoints
export async function getCouncilConfig() {
  const response = await fetch(`${API_BASE}/council/config`);
  if (!response.ok) throw new Error('Failed to fetch council config');
  return response.json();
}

export async function updateCouncilConfig(config) {
  const response = await fetch(`${API_BASE}/council/config`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config)
  });
  if (!response.ok) throw new Error('Failed to update council config');
  return response.json();
}

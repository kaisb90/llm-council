import { useState, useEffect } from 'react';
import * as api from '../api';
import './SettingsPanel.css';

export default function SettingsPanel({ onClose }) {
  const [providers, setProviders] = useState({});
  const [councilModels, setCouncilModels] = useState([]);
  const [chairmanModel, setChairmanModel] = useState(null);
  const [availableModels, setAvailableModels] = useState({});
  const [activeTab, setActiveTab] = useState('providers');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadProviders();
    loadCouncilConfig();
  }, []);

  const loadProviders = async () => {
    try {
      setLoading(true);
      const data = await api.getProviders();
      setProviders(data);
    } catch (error) {
      setError('Fehler beim Laden der Anbieter: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  const loadCouncilConfig = async () => {
    try {
      const data = await api.getCouncilConfig();
      setCouncilModels(data.council_models || []);
      setChairmanModel(data.chairman_model || null);
    } catch (error) {
      setError('Fehler beim Laden der Rat-Konfiguration: ' + error.message);
    }
  };

  const loadProviderModels = async (providerName) => {
    try {
      setLoading(true);
      const data = await api.getProviderModels(providerName);
      setAvailableModels((prev) => ({
        ...prev,
        [providerName]: data.models || [],
      }));
      setError(null);
    } catch (error) {
      setError(`Fehler beim Laden der Modelle für ${providerName}: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateProvider = async (providerName, config) => {
    try {
      await api.updateProvider(providerName, config);
      loadProviders();
      setError(null);
    } catch (error) {
      setError('Fehler beim Aktualisieren des Anbieters: ' + error.message);
    }
  };

  const saveCouncilConfig = async () => {
    try {
      setLoading(true);
      await api.updateCouncilConfig({
        council_models: councilModels,
        chairman_model: chairmanModel,
      });
      alert('Rat-Konfiguration erfolgreich gespeichert!');
      setError(null);
    } catch (error) {
      setError('Fehler beim Speichern der Rat-Konfiguration: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  const addCouncilModel = () => {
    setCouncilModels([
      ...councilModels,
      {
        provider: 'openrouter',
        model_id: '',
        display_name: 'Neues Modell',
        enabled: true,
        temperature: 0.7,
        max_tokens: 4096,
      },
    ]);
  };

  const removeCouncilModel = (index) => {
    setCouncilModels(councilModels.filter((_, i) => i !== index));
  };

  const updateCouncilModel = (index, field, value) => {
    const updated = [...councilModels];
    updated[index][field] = value;
    setCouncilModels(updated);
  };

  return (
    <div className="settings-overlay" onClick={onClose}>
      <div className="settings-panel" onClick={(e) => e.stopPropagation()}>
        <div className="settings-header">
          <h2>⚙️ Einstellungen</h2>
          <button className="close-btn" onClick={onClose}>
            ×
          </button>
        </div>

        <div className="settings-tabs">
          <button
            className={activeTab === 'providers' ? 'active' : ''}
            onClick={() => setActiveTab('providers')}
          >
            Anbieter
          </button>
          <button
            className={activeTab === 'council' ? 'active' : ''}
            onClick={() => setActiveTab('council')}
          >
            Rat-Konfiguration
          </button>
        </div>

        {error && <div className="error-banner">{error}</div>}

        <div className="settings-content">
          {activeTab === 'providers' && (
            <div className="providers-section">
              <h3>Anbieter konfigurieren</h3>
              <p className="section-description">
                Aktivieren und konfigurieren Sie LLM-Anbieter. API-Schlüssel können hier oder über Umgebungsvariablen gesetzt werden.
              </p>

              {Object.entries(providers).map(([name, config]) => (
                <div key={name} className="provider-card">
                  <div className="provider-header">
                    <h4>{name.charAt(0).toUpperCase() + name.slice(1)}</h4>
                    <label className="toggle">
                      <input
                        type="checkbox"
                        checked={config.enabled}
                        onChange={(e) =>
                          handleUpdateProvider(name, {
                            ...config,
                            enabled: e.target.checked,
                          })
                        }
                      />
                      <span className="slider"></span>
                    </label>
                  </div>

                  {config.enabled && (
                    <div className="provider-config">
                      {config.api_key !== undefined && (
                        <div className="form-group">
                          <label>API-Schlüssel</label>
                          <input
                            type="password"
                            placeholder="API-Schlüssel eingeben"
                            value={config.api_key || ''}
                            onChange={(e) =>
                              handleUpdateProvider(name, {
                                ...config,
                                api_key: e.target.value,
                              })
                            }
                          />
                        </div>
                      )}
                      {config.base_url !== undefined && (
                        <div className="form-group">
                          <label>Basis-URL</label>
                          <input
                            type="text"
                            placeholder="http://localhost:11434"
                            value={config.base_url || ''}
                            onChange={(e) =>
                              handleUpdateProvider(name, {
                                ...config,
                                base_url: e.target.value,
                              })
                            }
                          />
                        </div>
                      )}
                      <button
                        className="btn-secondary"
                        onClick={() => loadProviderModels(name)}
                        disabled={loading}
                      >
                        {loading ? 'Laden...' : 'Verfügbare Modelle laden'}
                      </button>

                      {availableModels[name] && (
                        <div className="models-list">
                          <h5>Verfügbare Modelle ({availableModels[name].length})</h5>
                          <ul>
                            {availableModels[name].slice(0, 10).map((model) => (
                              <li key={model.id}>
                                <strong>{model.name}</strong>
                                <span className="model-id">{model.id}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {activeTab === 'council' && (
            <div className="council-section">
              <h3>Ratsmitglieder</h3>
              <p className="section-description">
                Konfigurieren Sie, welche Modelle an der Beratung des Rates teilnehmen.
              </p>

              {councilModels.map((model, index) => (
                <div key={index} className="model-config-card">
                  <div className="model-config-header">
                    <input
                      type="text"
                      placeholder="Anzeigename"
                      value={model.display_name}
                      onChange={(e) =>
                        updateCouncilModel(index, 'display_name', e.target.value)
                      }
                    />
                    <button
                      className="btn-danger-small"
                      onClick={() => removeCouncilModel(index)}
                    >
                      Entfernen
                    </button>
                  </div>

                  <div className="model-config-fields">
                    <div className="form-group">
                      <label>Anbieter</label>
                      <select
                        value={model.provider}
                        onChange={(e) =>
                          updateCouncilModel(index, 'provider', e.target.value)
                        }
                      >
                        <option value="openrouter">OpenRouter</option>
                        <option value="gemini">Gemini</option>
                        <option value="ollama">Ollama</option>
                        <option value="mistral">Mistral</option>
                      </select>
                    </div>

                    <div className="form-group">
                      <label>Modell-ID</label>
                      <input
                        type="text"
                        placeholder="z.B. openai/gpt-4o"
                        value={model.model_id}
                        onChange={(e) =>
                          updateCouncilModel(index, 'model_id', e.target.value)
                        }
                      />
                    </div>

                    <div className="form-group">
                      <label>Temperatur</label>
                      <input
                        type="number"
                        min="0"
                        max="2"
                        step="0.1"
                        value={model.temperature}
                        onChange={(e) =>
                          updateCouncilModel(
                            index,
                            'temperature',
                            parseFloat(e.target.value)
                          )
                        }
                      />
                    </div>

                    <div className="form-group">
                      <label>Max Token</label>
                      <input
                        type="number"
                        min="256"
                        max="128000"
                        step="256"
                        value={model.max_tokens}
                        onChange={(e) =>
                          updateCouncilModel(
                            index,
                            'max_tokens',
                            parseInt(e.target.value)
                          )
                        }
                      />
                    </div>
                  </div>
                </div>
              ))}

              <button className="btn-primary" onClick={addCouncilModel}>
                + Ratsmitglied hinzufügen
              </button>

              <div className="chairman-section">
                <h3>Vorsitzender (Chairman)</h3>
                <p className="section-description">
                  Der Vorsitzende fasst die endgültige Antwort aus allen Beratungen des Rates zusammen.
                </p>

                {chairmanModel && (
                  <div className="model-config-card">
                    <div className="model-config-fields">
                      <div className="form-group">
                        <label>Anzeigename</label>
                        <input
                          type="text"
                          value={chairmanModel.display_name}
                          onChange={(e) =>
                            setChairmanModel({
                              ...chairmanModel,
                              display_name: e.target.value,
                            })
                          }
                        />
                      </div>

                      <div className="form-group">
                        <label>Anbieter</label>
                        <select
                          value={chairmanModel.provider}
                          onChange={(e) =>
                            setChairmanModel({
                              ...chairmanModel,
                              provider: e.target.value,
                            })
                          }
                        >
                          <option value="openrouter">OpenRouter</option>
                          <option value="gemini">Gemini</option>
                          <option value="ollama">Ollama</option>
                          <option value="mistral">Mistral</option>
                        </select>
                      </div>

                      <div className="form-group">
                        <label>Modell-ID</label>
                        <input
                          type="text"
                          value={chairmanModel.model_id}
                          onChange={(e) =>
                            setChairmanModel({
                              ...chairmanModel,
                              model_id: e.target.value,
                            })
                          }
                        />
                      </div>
                    </div>
                  </div>
                )}
              </div>

              <button
                className="btn-success"
                onClick={saveCouncilConfig}
                disabled={loading}
              >
                {loading ? 'Speichern...' : 'Konfiguration speichern'}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

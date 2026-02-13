import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import './Stage25.css';

export default function Stage25({ results }) {
  const [activeTab, setActiveTab] = useState(0);

  if (!results || results.length === 0) {
    return null;
  }

  const activeResult = results[activeTab];

  return (
    <div className="stage stage25">
      <h3 className="stage-title">Stage 2.5: Self-Repair & Validation</h3>
      <p className="stage-description">
        Each model reviewed the peer feedback from Stage 2 and attempted to fix identified issues.
      </p>

      <div className="tabs">
        {results.map((result, index) => (
          <button
            key={index}
            className={`tab ${activeTab === index ? 'active' : ''}`}
            onClick={() => setActiveTab(index)}
          >
            {result.model.split('/')[1] || result.model}
            {result.passthrough && <span className="badge-passthrough">✓ Valid</span>}
          </button>
        ))}
      </div>

      <div className="tab-content">
        <div className="model-header">
           <span className="model-name">{activeResult.model}</span>
           {activeResult.passthrough ? (
             <span className="status-badge success">No critical bugs found - Original answer retained</span>
           ) : (
             <span className="status-badge warning">Changes applied based on feedback</span>
           )}
        </div>

        {!activeResult.passthrough && activeResult.fix_log && activeResult.fix_log.length > 0 && (
          <div className="fix-log">
            <h4>Fix Log</h4>
            <ul>
              {activeResult.fix_log.map((entry, i) => (
                <li key={i}>
                  <strong>{entry.issue}:</strong> {entry.change}
                </li>
              ))}
            </ul>
          </div>
        )}

        <div className="revised-answer">
          <h4>Revised Response</h4>
          <div className="markdown-content">
            <ReactMarkdown>{activeResult.revised_answer}</ReactMarkdown>
          </div>
        </div>

        {activeResult.remaining_risks && activeResult.remaining_risks.length > 0 && (
          <div className="risks">
             <h4>Remaining Risks</h4>
             <ul>
               {activeResult.remaining_risks.map((risk, i) => (
                 <li key={i}>{risk}</li>
               ))}
             </ul>
          </div>
        )}
      </div>
    </div>
  );
}

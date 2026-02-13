import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import './Stage2.css';

function deAnonymizeText(text, labelToModel) {
  if (!labelToModel) return text;

  let result = text;
  // Replace each "Response X" with the actual model name
  Object.entries(labelToModel).forEach(([label, model]) => {
    const modelShortName = model.split('/')[1] || model;
    result = result.replace(new RegExp(label, 'g'), `**${modelShortName}**`);
  });
  return result;
}

export default function Stage2({ rankings, labelToModel, aggregateRankings }) {
  const [activeTab, setActiveTab] = useState(0);

  if (!rankings || rankings.length === 0) {
    return null;
  }

  return (
    <div className="stage stage2">
      <h3 className="stage-title">Stage 2: Peer Rankings</h3>

      <h4>Raw Evaluations</h4>
      <p className="stage-description">
        Each model evaluated all responses (anonymized as Response A, B, C, etc.) and provided rankings.
        Below, model names are shown in <strong>bold</strong> for readability, but the original evaluation used anonymous labels.
      </p>

      <div className="tabs">
        {rankings.map((rank, index) => (
          <button
            key={index}
            className={`tab ${activeTab === index ? 'active' : ''}`}
            onClick={() => setActiveTab(index)}
          >
            {rank.model.split('/')[1] || rank.model}
          </button>
        ))}
      </div>

      <div className="tab-content">
        <div className="ranking-model">
          {rankings[activeTab].model}
        </div>

        {rankings[activeTab].review_json ? (
          <div className="review-json-content">
             {Object.entries(rankings[activeTab].review_json.reviews || {}).map(([label, review]) => (
               <div key={label} className="review-item">
                 <h5>
                   {label}
                   {labelToModel && labelToModel[label] && (
                     <span className="model-reveal"> ({labelToModel[label].split('/')[1]})</span>
                   )}
                 </h5>

                 {review.bugs && review.bugs.length > 0 ? (
                   <ul className="bugs-list">
                     {review.bugs.map((bug, i) => (
                       <li key={i} className={`bug-item severity-${bug.severity}`}>
                         <span className="bug-severity">Sev {bug.severity}</span>
                         <strong>{bug.title}</strong>
                         {bug.evidence && (
                           <div className="bug-evidence">
                             "{bug.evidence.substring}"
                           </div>
                         )}
                       </li>
                     ))}
                   </ul>
                 ) : (
                   <div className="no-bugs">No significant bugs found.</div>
                 )}

                 {review.notes && (
                   <div className="review-notes">
                     <em>{review.notes}</em>
                   </div>
                 )}
               </div>
             ))}

             {rankings[activeTab].review_json.final_ranking && (
               <div className="parsed-ranking">
                 <strong>Final Ranking:</strong>
                 <ol>
                   {rankings[activeTab].review_json.final_ranking.map((label, i) => (
                     <li key={i}>
                       {label}
                       {labelToModel && labelToModel[label] && (
                         <span> ({labelToModel[label].split('/')[1]})</span>
                       )}
                     </li>
                   ))}
                 </ol>
               </div>
             )}
          </div>
        ) : (
          <div className="ranking-content markdown-content">
            <ReactMarkdown>
              {deAnonymizeText(rankings[activeTab].ranking, labelToModel)}
            </ReactMarkdown>
          </div>
        )}

        {!rankings[activeTab].review_json && rankings[activeTab].parsed_ranking &&
         rankings[activeTab].parsed_ranking.length > 0 && (
          <div className="parsed-ranking">
            <strong>Extracted Ranking:</strong>
            <ol>
              {rankings[activeTab].parsed_ranking.map((label, i) => (
                <li key={i}>
                  {labelToModel && labelToModel[label]
                    ? labelToModel[label].split('/')[1] || labelToModel[label]
                    : label}
                </li>
              ))}
            </ol>
          </div>
        )}
      </div>

      {aggregateRankings && aggregateRankings.length > 0 && (
        <div className="aggregate-rankings">
          <h4>Aggregate Rankings (Street Cred)</h4>
          <p className="stage-description">
            Combined results across all peer evaluations (lower score is better):
          </p>
          <div className="aggregate-list">
            {aggregateRankings.map((agg, index) => (
              <div key={index} className="aggregate-item">
                <span className="rank-position">#{index + 1}</span>
                <span className="rank-model">
                  {agg.model.split('/')[1] || agg.model}
                </span>
                <span className="rank-score">
                  Avg: {agg.average_rank.toFixed(2)}
                </span>
                <span className="rank-count">
                  ({agg.rankings_count} votes)
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

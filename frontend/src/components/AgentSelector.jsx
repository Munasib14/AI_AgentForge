import React from "react";

const AgentSelector = ({ selected, onChange }) => {
  const agents = ["DB Agent", "Web Agent", "Test Agent","DevOps Agent",  "Batch Jobs Agent"];

  return (
    <div style={{ marginBottom: "1rem" }}>
      <label>Cloud Migration Agents</label>
      <select value={selected} onChange={(e) => onChange(e.target.value)}>
        {agents.map((a) => (
          <option key={a} value={a}>
            {a}
          </option>
        ))}
      </select>
    </div>
  );
};
export default AgentSelector;
import React from "react";

const PromptDropdown = ({
  prompts,
  selectedPrompt,
  editablePrompt,
  onSelect,
  onEdit,
  onUpdate,
  onDelete,
}) => {
  return (
    <div style={{ marginBottom: "1rem" }}>
      <label>Select Common Prompt</label>
      <select value={selectedPrompt} onChange={(e) => onSelect(e.target.value)}>
        <option value="">Choose a prompt --</option>
        {prompts.map((p) => (
          <option key={p} value={p}>
            {p.replace(".j2", "").replaceAll("_", " ")}
          </option>
        ))}
      </select>

      {selectedPrompt && (
        <>
          <textarea
            value={editablePrompt}
            onChange={(e) => onEdit(e.target.value)}
            style={{ width: "100%", marginTop: "0.5rem", height: "100px" }}
          />
          <button onClick={() => onUpdate(editablePrompt)}>EDIT OPTION</button>
          <button onClick={onDelete} style={{ marginLeft: "0.5rem" }}>
            DELETE OPTION
          </button>
        </>
      )}
    </div>
  );
};

export default PromptDropdown;
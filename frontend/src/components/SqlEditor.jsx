import React from 'react';

const SqlEditor = ({ value, onChange }) => (
  <div>
    <textarea
      rows="8"
      cols="80"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder="Paste or write Code to be analyzed, transformed, or optimized..."
    />
  </div>
);

export default SqlEditor;
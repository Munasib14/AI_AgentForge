import React from 'react';

const ResponseBox = ({ content }) => (
  <div style={{ marginTop: '1rem' }}>
    <label>Agent Response:</label>
    <pre style={{ background: '#f3f3f3', padding: '1rem' }}>{content}</pre>
  </div>
);

export default ResponseBox;
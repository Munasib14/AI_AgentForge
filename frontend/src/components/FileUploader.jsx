import React from "react";

const FileUploader = () => {
  return (
    <div>
      <label>Select File:</label>
      <input type="file" />
      <button style={{ marginTop: "0.5rem" }}>UPLOAD FILE</button>
    </div>
  );
};

export default FileUploader;
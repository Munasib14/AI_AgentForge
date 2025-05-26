import React, { useState, useEffect } from "react";
import "./App.css";
import AgentSelector from "./components/AgentSelector";
import PromptDropdown from "./components/PromptDropdown";
import SqlEditor from "./components/SqlEditor";
import FileUploader from "./components/FileUploader";
import axios from "axios";

const API_URL = "http://127.0.0.1:8000";

const promptMap = {
  "DB Agent": [
    "transform_identity.j2",
    "optimize_performance.j2",
    "migrate_legacy_azure.j2",
    "refactor_procedure.j2",
    "best_practices.j2",
    "add_try_catch.j2",
    "analyze_security_risks.j2",
  ],
  "Web Agent": [
    "convert_asp.net_to_react.j2",
    "convert_asp.net_4.8_to_8.j2",
    "Html_to_Jsx.j2",
    "Automate_Form_Handling.j2",
    "Optimize_Css.j2",
    "State_Management.j2",
    "Routing_Setup.j2",
    "Authentication_Integration.j2"
  ],
  "Test Agent": [
    "Convert_ReactPage_to_Playwright.j2",
    "generate_advanced_integration_test.j2",
    "generate_advanced_unit_test.j2",
    "generate_multistep_feature_file.j2",
    // "generate_selenium_test.j2",
  ],
  "DevOps Agent": ["devops_infra.j2", "transform_infra.j2"],
  "Batch Jobs Agent": ["schedule_batch_cron.j2"],
};

function App() {
  const [selectedAgent, setSelectedAgent] = useState("DB Agent");
  const [promptList, setPromptList] = useState(promptMap["DB Agent"]);
  const [selectedPrompt, setSelectedPrompt] = useState("");
  const [editablePrompt, setEditablePrompt] = useState("");
  const [sqlCode, setSqlCode] = useState("");
  const [chatHistory, setChatHistory] = useState([]);
  const [pushStatus, setPushStatus] = useState("");

  // Github
  const [showModal, setShowModal] = useState(false);
  const [currentContent, setCurrentContent] = useState("");
  const [currentFilename, setCurrentFilename] = useState("");
  const [githubUrl, setGithubUrl] = useState("");

  useEffect(() => {
    setPromptList(promptMap[selectedAgent] || []);
    setSelectedPrompt("");
    setEditablePrompt("");
    setSqlCode("");
    setChatHistory([]);
  }, [selectedAgent]);

  useEffect(() => {
    const fetchPrompt = async () => {
      if (!selectedPrompt || !selectedAgent) return;

      try {
        const res = await axios.get(
          `${API_URL}/get-prompt?prompt_name=${encodeURIComponent(
            selectedPrompt
          )}&agent_type=${encodeURIComponent(selectedAgent)}`
        );

        const content = res?.data?.prompt_content || "";
        setEditablePrompt(content);
        setSqlCode(content);
      } catch (error) {
        console.error("Error fetching prompt:", error);
        const fallback = "-- ⚠️ Unable to fetch prompt.";
        setEditablePrompt(fallback);
        setSqlCode(fallback);
      }
    };

    fetchPrompt();
  }, [selectedPrompt, selectedAgent]);

  const handleRun = async () => {
    if (!sqlCode.trim()) {
      alert("⚠️ Please enter code.");
      return;
    }

    let endpoint = "";
    let payload = {};

    if (selectedAgent === "DB Agent") {
      endpoint = `${API_URL}/run-db-agent/`;
      payload = {
        sql_code: sqlCode,
        prompt_name: selectedPrompt || "transform_identity.j2",
      };
    } else if (selectedAgent === "Web Agent") {
      endpoint = `${API_URL}/run-web-agent/`;
      payload = {
        html_code: sqlCode,
        prompt_name: selectedPrompt || "convert_asp_net_to_react.j2",
      };
    } else if (selectedAgent === "Test Agent") {
      endpoint = `${API_URL}/run-test-agent/`;
      payload = {
        source_code: sqlCode,
        prompt_name: selectedPrompt || "Convert_ReactPage_to_Playwright.j2",
      };
    } else if (selectedAgent === "DevOps Agent") {
      endpoint = `${API_URL}/run-dev-agent/`;
      payload = {
        infra_description: sqlCode,
        prompt_name: selectedPrompt || "devops_infra.j2",
      };
    } else {
      alert("⚠️ Unsupported agent selected.");
      return;
    }

    try {
      const res = await axios.post(endpoint, payload);
      const agentResponse =
        res?.data?.result?.output || "⚠️ No output returned.";

      setChatHistory((prev) => [
        ...prev,
        { user: sqlCode, agent: agentResponse },
      ]);

      // Push the converted code to GitHub
      await pushToGitHub(agentResponse);
      setPushStatus("✅ Successfully pushed to GitHub!");

      await pushAllLocalChanges();
      setPushStatus("✅ Successfully pushed to GitHub!");

      // Clear the input field after submission
      setSqlCode("");
    } catch (err) {
      const errorMsg =
        "❌ Error: " + (err?.response?.data?.detail || err.message);
      setChatHistory((prev) => [...prev, { user: sqlCode, agent: errorMsg }]);
    }
  };

  // Function to handle downloading the converted code for each generated output
  const handleDownload = (output, index) => {
    const blob = new Blob([output], {
      type: "text/plain;charset=utf-8",
    });
    const url = URL.createObjectURL(blob);

    const link = document.createElement("a");
    link.href = url;
    link.download = `converted_code_${index + 1}.txt`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  // Function to handle pushing the converted code to GitHub
  const pushToGitHub = async (content) => {
    try {
      const filename = `converted_${Date.now()}.txt`;

      const payload = {
        filename,
        content,
      };

      setPushStatus("Pushing to GitHub...");

      const res = await axios.post(`${API_URL}/push-to-github/`, payload);

      if (res.status === 200 || res.status === 201) {
        setPushStatus("✅ Successfully pushed to GitHub!");
      } else {
        setPushStatus("❌ Failed to push to GitHub.");
      }
    } catch (error) {
      console.error("GitHub Push Error:", error);
      setPushStatus("❌ Error pushing to GitHub.");
    }
  };

  // Function to handle pushing all local changes to GitHub
  const pushAllLocalChanges = async () => {
    try {
      setPushStatus("🔄 Pushing all local changes...");

      const res = await axios.post(`${API_URL}/push-all-local/`);
      const msg = res.data?.message || "Unknown response";
      setPushStatus(msg.includes("✅") ? msg : "⚠️ " + msg);
    } catch (err) {
      setPushStatus("❌ Push failed.");
      console.error("Push all error:", err);
    }
  };

  const handleShare = (content) => {
    setCurrentContent(content);  // Store content to be shared
    setShowModal(true);          // Open the modal by setting the state to true
  };

  const handleSaveShare = async () => {
    if (!githubUrl.trim()) {
      alert("⚠️ Please enter a valid GitHub path.");
      return;
    }

    const payload = {
      content: currentContent,
      githubUrl,
    };

    try {
      const res = await axios.post(`${API_URL}/save-share/`, payload);

      if (res.status === 200 || res.status === 201) {
        alert("✅ Content shared successfully!");
        setShowModal(false);
      } else {
        alert("❌ Failed to share content.");
      }
    } catch (error) {
      alert("❌ Error sharing content.");
      console.error("Share Error:", error);
    }
  };

  return (
    <>
    
      
      <div className="header">
        <div className="title">GENAI COE-CHATBOT</div>
        <div className="username">MAPS</div>
      </div>

      <div className="container">
        <div className="left-panel">
          <div className="chat-wrapper">
            {[...chatHistory].reverse().map((item, idx) => (
              <div key={idx} className="chat-block">
                <div className="user-msg">
                  <strong>User:</strong> <pre>{item.user}</pre>
                </div>
                <div className="agent-msg">
                  <strong>Agent Output:</strong> <pre>{item.agent}</pre>
                  <button
                    className="run-btn"
                    onClick={() => handleDownload(item.agent, idx)}
                  >
                    DOWNLOAD
                  </button>

                  <button
  className="run-btn"
  onClick={() => handleShare(item.agent)}  // Pass the content to share
  style={{ marginLeft: "10px" }}
>
  SHARE
</button>

                </div>
              </div>
            ))}

          </div>


          <h4>User Input :</h4>
          <SqlEditor
            value={sqlCode}
            onChange={setSqlCode}
            placeholder="Paste or write SQL/Code..."
          />
          <div style={{ display: "flex", gap: "10px", marginTop: "10px" }}>
            <button className="run-btn" onClick={handleRun}>
              ENTER
            </button>
          </div>
        </div>

        <div className="right-panel">
          <AgentSelector
            selectedAgent={selectedAgent}
            onChange={setSelectedAgent}
          />

          <PromptDropdown
            prompts={promptList}
            selectedAgent={selectedAgent}
            selectedPrompt={selectedPrompt}
            editablePrompt={editablePrompt}
            onSelect={setSelectedPrompt}
            onEdit={setEditablePrompt}
            onUpdate={(updated) => {
              setPromptList((prev) =>
                prev.map((p) => (p === selectedPrompt ? updated : p))
              );
              setSelectedPrompt(updated);
              setEditablePrompt("");
              setSqlCode(updated);
            }}
            onDelete={() => {
              setPromptList((prev) => prev.filter((p) => p !== selectedPrompt));
              setSelectedPrompt("");
              setEditablePrompt("");
              setSqlCode("");
            }}
          />

          <FileUploader />
          {showModal && (
  <div className="fixed inset-0 bg-black bg-opacity-40 flex justify-center items-center z-50">
    <div className="bg-white p-6 rounded-2xl shadow-xl w-full max-w-md">
      <h3 className="text-lg font-semibold mb-4">Enter GitHub Path</h3>
      <input
        type="text"
        placeholder="e.g., username/repo/path/file.txt"
        value={githubUrl}
        onChange={(e) => setGithubUrl(e.target.value)}
        className="w-full text-lg px-6 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 mb-4"
/>
      <div className="flex justify-end gap-3">
        <button
          onClick={() => setShowModal(false)}
          className="px-4 py-2 bg-gray-300 text-gray-800 rounded-lg hover:bg-gray-400"
        >
          Cancel
        </button>
        <button
          onClick={handleSaveShare}
          className="ml-3 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          Save
        </button>
      </div>
    </div>
  </div>
)}

        </div>
      </div>
      
    </>
  );
}


export default App;

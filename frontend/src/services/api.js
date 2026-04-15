export const sendMessageToBackend = async (message) => {
  try {
    const response = await fetch('http://127.0.0.1:8000/query', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ query: message }),
    });

    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }

    const data = await response.json();
    return data.answer || "No response received";
  } catch (error) {
    console.error("Fetch Error:", error);
    throw new Error("Unable to connect to AI server. Please try again.");
  }
};

export const scanFolder = async (folderPath) => {
  try {
    const response = await fetch('http://127.0.0.1:8000/scan-folder', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ folder_path: folderPath }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => null);
      throw new Error(errorData?.detail || `Scan failed: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error("Scan Folder Error:", error);
    throw error;
  }
};


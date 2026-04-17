const BASE_URL = 'http://127.0.0.1:8000';

export const sendMessageToBackend = async (message) => {
  try {
    const response = await fetch(`${BASE_URL}/query`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ query: message, "top_k": 6 }),
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
    const response = await fetch(`${BASE_URL}/scan-folder`, {
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

export const cancelIndexJob = async (jobId) => {
  const res = await fetch(`${BASE_URL}/progress/${encodeURIComponent(jobId)}/cancel`, { method: 'POST' });
  if (!res.ok) throw new Error(`Cancel failed: ${res.status}`);
  return res.json();
};

export const fetchProgress = async (jobId) => {
  const res = await fetch(`${BASE_URL}/progress/${encodeURIComponent(jobId)}`);
  if (!res.ok) throw new Error(`Progress error: ${res.status}`);
  return res.json();
};

export const fetchInsightsSummary = async () => {
  const res = await fetch(`${BASE_URL}/insights/summary`);
  if (!res.ok) throw new Error(`Insights summary error: ${res.status}`);
  return res.json();
};

export const fetchInsightsContentDistribution = async () => {
  const res = await fetch(`${BASE_URL}/insights/content-distribution`);
  if (!res.ok) throw new Error(`Insights distribution error: ${res.status}`);
  return res.json();
};

export const fetchInsightsRecentFiles = async (limit = 10) => {
  const res = await fetch(`${BASE_URL}/insights/recent-files?limit=${encodeURIComponent(limit)}`);
  if (!res.ok) throw new Error(`Insights recent files error: ${res.status}`);
  return res.json();
};

export const fetchInsightsSizeDistribution = async () => {
  const res = await fetch(`${BASE_URL}/insights/size-distribution`);
  if (!res.ok) throw new Error(`Insights size distribution error: ${res.status}`);
  return res.json();
};

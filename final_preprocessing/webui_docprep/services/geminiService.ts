
import { GoogleGenAI } from "@google/genai";

const ai = new GoogleGenAI({ apiKey: process.env.API_KEY });

export const analyzeLogAnomaly = async (logs: string[]) => {
  const prompt = `Analyze the following processing logs for a document preprocessing pipeline. Identify bottlenecks, repeated failures, or strange patterns in the Decision Engine scenarios. Return a concise summary with actionable items.
  
  LOGS:
  ${logs.join('\n')}
  `;

  try {
    const response = await ai.models.generateContent({
      model: 'gemini-3-flash-preview',
      contents: prompt,
      config: {
        systemInstruction: "You are a senior DevOps engineer specializing in document processing pipelines. Be technical, precise, and brief."
      }
    });
    return response.text;
  } catch (error) {
    console.error("Gemini analysis failed:", error);
    return "Failed to analyze logs via AI.";
  }
};
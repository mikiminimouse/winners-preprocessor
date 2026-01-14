/**
 * Hello Service
 * Provides a simple hello world endpoint for testing the development pipeline
 */

export interface HelloResponse {
  message: string;
  timestamp: string;
}

/**
 * Get a hello world message
 * @returns Promise<HelloResponse> - Response with message and timestamp
 */
export const getHello = async (): Promise<HelloResponse> => {
  try {
    return {
      message: "Hello World",
      timestamp: new Date().toISOString()
    };
  } catch (error) {
    console.error("Hello service failed:", error);
    throw new Error("Failed to get hello message");
  }
};

/**
 * Get a personalized hello message
 * @param name - The name to personalize the message with
 * @returns Promise<HelloResponse> - Response with personalized message
 */
export const getPersonalizedHello = async (name: string): Promise<HelloResponse> => {
  try {
    if (!name || name.trim().length === 0) {
      throw new Error("Name is required");
    }

    return {
      message: `Hello, ${name}!`,
      timestamp: new Date().toISOString()
    };
  } catch (error) {
    console.error("Personalized hello service failed:", error);
    throw new Error("Failed to get personalized hello message");
  }
};
